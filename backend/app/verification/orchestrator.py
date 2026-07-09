"""Verification pipeline orchestrator."""

import json

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.prompts import render_prompt
from app.services.llm_service import LLMService
from app.llm.types import ChatCompletionResult
from app.verification.base import BaseVerificationModule, VerificationInput, VerificationResult
from app.verification.confidence_risk import ConfidenceRiskModule
from app.verification.context_validation import ContextValidationModule
from app.verification.policy_verification import PolicyVerificationModule
from app.verification.safety_verification import SafetyVerificationModule
from app.verification.verifier_models import parse_verifier_report


logger = get_logger(__name__)


class VerificationOrchestrator:
    """Coordinate verification modules through a shared interface."""

    def __init__(
        self,
        modules: list[BaseVerificationModule] | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.llm_service = llm_service or LLMService()
        self.last_llm_result: ChatCompletionResult | None = None
        self.modules = modules or [
            ContextValidationModule(),
            SafetyVerificationModule(),
            PolicyVerificationModule(),
            ConfidenceRiskModule(),
        ]

    async def run(self, verification_input: VerificationInput) -> list[VerificationResult]:
        """Run the single verifier LLM call and parse the result through all modules."""
        logger.info("verification_orchestrator_started", extra={"module_count": len(self.modules)})
        verifier_prompt = render_prompt(
            "verifier_system_prompt.txt",
            {
                "patient_context": json.dumps(verification_input.patient_context, indent=2, sort_keys=True),
                "clinical_question": verification_input.clinical_question,
                "recommendation": verification_input.recommendation,
                "policies": json.dumps(verification_input.policies, indent=2, sort_keys=True),
            },
        )
        llm_result = await self.llm_service.complete(
            model=self.settings.fireworks_verifier_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a clinical safety verifier. Return only valid JSON.",
                },
                {"role": "user", "content": verifier_prompt},
            ],
            temperature=self.settings.verifier_temperature,
            max_tokens=self.settings.verifier_max_tokens,
            response_format={"type": "json_object"},
        )
        self.last_llm_result = llm_result

        report = parse_verifier_report(llm_result.content)
        verification_input.verifier_report = report
        results: list[VerificationResult] = []
        for module in self.modules:
            result = await module.verify(verification_input)
            results.append(result)
        return results
