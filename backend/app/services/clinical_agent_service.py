"""Clinical AI agent service."""

import json

from app.api.schemas import GenerateAndVerifyRequest
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.prompts import render_prompt
from app.llm.types import ChatCompletionResult
from app.services.llm_service import LLMService


logger = get_logger(__name__)


class ClinicalAgentService:
    """Generate clinical recommendations through the configured clinical model."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.settings = get_settings()
        self.llm_service = llm_service or LLMService()

    async def generate_recommendation(self, request: GenerateAndVerifyRequest) -> ChatCompletionResult:
        """Generate a clinical recommendation from patient context and clinician question."""
        logger.info("clinical_recommendation_requested", extra={"case_id": request.metadata.case_id})
        patient_context_json = json.dumps(request.patient_context.model_dump(), indent=2, sort_keys=True)
        prompt = render_prompt(
            "clinical_agent_prompt.txt",
            {
                "patient_context": patient_context_json,
                "clinical_question": request.clinical_question,
            },
        )
        return await self.llm_service.complete(
            model=self.settings.fireworks_clinical_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful clinical AI assistant. "
                        "Provide concise recommendations for clinician review."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self.settings.clinical_temperature,
            max_tokens=self.settings.clinical_max_tokens,
        )
