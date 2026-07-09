"""Recommendation generation and verification routes."""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_recommendation_service
from app.api.schemas import (
    GenerateAndVerifyRequest,
    RecommendationVerificationResponse,
    VerifyRecommendationRequest,
)
from app.services.recommendation_service import RecommendationService


router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.post(
    "/generate-and-verify",
    response_model=RecommendationVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate and verify a clinical recommendation",
)
async def generate_and_verify_recommendation(
    request: GenerateAndVerifyRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationVerificationResponse:
    """Generate a clinical recommendation and return Agent Guard verification."""
    return await service.generate_and_verify(request)


@router.post(
    "/verify",
    response_model=RecommendationVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify an existing clinical recommendation",
)
async def verify_recommendation(
    request: VerifyRecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationVerificationResponse:
    """Verify a supplied recommendation with Agent Guard."""
    return await service.verify_existing(request)

