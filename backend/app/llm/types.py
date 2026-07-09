"""Shared LLM response models."""

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token usage metadata returned by an LLM provider."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ChatCompletionResult(BaseModel):
    """Normalized chat completion result."""

    content: str
    model: str
    latency_ms: int
    usage: TokenUsage = Field(default_factory=TokenUsage)
    reasoning_summary: str | None = None
    raw_response: dict | None = None

