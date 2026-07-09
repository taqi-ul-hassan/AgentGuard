"""FastAPI dependency providers."""

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.services.audit_service import AuditService
from app.services.clinical_agent_service import ClinicalAgentService
from app.services.policy_service import PolicyService
from app.services.recommendation_service import RecommendationService
from app.services.verification_service import VerificationService
from app.storage.database import get_session


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session for request-scoped dependencies."""
    yield from get_session()


def get_policy_service() -> PolicyService:
    """Return the policy service dependency."""
    return PolicyService()


def get_audit_service(db: Session = Depends(get_db_session)) -> AuditService:
    """Return the audit service dependency."""
    return AuditService(db_session=db)


def get_verification_service() -> VerificationService:
    """Return the verification service dependency."""
    return VerificationService()


def get_clinical_agent_service() -> ClinicalAgentService:
    """Return the clinical agent service dependency."""
    return ClinicalAgentService()


def get_recommendation_service(
    clinical_agent_service: ClinicalAgentService = Depends(get_clinical_agent_service),
    verification_service: VerificationService = Depends(get_verification_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> RecommendationService:
    """Return the recommendation service dependency."""
    return RecommendationService(
        clinical_agent_service=clinical_agent_service,
        verification_service=verification_service,
        audit_service=audit_service,
    )
