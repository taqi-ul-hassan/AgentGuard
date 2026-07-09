"""Verification application service."""

from app.api.schemas import ModelMetadata, ModuleResultResponse, PolicyResultResponse
from app.core.config import get_settings
from app.core.logging import get_logger
from app.decision.decision_engine import DecisionEngine
from app.explainability.explanation_engine import ExplainabilityEngine
from app.services.types import VerificationServiceResult
from app.verification.base import VerificationInput, VerificationResult
from app.verification.orchestrator import VerificationOrchestrator


logger = get_logger(__name__)


class VerificationService:
    """Coordinate the verification pipeline and decision/explanation layers."""

    def __init__(
        self,
        orchestrator: VerificationOrchestrator | None = None,
        decision_engine: DecisionEngine | None = None,
        explainability_engine: ExplainabilityEngine | None = None,
    ) -> None:
        self.settings = get_settings()
        self.orchestrator = orchestrator or VerificationOrchestrator()
        self.decision_engine = decision_engine or DecisionEngine()
        self.explainability_engine = explainability_engine or ExplainabilityEngine()

    async def verify(self, verification_input: VerificationInput) -> VerificationServiceResult:
        """Run the verification pipeline and return decision-ready output."""
        logger.info("verification_started", extra={"clinical_question": verification_input.clinical_question[:80]})
        verification_results = await self.orchestrator.run(verification_input)
        decision = await self.decision_engine.decide(verification_input, verification_results)
        summary = await self.explainability_engine.generate_summary(verification_input, verification_results, decision)
        details = await self.explainability_engine.generate_details(verification_input, verification_results, decision)

        module_results = [
            ModuleResultResponse(
                module=result.module_name,
                status=result.status,
                severity=result.severity,
                score=result.score,
                findings=result.findings,
                evidence=result.evidence,
                rationale=result.rationale,
            )
            for result in verification_results
        ]

        policy_results: list[PolicyResultResponse] = []
        if verification_input.verifier_report:
            policy_results = [
                PolicyResultResponse(
                    policy_id=finding.policy_id,
                    status=finding.status,
                    severity=finding.severity,
                    message=finding.message,
                )
                for finding in verification_input.verifier_report.policy_verification.findings
            ]

        logger.info(
            "verification_completed",
            extra={"decision": decision.decision.value, "risk_level": decision.risk_level.value},
        )
        return VerificationServiceResult(
            decision=decision,
            summary=summary,
            details=details,
            module_results=module_results,
            policy_results=policy_results,
            verifier_report=verification_input.verifier_report,
            model_metadata=ModelMetadata(
                verifier_model=self.orchestrator.last_llm_result.model if self.orchestrator.last_llm_result else None,
                verifier_latency_ms=(
                    self.orchestrator.last_llm_result.latency_ms if self.orchestrator.last_llm_result else None
                ),
                prompt_tokens=self.orchestrator.last_llm_result.usage.prompt_tokens
                if self.orchestrator.last_llm_result
                else None,
                completion_tokens=self.orchestrator.last_llm_result.usage.completion_tokens
                if self.orchestrator.last_llm_result
                else None,
                total_tokens=self.orchestrator.last_llm_result.usage.total_tokens
                if self.orchestrator.last_llm_result
                else None,
            ),
        )
