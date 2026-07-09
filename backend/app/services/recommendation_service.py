"""Recommendation application service."""

from uuid import uuid4

from app.api.schemas import (
    DecisionStatus,
    GenerateAndVerifyRequest,
    ModelMetadata,
    RecommendationVerificationResponse,
    RiskLevel,
    VerifyRecommendationRequest,
)
from app.core.config import get_settings
from app.core.errors import AgentGuardError
from app.core.logging import get_logger
from app.llm.types import ChatCompletionResult, TokenUsage
from app.services.audit_service import AuditService
from app.services.clinical_agent_service import ClinicalAgentService
from app.services.policy_service import PolicyService
from app.services.verification_service import VerificationService
from app.verification.base import VerificationInput


logger = get_logger(__name__)


class RecommendationService:
    """Coordinate recommendation generation, verification, and audit persistence."""

    def __init__(
        self,
        clinical_agent_service: ClinicalAgentService | None = None,
        verification_service: VerificationService | None = None,
        audit_service: AuditService | None = None,
        policy_service: PolicyService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.clinical_agent_service = clinical_agent_service or ClinicalAgentService()
        self.verification_service = verification_service or VerificationService()
        self.audit_service = audit_service or AuditService()
        self.policy_service = policy_service or PolicyService()

    async def generate_and_verify(self, request: GenerateAndVerifyRequest) -> RecommendationVerificationResponse:
        """Generate a recommendation, verify it, persist an audit, and return the response."""
        logger.info("generate_and_verify_requested", extra={"case_id": request.metadata.case_id})
        try:
            clinical_result = await self.clinical_agent_service.generate_recommendation(request)
            recommendation = clinical_result.content
        except AgentGuardError as exc:
            logger.warning("clinical_generation_failed", extra={"code": exc.code})
            clinical_result = self._failed_clinical_result(str(exc))
            recommendation = "Clinical AI generation failed. Agent Guard flagged this request for clinician review."

        response = await self._verify_and_build_response(
            patient_context=request.patient_context.model_dump(mode="json"),
            clinical_question=request.clinical_question,
            recommendation=recommendation,
            clinical_result=clinical_result,
        )
        await self._persist_audit_safely(
            response=response,
            patient_context=request.patient_context,
            clinical_question=request.clinical_question,
            case_id=request.metadata.case_id,
        )
        return response

    async def verify_existing(self, request: VerifyRecommendationRequest) -> RecommendationVerificationResponse:
        """Verify a supplied recommendation, persist an audit, and return the response."""
        logger.info("verify_existing_requested", extra={"case_id": request.metadata.case_id})
        response = await self._verify_and_build_response(
            patient_context=request.patient_context.model_dump(mode="json"),
            clinical_question=request.clinical_question,
            recommendation=request.recommendation,
            clinical_result=None,
        )
        await self._persist_audit_safely(
            response=response,
            patient_context=request.patient_context,
            clinical_question=request.clinical_question,
            case_id=request.metadata.case_id,
        )
        return response

    async def _verify_and_build_response(
        self,
        *,
        patient_context: dict,
        clinical_question: str,
        recommendation: str,
        clinical_result: ChatCompletionResult | None,
    ) -> RecommendationVerificationResponse:
        """Run Agent Guard verification and build the public response."""
        try:
            policies = await self.policy_service.get_policy_payload()
            verification_input = VerificationInput(
                patient_context=patient_context,
                clinical_question=clinical_question,
                recommendation=recommendation,
                policies=policies,
            )
            verification = await self.verification_service.verify(verification_input)
            model_metadata = verification.model_metadata
            if clinical_result:
                model_metadata.clinical_model = clinical_result.model
                model_metadata.clinical_latency_ms = clinical_result.latency_ms
                model_metadata.reasoning_summary = clinical_result.reasoning_summary
                model_metadata.prompt_tokens = self._sum_optional(
                    model_metadata.prompt_tokens,
                    clinical_result.usage.prompt_tokens,
                )
                model_metadata.completion_tokens = self._sum_optional(
                    model_metadata.completion_tokens,
                    clinical_result.usage.completion_tokens,
                )
                model_metadata.total_tokens = self._sum_optional(
                    model_metadata.total_tokens,
                    clinical_result.usage.total_tokens,
                )
            model_metadata.latency_ms = self._sum_optional(
                model_metadata.clinical_latency_ms,
                model_metadata.verifier_latency_ms,
            )
            return RecommendationVerificationResponse(
                audit_id=uuid4(),
                recommendation=recommendation,
                decision=verification.decision.decision,
                risk_level=verification.decision.risk_level,
                confidence=verification.decision.confidence,
                summary=verification.summary,
                module_results=verification.module_results,
                policy_results=verification.policy_results,
                model_metadata=model_metadata,
            )
        except AgentGuardError as exc:
            logger.warning("verification_failed", extra={"code": exc.code})
            return self._flagged_failure_response(recommendation, exc.message)

    async def _persist_audit_safely(
        self,
        *,
        response: RecommendationVerificationResponse,
        patient_context,
        clinical_question: str,
        case_id: str | None,
    ) -> None:
        """Persist audits without crashing the API response path."""
        try:
            await self.audit_service.create_audit(
                response=response,
                patient_context=patient_context,
                clinical_question=clinical_question,
                case_id=case_id,
            )
        except AgentGuardError as exc:
            logger.warning("audit_persistence_failed", extra={"code": exc.code, "audit_id": str(response.audit_id)})

    def _flagged_failure_response(self, recommendation: str, message: str) -> RecommendationVerificationResponse:
        """Build a FLAG response when verification cannot be completed."""
        return RecommendationVerificationResponse(
            audit_id=uuid4(),
            recommendation=recommendation,
            decision=DecisionStatus.FLAG,
            risk_level=RiskLevel.HIGH,
            confidence=0.0,
            summary=f"Agent Guard could not complete verification: {message}",
            module_results=[],
            policy_results=[],
            model_metadata=ModelMetadata(
                clinical_model=self.settings.fireworks_clinical_model,
                verifier_model=self.settings.fireworks_verifier_model,
            ),
        )

    def _failed_clinical_result(self, message: str) -> ChatCompletionResult:
        """Represent failed clinical generation as metadata for a safe FLAG response."""
        return ChatCompletionResult(
            content=message,
            model=self.settings.fireworks_clinical_model,
            latency_ms=0,
            usage=TokenUsage(),
        )

    def _sum_optional(self, first: int | None, second: int | None) -> int | None:
        """Sum optional integer metadata fields."""
        values = [value for value in (first, second) if value is not None]
        return sum(values) if values else None
