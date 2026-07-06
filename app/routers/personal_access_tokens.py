"""Dashboard Personal Access Token management APIs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.routers.dependencies import resolve_actor
from app.schemas.auth import PersonalAccessTokenCreateRequest
from app.schemas.context import ActorContext
from app.services.config_service import EngramConfigService
from app.services.personal_access_token_service import PersonalAccessTokenService
from app.services.vortex_http import HTTP_CREATED, send_success_response

router = APIRouter(
    prefix="/auth/personal-access-tokens", tags=["engram-personal-access-tokens"]
)


@router.get("/policy")
async def get_personal_access_token_policy(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    """Return PAT policy settings so the dashboard can display default/max TTL to users."""
    settings = EngramConfigService.auth()
    policy = {
        "personal_access_tokens_enabled": settings.personal_access_tokens_enabled,
        "default_ttl_seconds": settings.personal_access_token_default_ttl_seconds,
        "default_ttl_days": settings.personal_access_token_default_ttl_seconds // 86400,
        "max_ttl_seconds": settings.personal_access_token_max_ttl_seconds,
        "max_ttl_days": settings.personal_access_token_max_ttl_seconds // 86400,
    }
    return send_success_response(policy)


@router.get("")
async def list_personal_access_tokens(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await PersonalAccessTokenService.list_personal_access_tokens(actor)
    )


@router.post("", status_code=HTTP_CREATED)
async def create_personal_access_token(
    request: PersonalAccessTokenCreateRequest,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await PersonalAccessTokenService.create_personal_access_token(actor, request),
        status_code=HTTP_CREATED,
    )


@router.post("/{token_id}/revoke")
async def revoke_personal_access_token(
    token_id: UUID,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await PersonalAccessTokenService.revoke_personal_access_token(actor, token_id)
    )
