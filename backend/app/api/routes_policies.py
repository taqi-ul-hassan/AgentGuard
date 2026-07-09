"""Policy management routes."""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_policy_service
from app.api.schemas import PolicyListResponse, PolicyReloadResponse
from app.services.policy_service import PolicyService


router = APIRouter(prefix="/policies", tags=["Policies"])


@router.get(
    "",
    response_model=PolicyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List active policies",
)
async def list_policies(service: PolicyService = Depends(get_policy_service)) -> PolicyListResponse:
    """Return active policy definitions."""
    return await service.list_policies()


@router.post(
    "/reload",
    response_model=PolicyReloadResponse,
    status_code=status.HTTP_200_OK,
    summary="Reload policies from disk",
)
async def reload_policies(service: PolicyService = Depends(get_policy_service)) -> PolicyReloadResponse:
    """Reload policy definitions from disk."""
    return await service.reload_policies()
