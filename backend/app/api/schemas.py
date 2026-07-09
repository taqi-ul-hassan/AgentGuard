"""Pydantic schemas for Agent Guard API contracts."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DecisionStatus(StrEnum):
    """Final Agent Guard decision values."""

    PASS = "PASS"
    FLAG = "FLAG"


class ModuleStatus(StrEnum):
    """Verification module status values."""

    PASS = "PASS"
    FLAG = "FLAG"
    WARNING = "WARNING"
    ERROR = "ERROR"


class RiskLevel(StrEnum):
    """Risk levels produced by the verification pipeline."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PolicyStatus(StrEnum):
    """Policy evaluation status values."""

    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"
    NOT_EVALUATED = "NOT_EVALUATED"


class ErrorDetail(BaseModel):
    """Structured API error payload."""

    code: str = Field(..., examples=["INVALID_REQUEST"])
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Standard API error response."""

    error: ErrorDetail


class PatientContext(BaseModel):
    """Flexible patient context supplied to the clinical agent and verifier."""

    model_config = ConfigDict(extra="allow")

    age: int | None = Field(default=None, ge=0, le=130)
    sex: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    vitals: dict[str, Any] = Field(default_factory=dict)
    labs: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class RequestMetadata(BaseModel):
    """Optional metadata attached to a recommendation request."""

    model_config = ConfigDict(extra="allow")

    case_id: str | None = None
    clinician_id: str | None = None
    source_agent: str | None = None


class GenerateAndVerifyRequest(BaseModel):
    """Request for generating and verifying a clinical recommendation."""

    patient_context: PatientContext
    clinical_question: str = Field(..., min_length=1, max_length=4000)
    metadata: RequestMetadata = Field(default_factory=RequestMetadata)


class VerifyRecommendationRequest(BaseModel):
    """Request for verifying an existing recommendation."""

    patient_context: PatientContext
    clinical_question: str = Field(..., min_length=1, max_length=4000)
    recommendation: str = Field(..., min_length=1, max_length=12000)
    metadata: RequestMetadata = Field(default_factory=RequestMetadata)


class ModuleResultResponse(BaseModel):
    """Public representation of an individual verification module result."""

    module: str
    status: ModuleStatus
    severity: RiskLevel | None = None
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    findings: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    rationale: str | None = None


class PolicyResultResponse(BaseModel):
    """Public representation of a policy evaluation result."""

    policy_id: str
    status: PolicyStatus
    severity: RiskLevel | None = None
    message: str | None = None


class ModelMetadata(BaseModel):
    """Metadata for models used during request processing."""

    clinical_model: str | None = None
    verifier_model: str | None = None
    latency_ms: int | None = None
    clinical_latency_ms: int | None = None
    verifier_latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_summary: str | None = None


class RecommendationVerificationResponse(BaseModel):
    """Response returned by recommendation verification endpoints."""

    audit_id: UUID
    recommendation: str
    decision: DecisionStatus
    risk_level: RiskLevel
    confidence: float = Field(..., ge=0.0, le=1.0)
    summary: str
    module_results: list[ModuleResultResponse] = Field(default_factory=list)
    policy_results: list[PolicyResultResponse] = Field(default_factory=list)
    model_metadata: ModelMetadata = Field(default_factory=ModelMetadata)


class AuditSummary(BaseModel):
    """Summary view of an audit record."""

    id: UUID
    created_at: datetime
    case_id: str | None = None
    decision: DecisionStatus
    risk_level: RiskLevel
    confidence: float
    summary: str


class AuditListResponse(BaseModel):
    """Paginated audit response."""

    items: list[AuditSummary]
    limit: int
    offset: int
    total: int


class AuditDetailResponse(RecommendationVerificationResponse):
    """Detailed audit response."""

    created_at: datetime
    patient_context: PatientContext
    clinical_question: str


class PolicyDefinition(BaseModel):
    """Policy definition exposed by policy endpoints."""

    policy_id: str
    description: str
    severity: RiskLevel
    required: bool = True
    evaluation_prompt: str


class PolicyListResponse(BaseModel):
    """Active policy set response."""

    version: str
    policies: list[PolicyDefinition]


class PolicyReloadResponse(BaseModel):
    """Policy reload acknowledgement."""

    status: str
    version: str
    loaded_count: int
