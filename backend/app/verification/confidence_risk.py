"""Confidence and risk assessment module."""

from app.api.schemas import ModuleStatus, RiskLevel
from app.verification.base import BaseVerificationModule, VerificationInput, VerificationResult


class ConfidenceRiskModule(BaseVerificationModule):
    """Estimate confidence and assign interpretable risk level."""

    module_name = "confidence_risk"

    async def verify(self, verification_input: VerificationInput) -> VerificationResult:
        """Parse confidence and risk results from the shared verifier report."""
        report = self._require_report(verification_input).confidence_risk
        return VerificationResult(
            module_name=self.module_name,
            status=ModuleStatus.PASS,
            severity=report.risk_level or RiskLevel.MODERATE,
            score=report.confidence,
            findings=[report.rationale] if report.rationale else [],
            rationale=report.rationale,
        )
