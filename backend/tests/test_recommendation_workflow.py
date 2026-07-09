"""Recommendation workflow tests with fake model services."""

from app.api.schemas import GenerateAndVerifyRequest, PatientContext
from app.llm.types import ChatCompletionResult
from app.services.audit_service import AuditService
from app.services.clinical_agent_service import ClinicalAgentService
from app.services.policy_service import PolicyService
from app.services.recommendation_service import RecommendationService
from app.services.verification_service import VerificationService
from app.verification.orchestrator import VerificationOrchestrator

from tests.test_repositories import make_session
from tests.test_verification_contracts import FakeLLMService


class FakeClinicalAgentService(ClinicalAgentService):
    """Fake clinical agent for workflow tests."""

    async def generate_recommendation(self, request):
        """Return a deterministic recommendation."""
        return ChatCompletionResult(content="Recommend clinician review.", model="fake-clinical", latency_ms=1)


async def test_generate_and_verify_workflow_persists_audit() -> None:
    """RecommendationService should complete generate, verify, decision, and audit workflow."""
    session = make_session()
    service = RecommendationService(
        clinical_agent_service=FakeClinicalAgentService(),
        verification_service=VerificationService(orchestrator=VerificationOrchestrator(llm_service=FakeLLMService())),
        audit_service=AuditService(db_session=session),
        policy_service=PolicyService(),
    )

    response = await service.generate_and_verify(
        GenerateAndVerifyRequest(
            patient_context=PatientContext(age=67, symptoms=["chest pain"]),
            clinical_question="What next?",
        )
    )

    assert response.decision == "PASS"
    assert response.model_metadata.clinical_model == "fake-clinical"
    assert response.audit_id
