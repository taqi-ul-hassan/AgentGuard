"""Repository and audit persistence tests."""

from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.schemas import DecisionStatus, ModelMetadata, PatientContext, RecommendationVerificationResponse, RiskLevel
from app.services.audit_service import AuditService
from app.storage.database import Base


def make_session():
    """Create an isolated in-memory SQLite session."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)()


async def persist_sample_audit(service: AuditService):
    """Persist a sample audit record."""
    response = RecommendationVerificationResponse(
        audit_id=uuid4(),
        recommendation="Review patient urgently.",
        decision=DecisionStatus.FLAG,
        risk_level=RiskLevel.HIGH,
        confidence=0.4,
        summary="Flagged for test.",
        module_results=[],
        policy_results=[],
        model_metadata=ModelMetadata(clinical_model="clinical", verifier_model="verifier"),
    )
    await service.create_audit(
        response=response,
        patient_context=PatientContext(age=70),
        clinical_question="What next?",
        case_id="case-1",
    )
    return response


async def test_audit_service_persists_and_retrieves_audit() -> None:
    """AuditService should insert, list, and retrieve audit records."""
    session = make_session()
    service = AuditService(db_session=session)
    response = await persist_sample_audit(service)

    listing = await service.list_audits(decision=None, risk_level=None, limit=10, offset=0)
    detail = await service.get_audit(response.audit_id)

    assert listing.total == 1
    assert detail.audit_id == response.audit_id
    assert detail.patient_context.age == 70
