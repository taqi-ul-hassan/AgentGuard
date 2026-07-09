"""Internal service result models."""

from pydantic import BaseModel, Field

from app.api.schemas import ModelMetadata, ModuleResultResponse, PolicyResultResponse
from app.decision.types import DecisionOutcome
from app.verification.verifier_models import VerifierReport


class VerificationServiceResult(BaseModel):
    """Complete internal verification workflow output."""

    decision: DecisionOutcome
    summary: str
    details: list[str] = Field(default_factory=list)
    module_results: list[ModuleResultResponse] = Field(default_factory=list)
    policy_results: list[PolicyResultResponse] = Field(default_factory=list)
    verifier_report: VerifierReport | None = None
    model_metadata: ModelMetadata = Field(default_factory=ModelMetadata)
