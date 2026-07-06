"""Dashboard scope discovery APIs."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.routers.dependencies import resolve_actor
from app.schemas.context import ActorContext
from app.schemas.enums import ScopeType
from app.services.scope_service import ScopeService
from app.services.vortex_http import send_success_response

router = APIRouter(prefix="/api/scopes", tags=["engram-scopes"])


@router.get("")
async def list_scope_options(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
) -> JSONResponse:
    return send_success_response(await ScopeService.list_scope_options(actor))


@router.get("/search")
async def search_scopes(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
    query: Annotated[str | None, Query(alias="q")] = None,
    scope_type: Annotated[ScopeType | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> JSONResponse:
    return send_success_response(
        await ScopeService.search_scopes(
            actor, query=query, scope_type=scope_type, limit=limit
        )
    )


@router.get("/users")
async def search_users(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
    query: Annotated[str | None, Query(alias="q")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> JSONResponse:
    return send_success_response(
        await ScopeService.search_users(actor, query=query, limit=limit)
    )


@router.get("/organizations")
async def list_organizations(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
    query: Annotated[str | None, Query(alias="q")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> JSONResponse:
    return send_success_response(
        await ScopeService.list_organizations(actor, query=query, limit=limit)
    )


@router.get("/repositories")
async def list_repositories(
    actor: Annotated[ActorContext, Depends(resolve_actor)],
    query: Annotated[str | None, Query(alias="q")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> JSONResponse:
    return send_success_response(
        await ScopeService.list_repositories(actor, query=query, limit=limit)
    )
