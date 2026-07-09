"""Structured verifier JSON models and parsing helpers."""

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.api.schemas import ModuleStatus, PolicyStatus, RiskLevel
from app.core.errors import AgentGuardError


class ContextFinding(BaseModel):
    """Context grounding section returned by the verifier."""

    status: ModuleStatus = ModuleStatus.WARNING
    grounding_score: float = Field(default=0.0, ge=0.0, le=1.0)
    unsupported_claims: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    rationale: str = ""

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        """Normalize verifier status casing."""
        return str(value).upper() if value is not None else value


class SafetyFinding(BaseModel):
    """Safety section returned by the verifier."""

    status: ModuleStatus = ModuleStatus.WARNING
    severity: RiskLevel = RiskLevel.MODERATE
    critical_issue: bool = False
    hallucination_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    findings: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    rationale: str = ""

    @field_validator("status", "severity", mode="before")
    @classmethod
    def normalize_enums(cls, value: Any) -> Any:
        """Normalize verifier enum casing."""
        return str(value).upper() if value is not None else value


class PolicyFinding(BaseModel):
    """Individual policy finding returned by the verifier."""

    policy_id: str
    status: PolicyStatus = PolicyStatus.NOT_EVALUATED
    severity: RiskLevel = RiskLevel.MODERATE
    required: bool = True
    message: str = ""

    @field_validator("status", "severity", mode="before")
    @classmethod
    def normalize_enums(cls, value: Any) -> Any:
        """Normalize verifier enum casing."""
        return str(value).upper() if value is not None else value


class PolicyVerificationFinding(BaseModel):
    """Policy compliance section returned by the verifier."""

    status: ModuleStatus = ModuleStatus.WARNING
    findings: list[PolicyFinding] = Field(default_factory=list)
    rationale: str = ""

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        """Normalize verifier status casing."""
        return str(value).upper() if value is not None else value


class RiskFinding(BaseModel):
    """Confidence and risk section returned by the verifier."""

    risk_level: RiskLevel = RiskLevel.MODERATE
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = ""

    @field_validator("risk_level", mode="before")
    @classmethod
    def normalize_risk(cls, value: Any) -> Any:
        """Normalize verifier risk casing."""
        return str(value).upper() if value is not None else value


class ExplanationFinding(BaseModel):
    """Explanation section returned by the verifier."""

    short: str = ""
    detailed: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class VerifierReport(BaseModel):
    """Complete structured report returned by the single verifier LLM call."""

    context_validation: ContextFinding = Field(default_factory=ContextFinding)
    safety_verification: SafetyFinding = Field(default_factory=SafetyFinding)
    policy_verification: PolicyVerificationFinding = Field(default_factory=PolicyVerificationFinding)
    confidence_risk: RiskFinding = Field(default_factory=RiskFinding)
    explanation: ExplanationFinding = Field(default_factory=ExplanationFinding)

    @field_validator("context_validation", mode="before")
    @classmethod
    def default_context(cls, value: Any) -> Any:
        """Normalize missing context sections."""
        return value or {}


def parse_verifier_report(raw_content: str) -> VerifierReport:
    """Parse and validate verifier JSON, accepting fenced JSON when necessary."""
    content = raw_content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        content = fenced.group(1).strip()

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AgentGuardError(
            "MALFORMED_VERIFIER_JSON",
            "Verifier model returned malformed JSON.",
            {"error": str(exc), "preview": raw_content[:500]},
        ) from exc

    try:
        return VerifierReport.model_validate(payload)
    except ValidationError as exc:
        raise AgentGuardError(
            "INVALID_VERIFIER_JSON",
            "Verifier model returned JSON that does not match the expected schema.",
            {"errors": exc.errors()},
        ) from exc
