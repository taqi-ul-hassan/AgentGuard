"""Verification module contract tests."""

import pytest

from app.api.schemas import ModuleStatus
from app.llm.types import ChatCompletionResult
from app.verification.base import VerificationInput
from app.verification.orchestrator import VerificationOrchestrator
from app.verification.verifier_models import parse_verifier_report


class FakeLLMService:
    """Fake verifier LLM service for orchestrator tests."""

    async def complete(self, **kwargs) -> ChatCompletionResult:
        """Return valid verifier JSON."""
        return ChatCompletionResult(
            content="""
{
  "context_validation": {
    "status": "PaSs",
    "grounding_score": 0.9,
    "unsupported_claims": [],
    "evidence": ["Patient context supports recommendation."],
    "rationale": "Grounded."
  },
  "safety_verification": {
    "status": "PaSs",
    "severity": "low",
    "critical_issue": false,
    "hallucination_risk": 0.1,
    "findings": [],
    "evidence": [],
    "rationale": "No safety issue."
  },
  "policy_verification": {
    "status": "PaSs",
    "findings": [],
    "rationale": "No policy issue."
  },
  "confidence_risk": {
    "risk_level": "low",
    "confidence": 0.85,
    "rationale": "High confidence."
  },
  "explanation": {
    "short": "No material safety issue found.",
    "detailed": ["Recommendation is grounded."],
    "evidence": ["Patient context supports recommendation."]
  }
}
""",
            model="fake-verifier",
            latency_ms=1,
        )


@pytest.mark.asyncio
async def test_verification_orchestrator_runs_modules_from_shared_verifier_report() -> None:
    """The orchestrator should run all modules through one shared verifier call."""
    orchestrator = VerificationOrchestrator(llm_service=FakeLLMService())
    verification_input = VerificationInput(
        patient_context={},
        clinical_question="Placeholder question?",
        recommendation="Placeholder recommendation.",
    )

    results = await orchestrator.run(verification_input)

    assert len(results) == 4
    assert results[0].status == ModuleStatus.PASS
    assert verification_input.verifier_report is not None


def test_parse_verifier_report_accepts_fenced_json() -> None:
    """Verifier parser should accept fenced JSON from models."""
    report = parse_verifier_report(
        """```json
{"context_validation":{"status":"PASS","grounding_score":0.7},"confidence_risk":{"risk_level":"LOW","confidence":0.8}}
```"""
    )

    assert report.context_validation.grounding_score == 0.7
