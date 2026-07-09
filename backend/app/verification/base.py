"""Verification module interfaces and shared models."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.api.schemas import ModuleStatus, RiskLevel
from app.verification.verifier_models import VerifierReport


class VerificationInput(BaseModel):
    """Input shared by all verification modules."""

    patient_context: dict[str, Any]
    clinical_question: str
    recommendation: str
    policies: list[dict[str, Any]] = Field(default_factory=list)
    previous_module_results: list["VerificationResult"] = Field(default_factory=list)
    verifier_report: VerifierReport | None = None


class VerificationResult(BaseModel):
    """Normalized output shared by all verification modules."""

    module_name: str
    status: ModuleStatus
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    severity: RiskLevel | None = None
    findings: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    rationale: str | None = None


class BaseVerificationModule(ABC):
    """Base interface for all verification modules."""

    module_name: str

    @abstractmethod
    async def verify(self, verification_input: VerificationInput) -> VerificationResult:
        """Verify a recommendation and return a normalized result."""

    def _require_report(self, verification_input: VerificationInput) -> VerifierReport:
        """Return the shared verifier report or fail loudly for orchestration bugs."""
        if verification_input.verifier_report is None:
            msg = "Verifier report is required before module parsing."
            raise RuntimeError(msg)
        return verification_input.verifier_report
