"""Fireworks AI OpenAI-compatible client."""

import asyncio
import time
from typing import Any

from app.core.config import get_settings
from app.core.errors import AgentGuardError
from app.core.logging import get_logger
from app.llm.types import ChatCompletionResult, TokenUsage

import httpx


logger = get_logger(__name__)


class FireworksClient:
    """OpenAI-compatible Fireworks AI client wrapper."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.fireworks_base_url.rstrip("/")

    async def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> ChatCompletionResult:
        """Call the Fireworks chat completions API.

        Uses the Fireworks OpenAI-compatible `/chat/completions` endpoint documented at
        https://docs.fireworks.ai/tools-sdks/openai-compatibility.
        """
        if not self.settings.fireworks_api_key:
            raise AgentGuardError(
                "FIREWORKS_API_KEY_MISSING",
                "FIREWORKS_API_KEY is not configured.",
                {"model": model},
            )

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None else 0.0,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.settings.fireworks_api_key}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(self.settings.model_timeout_seconds)
        last_error: Exception | None = None
        started = time.perf_counter()

        for attempt in range(1, self.settings.fireworks_max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)

                latency_ms = int((time.perf_counter() - started) * 1000)
                if response.status_code >= 500 or response.status_code in {408, 429}:
                    raise httpx.HTTPStatusError(
                        "Retryable Fireworks API error",
                        request=response.request,
                        response=response,
                    )
                if response.status_code >= 400:
                    logger.warning(
                        "fireworks_non_retryable_error",
                        extra={"model": model, "status_code": response.status_code, "latency_ms": latency_ms},
                    )
                    raise AgentGuardError(
                        "FIREWORKS_API_ERROR",
                        "Fireworks API returned an error.",
                        {"status_code": response.status_code, "body": response.text[:500]},
                    )

                data = response.json()
                choice = (data.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                content = message.get("content") or ""
                usage = data.get("usage") or {}
                logger.info(
                    "fireworks_chat_completion_success",
                    extra={"model": model, "attempt": attempt, "latency_ms": latency_ms},
                )
                return ChatCompletionResult(
                    content=content,
                    model=data.get("model") or model,
                    latency_ms=latency_ms,
                    usage=TokenUsage(
                        prompt_tokens=usage.get("prompt_tokens"),
                        completion_tokens=usage.get("completion_tokens"),
                        total_tokens=usage.get("total_tokens"),
                    ),
                    reasoning_summary=message.get("reasoning_content"),
                    raw_response=data,
                )
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                logger.warning(
                    "fireworks_retryable_error",
                    extra={"model": model, "attempt": attempt, "error_type": type(exc).__name__},
                )
                if attempt >= self.settings.fireworks_max_retries:
                    break
                await asyncio.sleep(self.settings.fireworks_backoff_seconds * (2 ** (attempt - 1)))
            except ValueError as exc:
                raise AgentGuardError("FIREWORKS_MALFORMED_RESPONSE", "Fireworks returned invalid JSON.") from exc

        raise AgentGuardError(
            "FIREWORKS_API_ERROR",
            "Fireworks request failed after retries.",
            {"model": model, "error_type": type(last_error).__name__ if last_error else "unknown"},
        )
