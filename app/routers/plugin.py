"""Authenticated lifecycle endpoints for Engram agent plugins."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.routers.dependencies import resolve_mcp_actor, resolve_mcp_repository_context
from app.schemas.context import ActorContext
from app.schemas.plugin import PluginSessionStatusResponse
from app.schemas.repository import RepositoryContext
from app.services.plugin_session_service import PluginSessionService

router = APIRouter(prefix="/api/plugin", tags=["engram-plugin"])


@router.get("/session-status")
async def get_plugin_session_status(
    actor: Annotated[ActorContext, Depends(resolve_mcp_actor)],
    repository_context: Annotated[
        RepositoryContext | None, Depends(resolve_mcp_repository_context)
    ],
) -> PluginSessionStatusResponse:
    """Return repository resolution and approved repository-memory count."""
    return await PluginSessionService.get_session_status(actor, repository_context)