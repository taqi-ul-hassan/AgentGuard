"""Optional local ROCm OpenAI-compatible model client adapter."""

import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AgentGuardError
from app.core.logging import get_logger
from app.llm.types import ChatCompletionResult, TokenUsage


logger = get_logger(__name__)


class LocalRocmClient:
    """Adapter for AMD ROCm-accelerated local model servers with OpenAI-compatible APIs."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.local_rocm_base_url.rstrip("/")

    async def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> ChatCompletionResult:
        """Call a local ROCm-compatible OpenAI-style chat completion endpoint."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.settings.local_rocm_timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/chat/completions", json=payload)
            latency_ms = int((time.perf_counter() - started) * 1000)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise AgentGuardError(
                "LOCAL_ROCM_API_ERROR",
                "Local ROCm model endpoint request failed.",
                {"model": model, "base_url": self.base_url},
            ) from exc
        except ValueError as exc:
            raise AgentGuardError(
                "LOCAL_ROCM_MALFORMED_RESPONSE",
                "Local ROCm endpoint returned invalid JSON.",
            ) from exc

        message = ((data.get("choices") or [{}])[0].get("message") or {})
        usage = data.get("usage") or {}
        logger.info("local_rocm_chat_completion_completed", extra={"model": model, "latency_ms": latency_ms})
        return ChatCompletionResult(
            content=message.get("content") or "",
            model=data.get("model") or model,
            latency_ms=latency_ms,
            usage=TokenUsage(
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
            ),
            raw_response=data,
        )
