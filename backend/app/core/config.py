"""Application settings and environment loading."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Agent Guard backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Agent Guard API"
    app_version: str = "0.1.0"
    api_prefix: str = "/v1"
    environment: str = "development"
    log_level: str = "INFO"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8501", "http://127.0.0.1:8501"])

    fireworks_api_key: str | None = None
    fireworks_clinical_model: str = "accounts/fireworks/models/llama-v3p1-8b-instruct"
    fireworks_verifier_model: str = "accounts/fireworks/models/llama-v3p1-8b-instruct"
    model_timeout_seconds: int = 30
    fireworks_base_url: str = "https://api.fireworks.ai/inference/v1"
    fireworks_max_retries: int = 3
    fireworks_backoff_seconds: float = 0.75
    clinical_temperature: float = 0.2
    verifier_temperature: float = 0.0
    clinical_max_tokens: int = 900
    verifier_max_tokens: int = 1600
    grounding_threshold: float = 0.6
    hallucination_threshold: float = 0.7
    local_rocm_base_url: str = "http://localhost:8001/v1"
    local_rocm_timeout_seconds: int = 60

    database_url: str = "sqlite:///./agent_guard.db"
    policy_path: str = "app/policies/default_clinical_policies.yaml"
    enable_local_rocm: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
