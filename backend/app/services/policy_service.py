"""Policy loading and validation service."""

from pathlib import Path
from typing import Any

from app.api.schemas import PolicyDefinition, PolicyListResponse, PolicyReloadResponse, RiskLevel
from app.core.config import get_settings
from app.core.errors import AgentGuardError
from app.core.logging import get_logger

import yaml


logger = get_logger(__name__)


class PolicyService:
    """Load and expose configurable clinical governance policies."""

    def __init__(self, policy_path: str | None = None) -> None:
        self.settings = get_settings()
        self.policy_path = self._resolve_policy_path(policy_path or self.settings.policy_path)
        self._cached_policy_set: PolicyListResponse | None = None

    async def list_policies(self) -> PolicyListResponse:
        """Return active policy definitions from YAML."""
        if self._cached_policy_set is None:
            self._cached_policy_set = self._load_policy_file()
        return self._cached_policy_set

    async def reload_policies(self) -> PolicyReloadResponse:
        """Reload policy definitions from disk."""
        self._cached_policy_set = self._load_policy_file()
        logger.info(
            "policy_reload_completed",
            extra={"version": self._cached_policy_set.version, "loaded_count": len(self._cached_policy_set.policies)},
        )
        return PolicyReloadResponse(
            status="ok",
            version=self._cached_policy_set.version,
            loaded_count=len(self._cached_policy_set.policies),
        )

    async def get_policy_payload(self) -> list[dict[str, Any]]:
        """Return policies as dictionaries for verifier prompts."""
        policy_set = await self.list_policies()
        return [policy.model_dump(mode="json") for policy in policy_set.policies]

    async def get_policy(self, policy_id: str) -> PolicyDefinition | None:
        """Look up a policy by identifier."""
        policy_set = await self.list_policies()
        return next((policy for policy in policy_set.policies if policy.policy_id == policy_id), None)

    def _load_policy_file(self) -> PolicyListResponse:
        """Read and validate the configured policy YAML file."""
        try:
            raw = yaml.safe_load(self.policy_path.read_text(encoding="utf-8")) or {}
        except OSError as exc:
            raise AgentGuardError(
                "POLICY_LOAD_ERROR",
                "Unable to read policy configuration.",
                {"path": str(self.policy_path)},
            ) from exc
        except yaml.YAMLError as exc:
            raise AgentGuardError(
                "POLICY_LOAD_ERROR",
                "Policy configuration is not valid YAML.",
                {"path": str(self.policy_path), "error": str(exc)},
            ) from exc

        try:
            policies = [
                PolicyDefinition(
                    policy_id=str(item["policy_id"]),
                    description=str(item["description"]),
                    severity=RiskLevel(str(item["severity"]).upper()),
                    required=self._parse_required(item.get("required", True)),
                    evaluation_prompt=str(item["evaluation_prompt"]),
                )
                for item in raw.get("policies", [])
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise AgentGuardError(
                "POLICY_LOAD_ERROR",
                "Policy configuration does not match the expected schema.",
                {"path": str(self.policy_path)},
            ) from exc

        if not policies:
            raise AgentGuardError(
                "POLICY_LOAD_ERROR",
                "Policy configuration must contain at least one policy.",
                {"path": str(self.policy_path)},
            )

        version = str(raw.get("version", "unversioned"))
        logger.info("policy_load_completed", extra={"version": version, "loaded_count": len(policies)})
        return PolicyListResponse(version=version, policies=policies)

    def _resolve_policy_path(self, policy_path: str) -> Path:
        """Resolve policy path for local, Docker, and test working directories."""
        path = Path(policy_path)
        if path.is_absolute():
            return path
        candidates = [
            Path.cwd() / path,
            Path.cwd() / "backend" / path,
            Path(__file__).resolve().parents[1] / "policies" / path.name,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _parse_required(self, value: Any) -> bool:
        """Parse policy required values from YAML booleans or common strings."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() not in {"false", "0", "no", "off"}
        return bool(value)
