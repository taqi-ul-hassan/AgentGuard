"""Internal decision models."""

from pydantic import BaseModel, Field

from app.api.schemas import DecisionStatus, RiskLevel


class DecisionOutcome(BaseModel):
    """Deterministic output of the decision engine."""

    decision: DecisionStatus
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)

