"""Policy verification module."""

from app.api.schemas import ModuleStatus
from app.verification.base import BaseVerificationModule, VerificationInput, VerificationResult


class PolicyVerificationModule(BaseVerificationModule):
    """Evaluate recommendations against configurable governance policies."""

    module_name = "policy_verification"

    async def verify(self, verification_input: VerificationInput) -> VerificationResult:
        """Parse policy verification results from the shared verifier report."""
        report = self._require_report(verification_input).policy_verification
        findings = [
            f"{finding.policy_id}: {finding.status.value}. {finding.message}".strip()
            for finding in report.findings
        ]
        return VerificationResult(
            module_name=self.module_name,
            status=report.status or ModuleStatus.WARNING,
            findings=findings,
            evidence=[finding.policy_id for finding in report.findings],
            rationale=report.rationale,
        )
