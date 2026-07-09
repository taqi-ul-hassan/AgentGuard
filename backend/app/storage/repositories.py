"""Repository interfaces for persistence access."""

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.api.schemas import DecisionStatus, RiskLevel
from app.core.errors import AgentGuardError
from app.core.logging import get_logger
from app.storage.models import AuditRecord


logger = get_logger(__name__)


class AuditRepository:
    """Repository for audit records and module results."""

    def __init__(self, db_session: Session | None = None) -> None:
        self.db_session = db_session

    def add(self, audit: AuditRecord) -> AuditRecord:
        """Persist an audit record."""
        if self.db_session is None:
            raise AgentGuardError("DATABASE_ERROR", "Database session is not available.")
        try:
            self.db_session.add(audit)
            self.db_session.commit()
            self.db_session.refresh(audit)
        except Exception as exc:
            self.db_session.rollback()
            raise AgentGuardError("AUDIT_WRITE_FAILED", "Unable to persist audit record.") from exc
        logger.info("audit_repository_add_completed", extra={"audit_id": audit.id})
        return audit

    def list(
        self,
        *,
        limit: int,
        offset: int,
        decision: DecisionStatus | None = None,
        risk_level: RiskLevel | None = None,
    ) -> list[AuditRecord]:
        """List audit records."""
        if self.db_session is None:
            raise AgentGuardError("DATABASE_ERROR", "Database session is not available.")
        statement: Select[tuple[AuditRecord]] = select(AuditRecord).order_by(AuditRecord.created_at.desc())
        if decision:
            statement = statement.where(AuditRecord.decision == decision.value)
        if risk_level:
            statement = statement.where(AuditRecord.risk_level == risk_level.value)
        statement = statement.limit(limit).offset(offset)
        logger.info("audit_repository_list_completed", extra={"limit": limit, "offset": offset})
        return list(self.db_session.scalars(statement).all())

    def count(
        self,
        *,
        decision: DecisionStatus | None = None,
        risk_level: RiskLevel | None = None,
    ) -> int:
        """Count audit records matching optional filters."""
        if self.db_session is None:
            raise AgentGuardError("DATABASE_ERROR", "Database session is not available.")
        statement = select(func.count()).select_from(AuditRecord)
        if decision:
            statement = statement.where(AuditRecord.decision == decision.value)
        if risk_level:
            statement = statement.where(AuditRecord.risk_level == risk_level.value)
        return int(self.db_session.scalar(statement) or 0)

    def get(self, audit_id: UUID) -> AuditRecord | None:
        """Retrieve a single audit record."""
        if self.db_session is None:
            raise AgentGuardError("DATABASE_ERROR", "Database session is not available.")
        logger.info("audit_repository_get_requested", extra={"audit_id": str(audit_id)})
        return self.db_session.get(AuditRecord, str(audit_id))
