"""Policy service scaffold tests."""

import pytest

from app.api.schemas import RiskLevel
from app.services.policy_service import PolicyService


@pytest.mark.asyncio
async def test_policy_service_returns_default_policies() -> None:
    """PolicyService should load the configured YAML policy response."""
    service = PolicyService()
    response = await service.list_policies()

    assert response.version
    assert len(response.policies) >= 3
    assert any(policy.severity == RiskLevel.CRITICAL for policy in response.policies)


@pytest.mark.asyncio
async def test_policy_service_loads_custom_yaml(tmp_path) -> None:
    """PolicyService should validate custom YAML policy files."""
    policy_file = tmp_path / "policies.yaml"
    policy_file.write_text(
        """
version: "test"
policies:
  - policy_id: "must_escalate"
    description: "Escalate unsafe recommendations."
    severity: "critical"
    required: true
    evaluation_prompt: "Evaluate escalation."
""",
        encoding="utf-8",
    )

    service = PolicyService(policy_path=str(policy_file))
    response = await service.list_policies()

    assert response.version == "test"
    assert response.policies[0].policy_id == "must_escalate"
    assert response.policies[0].severity == RiskLevel.CRITICAL


@pytest.mark.asyncio
async def test_policy_service_parses_quoted_required_false(tmp_path) -> None:
    """PolicyService should treat quoted false values as false."""
    policy_file = tmp_path / "policies.yaml"
    policy_file.write_text(
        """
version: "test"
policies:
  - policy_id: "optional_policy"
    description: "Optional policy."
    severity: "low"
    required: "false"
    evaluation_prompt: "Evaluate optional condition."
""",
        encoding="utf-8",
    )

    service = PolicyService(policy_path=str(policy_file))
    response = await service.list_policies()

    assert response.policies[0].required is False
