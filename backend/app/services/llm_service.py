"""LLM service facade."""

from app.core.logging import get_logger
from app.llm.fireworks_client import FireworksClient
from app.llm.types import ChatCompletionResult


logger = get_logger(__name__)


class LLMService:
    """Provide model invocation abstractions for hosted and local LLM backends."""

    def __init__(self, fireworks_client: FireworksClient | None = None) -> None:
        self.fireworks_client = fireworks_client or FireworksClient()

    async def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: dict | None = None,
    ) -> ChatCompletionResult:
        """Return an LLM completion through the configured hosted provider."""
        logger.info("llm_completion_requested", extra={"model": model, "message_count": len(messages)})
        return await self.fireworks_client.chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
