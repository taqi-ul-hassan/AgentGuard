"""Safety verification module."""

from app.api.schemas import ModuleStatus
from app.verification.base import BaseVerificationModule, VerificationInput, VerificationResult


class SafetyVerificationModule(BaseVerificationModule):
    """Detect unsafe, contradictory, or unsupported clinical recommendations."""

    module_name = "safety_verification"

    async def verify(self, verification_input: VerificationInput) -> VerificationResult:
        """Parse safety verification results from the shared verifier report."""
        report = self._require_report(verification_input).safety_verification
        return VerificationResult(
            module_name=self.module_name,
            status=report.status or ModuleStatus.WARNING,
            severity=report.severity,
            score=report.hallucination_risk,
            findings=report.findings,
            evidence=report.evidence,
            rationale=report.rationale,
        )
