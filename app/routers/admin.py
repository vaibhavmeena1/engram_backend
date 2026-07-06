"""Dashboard admin inspection APIs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.routers.dependencies import resolve_actor
from app.schemas.admin import RoleAssignmentCreateRequest
from app.schemas.context import ActorContext
from app.services.admin_service import AdminService
from app.services.vortex_http import HTTP_CREATED, send_success_response

router = APIRouter(prefix="/api/admin", tags=["engram-admin"])


@router.get("/users")
async def list_users(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JSONResponse:
    return send_success_response(
        await AdminService.list_users(actor, limit=limit, offset=offset)
    )


@router.get("/roles")
async def list_roles(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(await AdminService.list_roles(actor))


@router.get("/role-assignments")
async def list_role_assignments(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JSONResponse:
    return send_success_response(
        await AdminService.list_role_assignments(actor, limit=limit, offset=offset)
    )


@router.post("/role-assignments", status_code=HTTP_CREATED)
async def create_role_assignment(
    request: RoleAssignmentCreateRequest,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await AdminService.create_role_assignment(actor, request),
        status_code=HTTP_CREATED,
    )


@router.delete("/role-assignments/{assignment_id}")
async def delete_role_assignment(
    assignment_id: UUID,
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(
        await AdminService.delete_role_assignment(actor, assignment_id)
    )
