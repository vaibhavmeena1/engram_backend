"""Dashboard memory proposal review APIs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.routers.dependencies import resolve_actor
from app.schemas.context import ActorContext
from app.schemas.enums import ProposalStatus, ProposalType, ScopeType
from app.schemas.review import ProposalApplyEditedRequest, ProposalReviewRequest
from app.services.dashboard_memory_service import DashboardMemoryService
from app.services.memory_service import MemoryService
from app.services.vortex_http import send_success_response

router = APIRouter(prefix="/api/memory-proposals", tags=["engram-memory-proposals"])


@router.get("")
async def list_memory_proposals(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
    proposal_status: Annotated[ProposalStatus | None, Query(alias="status")] = None,
    proposal_type: Annotated[ProposalType | None, Query()] = None,
    scope_type: Annotated[ScopeType | None, Query()] = None,
    scope_id: Annotated[UUID | None, Query()] = None,
    fact_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JSONResponse:
    return send_success_response(
        await DashboardMemoryService.list_proposals(
            actor=actor,
            proposal_status=proposal_status,
            proposal_type=proposal_type,
            scope_type=scope_type,
            scope_id=scope_id,
            fact_id=fact_id,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/{proposal_id}")
async def get_memory_proposal(
    proposal_id: UUID,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await DashboardMemoryService.get_proposal(actor, proposal_id)
    )


@router.post("/{proposal_id}/approve")
async def approve_memory_proposal(
    proposal_id: UUID,
    request: ProposalReviewRequest,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await MemoryService.approve_proposal(actor, proposal_id, request)
    )


@router.post("/{proposal_id}/reject")
async def reject_memory_proposal(
    proposal_id: UUID,
    request: ProposalReviewRequest,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await MemoryService.reject_proposal(actor, proposal_id, request)
    )


@router.post("/{proposal_id}/apply-edited")
async def apply_edited_memory_proposal(
    proposal_id: UUID,
    request: ProposalApplyEditedRequest,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await MemoryService.apply_edited_proposal(actor, proposal_id, request)
    )
