"""Decision engine scaffold tests."""

import pytest

from app.api.schemas import ModuleStatus, PolicyStatus, RiskLevel
from app.decision.decision_engine import DecisionEngine
from app.verification.base import VerificationInput, VerificationResult
from app.verification.verifier_models import (
    ContextFinding,
    PolicyFinding,
    PolicyVerificationFinding,
    RiskFinding,
    SafetyFinding,
    VerifierReport,
)


@pytest.mark.asyncio
async def test_decision_engine_flags_critical_safety() -> None:
    """Critical safety findings should deterministically FLAG."""
    engine = DecisionEngine()
    verification_input = VerificationInput(
        patient_context={},
        clinical_question="Placeholder question?",
        recommendation="Placeholder recommendation.",
        verifier_report=VerifierReport(
            context_validation=ContextFinding(status=ModuleStatus.PASS, grounding_score=0.95),
            safety_verification=SafetyFinding(
                status=ModuleStatus.FLAG,
                severity=RiskLevel.CRITICAL,
                critical_issue=True,
            ),
            confidence_risk=RiskFinding(risk_level=RiskLevel.CRITICAL, confidence=0.2),
        ),
    )

    decision = await engine.decide(verification_input, [])

    assert decision.decision == "FLAG"
    assert decision.risk_level == RiskLevel.CRITICAL


@pytest.mark.asyncio
async def test_decision_engine_passes_clean_report() -> None:
    """Clean verifier reports should PASS."""
    engine = DecisionEngine()
    verification_input = VerificationInput(
        patient_context={},
        clinical_question="Question?",
        recommendation="Recommendation.",
        verifier_report=VerifierReport(
            context_validation=ContextFinding(status=ModuleStatus.PASS, grounding_score=0.92),
            safety_verification=SafetyFinding(
                status=ModuleStatus.PASS,
                severity=RiskLevel.LOW,
                hallucination_risk=0.1,
            ),
            policy_verification=PolicyVerificationFinding(
                status=ModuleStatus.PASS,
                findings=[
                    PolicyFinding(
                        policy_id="p1",
                        status=PolicyStatus.SATISFIED,
                        severity=RiskLevel.LOW,
                        required=True,
                    )
                ],
            ),
            confidence_risk=RiskFinding(risk_level=RiskLevel.LOW, confidence=0.88),
        ),
    )

    decision = await engine.decide(
        verification_input,
        [VerificationResult(module_name="context_validation", status=ModuleStatus.PASS)],
    )

    assert decision.decision == "PASS"
