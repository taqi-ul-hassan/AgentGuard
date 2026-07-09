"""Audit persistence service."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.api.schemas import (
    AuditDetailResponse,
    AuditListResponse,
    AuditSummary,
    DecisionStatus,
    PatientContext,
    RecommendationVerificationResponse,
    RiskLevel,
)
from app.core.errors import AgentGuardError
from app.core.logging import get_logger
from app.storage.models import AuditRecord, ModuleResultRecord
from app.storage.repositories import AuditRepository


logger = get_logger(__name__)


class AuditService:
    """Persist and retrieve Agent Guard audit records."""

    def __init__(self, db_session: Session | None = None, repository: AuditRepository | None = None) -> None:
        self.db_session = db_session
        self.repository = repository or AuditRepository(db_session=db_session)

    async def create_audit(
        self,
        *,
        response: RecommendationVerificationResponse,
        patient_context: PatientContext,
        clinical_question: str,
        case_id: str | None = None,
    ) -> UUID:
        """Persist an audit record and return its ID."""
        audit = AuditRecord(
            id=str(response.audit_id),
            case_id=case_id,
            clinical_question=clinical_question,
            patient_context_json=patient_context.model_dump(mode="json"),
            recommendation=response.recommendation,
            decision=response.decision.value,
            risk_level=response.risk_level.value,
            confidence=response.confidence,
            summary=response.summary,
            policy_results_json=[item.model_dump(mode="json") for item in response.policy_results],
            model_metadata_json=response.model_metadata.model_dump(mode="json"),
        )
        audit.module_results = [
            ModuleResultRecord(
                audit_id=str(response.audit_id),
                module_name=item.module,
                status=item.status.value,
                severity=item.severity.value if item.severity else None,
                score=item.score,
                findings_json={
                    "findings": item.findings,
                    "evidence": item.evidence,
                    "rationale": item.rationale,
                },
            )
            for item in response.module_results
        ]
        self.repository.add(audit)
        logger.info("audit_create_completed", extra={"audit_id": str(response.audit_id)})
        return response.audit_id

    async def list_audits(
        self,
        decision: DecisionStatus | None,
        risk_level: RiskLevel | None,
        limit: int,
        offset: int,
    ) -> AuditListResponse:
        """Return paginated audit summaries."""
        logger.info("audit_list_requested", extra={"decision": decision, "risk_level": risk_level})
        records = self.repository.list(limit=limit, offset=offset, decision=decision, risk_level=risk_level)
        total = self.repository.count(decision=decision, risk_level=risk_level)
        return AuditListResponse(
            items=[
                AuditSummary(
                    id=UUID(record.id),
                    created_at=record.created_at,
                    case_id=record.case_id,
                    decision=DecisionStatus(record.decision),
                    risk_level=RiskLevel(record.risk_level),
                    confidence=record.confidence,
                    summary=record.summary,
                )
                for record in records
            ],
            limit=limit,
            offset=offset,
            total=total,
        )

    async def get_audit(self, audit_id: UUID) -> AuditDetailResponse:
        """Return a single audit record."""
        logger.info("audit_get_requested", extra={"audit_id": str(audit_id)})
        record = self.repository.get(audit_id)
        if record is None:
            raise AgentGuardError("AUDIT_NOT_FOUND", "Audit record was not found.", {"audit_id": str(audit_id)})
        return AuditDetailResponse(
            audit_id=UUID(record.id),
            recommendation=record.recommendation,
            decision=DecisionStatus(record.decision),
            risk_level=RiskLevel(record.risk_level),
            confidence=record.confidence,
            summary=record.summary,
            module_results=[
                {
                    "module": item.module_name,
                    "status": item.status,
                    "severity": item.severity,
                    "score": item.score,
                    "findings": item.findings_json.get("findings", []),
                    "evidence": item.findings_json.get("evidence", []),
                    "rationale": item.findings_json.get("rationale"),
                }
                for item in record.module_results
            ],
            policy_results=record.policy_results_json,
            model_metadata=record.model_metadata_json,
            created_at=record.created_at,
            patient_context=PatientContext.model_validate(record.patient_context_json),
            clinical_question=record.clinical_question,
        )
