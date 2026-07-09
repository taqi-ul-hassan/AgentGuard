"""Clinician-facing explainability engine."""

from app.decision.types import DecisionOutcome
from app.verification.base import VerificationInput, VerificationResult


class ExplainabilityEngine:
    """Generate clinician-friendly explanations from verification findings."""

    def __init__(self) -> None:
        """Initialize the explainability engine."""

    async def generate_summary(
        self,
        verification_input: VerificationInput,
        verification_results: list[VerificationResult],
        decision: DecisionOutcome,
    ) -> str:
        """Generate a short clinician-facing explanation without hidden reasoning."""
        report = verification_input.verifier_report
        if report and report.explanation.short:
            return report.explanation.short
        return " ".join(decision.reasons)

    async def generate_details(
        self,
        verification_input: VerificationInput,
        verification_results: list[VerificationResult],
        decision: DecisionOutcome,
    ) -> list[str]:
        """Generate detailed clinician-facing explanation bullets."""
        report = verification_input.verifier_report
        details: list[str] = []
        if report:
            details.extend(report.explanation.detailed)
        details.extend(decision.reasons)
        for result in verification_results:
            details.extend(result.findings)
        return list(dict.fromkeys(item for item in details if item))

    async def extract_evidence(self, verification_input: VerificationInput) -> list[str]:
        """Extract evidence snippets from the verifier report."""
        report = verification_input.verifier_report
        if not report:
            return []
        evidence = []
        evidence.extend(report.context_validation.evidence)
        evidence.extend(report.safety_verification.evidence)
        evidence.extend(report.explanation.evidence)
        return list(dict.fromkeys(item for item in evidence if item))
