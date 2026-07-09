"""SQLAlchemy ORM models for audit persistence."""

from datetime import datetime
from uuid import uuid4

from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.storage.database import Base


class AuditRecord(Base):
    """Audit record for a recommendation verification event."""

    __tablename__ = "audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    case_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clinical_question: Mapped[str] = mapped_column(Text, nullable=False)
    patient_context_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    policy_results_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    model_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    module_results: Mapped[list["ModuleResultRecord"]] = relationship(
        back_populates="audit",
        cascade="all, delete-orphan",
    )


class ModuleResultRecord(Base):
    """Persisted verification module result."""

    __tablename__ = "module_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    audit_id: Mapped[str] = mapped_column(String(36), ForeignKey("audits.id"), nullable=False, index=True)
    module_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    findings_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    audit: Mapped[AuditRecord] = relationship(back_populates="module_results")
