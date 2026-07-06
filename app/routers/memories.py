"""Dashboard memory fact APIs."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import JSONResponse

from app.routers.dependencies import resolve_actor
from app.schemas.context import ActorContext
from app.schemas.enums import MemoryListSection, MemoryStatus, ScopeType
from app.schemas.memory import (
    MemoryCreateRequest,
    MemoryListRequest,
    MemoryStatusChangeRequest,
    MemoryUpdateProposalRequest,
)
from app.services.dashboard_memory_service import DashboardMemoryService
from app.services.memory_service import MemoryService
from app.services.vortex_http import HTTP_ACCEPTED, HTTP_CREATED, send_success_response

router = APIRouter(prefix="/api/memories", tags=["engram-memories"])


@router.get("")
async def list_memories(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
    section: Annotated[MemoryListSection | None, Query()] = None,
    scope_type: Annotated[ScopeType | None, Query()] = None,
    scope_id: Annotated[UUID | None, Query()] = None,
    org_id: Annotated[UUID | None, Query()] = None,
    repo_id: Annotated[UUID | None, Query()] = None,
    owner_user_id: Annotated[UUID | None, Query()] = None,
    memory_status: Annotated[MemoryStatus | None, Query(alias="status")] = None,
    tag: Annotated[str | None, Query()] = None,
    created_by: Annotated[UUID | None, Query()] = None,
    approved_by: Annotated[UUID | None, Query()] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
    updated_from: Annotated[datetime | None, Query()] = None,
    updated_to: Annotated[datetime | None, Query()] = None,
    query: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JSONResponse:
    request = MemoryListRequest(
        section=section,
        scope_type=scope_type,
        scope_id=scope_id,
        org_id=org_id,
        repo_id=repo_id,
        owner_user_id=owner_user_id,
        status=memory_status,
        tag=tag,
        created_by=created_by,
        approved_by=approved_by,
        created_from=created_from,
        created_to=created_to,
        updated_from=updated_from,
        updated_to=updated_to,
        query=query,
        limit=limit,
        offset=offset,
    )
    return send_success_response(
        await DashboardMemoryService.list_memories(actor, request)
    )


@router.get("/{memory_id}")
async def get_memory(
    memory_id: UUID,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await DashboardMemoryService.get_memory(actor, memory_id)
    )


@router.post("", status_code=HTTP_CREATED)
async def create_memory(
    request: MemoryCreateRequest,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await MemoryService.create_memory(actor, request), status_code=HTTP_CREATED
    )


@router.patch("/{memory_id}", status_code=HTTP_ACCEPTED)
async def propose_memory_update(
    memory_id: UUID,
    request: MemoryUpdateProposalRequest,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await DashboardMemoryService.propose_memory_update(actor, memory_id, request),
        status_code=HTTP_ACCEPTED,
    )


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: UUID,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
    request: Annotated[MemoryStatusChangeRequest | None, Body()] = None,
) -> JSONResponse:
    return send_success_response(
        await DashboardMemoryService.delete_memory(
            actor, memory_id, request or MemoryStatusChangeRequest()
        )
    )


@router.post("/{memory_id}/tags/{tag_id}")
async def attach_tag(
    memory_id: UUID,
    tag_id: UUID,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await DashboardMemoryService.attach_tag(actor, memory_id, tag_id)
    )


@router.delete("/{memory_id}/tags/{tag_id}")
async def detach_tag(
    memory_id: UUID,
    tag_id: UUID,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await DashboardMemoryService.detach_tag(actor, memory_id, tag_id)
    )
