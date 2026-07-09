"""Deterministic PASS / FLAG decision engine."""

from app.api.schemas import DecisionStatus, ModuleStatus, PolicyStatus, RiskLevel
from app.core.config import get_settings
from app.decision.types import DecisionOutcome
from app.verification.base import VerificationInput, VerificationResult


class DecisionEngine:
    """Aggregate verification results into a final PASS or FLAG decision."""

    def __init__(self) -> None:
        """Initialize the decision engine."""
        self.settings = get_settings()

    async def decide(
        self,
        verification_input: VerificationInput,
        verification_results: list[VerificationResult],
    ) -> DecisionOutcome:
        """Return a final Agent Guard decision using transparent deterministic rules."""
        report = verification_input.verifier_report
        reasons: list[str] = []

        if report is None:
            return DecisionOutcome(
                decision=DecisionStatus.FLAG,
                risk_level=RiskLevel.HIGH,
                confidence=0.0,
                reasons=["Verification did not complete."],
            )

        decision = DecisionStatus.PASS

        safety = report.safety_verification
        context = report.context_validation
        risk = report.confidence_risk
        policy = report.policy_verification

        if safety.critical_issue or safety.severity == RiskLevel.CRITICAL:
            decision = DecisionStatus.FLAG
            reasons.append("Critical safety issue identified.")

        mandatory_violations = [
            finding.policy_id
            for finding in policy.findings
            if finding.required and finding.status == PolicyStatus.VIOLATED
        ]
        if mandatory_violations:
            decision = DecisionStatus.FLAG
            reasons.append(f"Mandatory policy violation: {', '.join(mandatory_violations)}.")

        if context.grounding_score < self.settings.grounding_threshold:
            decision = DecisionStatus.FLAG
            reasons.append("Grounding score is below the configured threshold.")

        if safety.hallucination_risk >= self.settings.hallucination_threshold:
            decision = DecisionStatus.FLAG
            reasons.append("Hallucination risk is above the configured threshold.")

        if any(result.status == ModuleStatus.ERROR for result in verification_results):
            decision = DecisionStatus.FLAG
            reasons.append("One or more verification modules failed.")

        if not reasons:
            reasons.append("No critical safety, grounding, hallucination, or mandatory policy issues were found.")

        return DecisionOutcome(
            decision=decision,
            risk_level=risk.risk_level,
            confidence=risk.confidence,
            reasons=reasons,
        )
