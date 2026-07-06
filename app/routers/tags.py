"""Dashboard tag management APIs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.routers.dependencies import resolve_actor
from app.schemas.context import ActorContext
from app.schemas.tag import TagCreateRequest, TagUpdateRequest
from app.services.tag_service import TagService
from app.services.vortex_http import HTTP_CREATED, send_success_response

router = APIRouter(prefix="/api/tags", tags=["engram-tags"])


@router.get("")
async def list_tags(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(await TagService.list_tags(actor))


@router.post("", status_code=HTTP_CREATED)
async def create_tag(
    request: TagCreateRequest,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await TagService.create_tag(actor, request), status_code=HTTP_CREATED
    )


@router.patch("/{tag_id}")
async def update_tag(
    tag_id: UUID,
    request: TagUpdateRequest,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(await TagService.update_tag(actor, tag_id, request))


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: UUID,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(await TagService.delete_tag(actor, tag_id))
