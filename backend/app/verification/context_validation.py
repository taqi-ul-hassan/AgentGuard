"""Context validation verification module."""

from app.api.schemas import ModuleStatus
from app.verification.base import BaseVerificationModule, VerificationInput, VerificationResult


class ContextValidationModule(BaseVerificationModule):
    """Verify that a recommendation is grounded in patient context."""

    module_name = "context_validation"

    async def verify(self, verification_input: VerificationInput) -> VerificationResult:
        """Parse context validation results from the shared verifier report."""
        report = self._require_report(verification_input).context_validation
        return VerificationResult(
            module_name=self.module_name,
            status=report.status or ModuleStatus.WARNING,
            score=report.grounding_score,
            findings=report.unsupported_claims,
            evidence=report.evidence,
            rationale=report.rationale,
        )
