"""Prompt template loading utilities."""

from functools import lru_cache
from pathlib import Path
from string import Template
from typing import Any

from app.core.errors import AgentGuardError


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


@lru_cache
def load_prompt_template(name: str) -> str:
    """Load a prompt template from the application prompt directory."""
    path = PROMPT_DIR / name
    if not path.exists():
        raise AgentGuardError("PROMPT_NOT_FOUND", f"Prompt template not found: {name}", {"path": str(path)})
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, variables: dict[str, Any]) -> str:
    """Render a prompt template with safe string substitution."""
    template = Template(load_prompt_template(name))
    normalized = {key: str(value) for key, value in variables.items()}
    return template.safe_substitute(normalized)

