"""Audit history routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_audit_service
from app.api.schemas import AuditDetailResponse, AuditListResponse, DecisionStatus, RiskLevel
from app.services.audit_service import AuditService


router = APIRouter(prefix="/audits", tags=["Audits"])


@router.get(
    "",
    response_model=AuditListResponse,
    status_code=status.HTTP_200_OK,
    summary="List audit records",
)
async def list_audits(
    decision: DecisionStatus | None = Query(default=None),
    risk_level: RiskLevel | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: AuditService = Depends(get_audit_service),
) -> AuditListResponse:
    """Return audit history."""
    return await service.list_audits(decision=decision, risk_level=risk_level, limit=limit, offset=offset)


@router.get(
    "/{audit_id}",
    response_model=AuditDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an audit record",
)
async def get_audit(
    audit_id: UUID,
    service: AuditService = Depends(get_audit_service),
) -> AuditDetailResponse:
    """Return a stored audit record."""
    return await service.get_audit(audit_id)

