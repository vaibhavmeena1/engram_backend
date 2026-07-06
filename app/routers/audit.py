"""Dashboard audit inspection APIs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.routers.dependencies import resolve_actor
from app.schemas.context import ActorContext
from app.services.audit_query_service import AuditQueryService
from app.services.vortex_http import send_success_response

router = APIRouter(prefix="/api/audit", tags=["engram-audit"])


@router.get("/memory-access-logs")
async def list_memory_access_logs(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
    action: Annotated[str | None, Query()] = None,
    memory_fact_id: Annotated[UUID | None, Query()] = None,
    proposal_id: Annotated[UUID | None, Query()] = None,
    request_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JSONResponse:
    return send_success_response(
        await AuditQueryService.list_memory_access_logs(
            actor=actor,
            action=action,
            memory_fact_id=memory_fact_id,
            proposal_id=proposal_id,
            request_id=request_id,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/memory-fact-versions")
async def list_memory_fact_versions(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
    fact_id: Annotated[UUID | None, Query()] = None,
    proposal_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JSONResponse:
    return send_success_response(
        await AuditQueryService.list_memory_fact_versions(
            actor=actor,
            fact_id=fact_id,
            proposal_id=proposal_id,
            limit=limit,
            offset=offset,
        )
    )
