"""Shared FastAPI dependencies for Engram routers."""

from typing import Annotated

from fastapi import Depends, Request

from app.schemas.context import ActorContext
from app.schemas.repository import RepositoryContext, RepositoryRemoteInput
from app.services.actor_context import ActorContextService
from app.services.auth_context_service import AuthContextService
from app.services.mcp_context_service import McpContextService
from app.services.repository_resolver import RepositoryResolver

REPOSITORY_ID_HEADER = "x-engram-repository-id"
REPOSITORY_ORIGIN_URL_HEADER = "x-engram-repository-origin-url"
REPOSITORY_PATH_HEADER = "x-engram-repository-path"
REPOSITORY_BRANCH_HEADER = "x-engram-repository-branch"
REPOSITORY_COMMIT_HEADER = "x-engram-repository-commit"


async def resolve_actor(request: Request) -> ActorContext:
    """Resolve and store the authenticated actor for a dashboard/API request."""
    return await AuthContextService.resolve_actor_context(request)


async def resolve_mcp_actor(request: Request) -> ActorContext:
    """Resolve a Personal Access Token actor permitted to call plugin APIs."""
    actor_context = await AuthContextService.resolve_actor_context(
        request, required_pat_scope="mcp"
    )
    McpContextService.ensure_mcp_actor(actor_context)
    return actor_context


async def resolve_mcp_repository_context(
    request: Request,
    actor_context: Annotated[ActorContext, Depends(resolve_mcp_actor)],
) -> RepositoryContext | None:
    """Resolve repository headers supplied by an authenticated Claude plugin."""
    repository_context = await RepositoryResolver.resolve_repository_context(
        org_id=actor_context.org_id,
        repository_input=RepositoryRemoteInput(
            explicit_repo_id=AuthContextService.parse_uuid(
                request.headers.get(REPOSITORY_ID_HEADER)
            ),
            origin_url=request.headers.get(REPOSITORY_ORIGIN_URL_HEADER),
            git_root_basename=request.headers.get(REPOSITORY_PATH_HEADER),
            branch=request.headers.get(REPOSITORY_BRANCH_HEADER),
            commit_sha=request.headers.get(REPOSITORY_COMMIT_HEADER),
        ),
    )
    ActorContextService.set_repository_context(repository_context)
    return repository_context


async def resolve_repository_context(
    request: Request,
    actor_context: Annotated[ActorContext, Depends(resolve_actor)],
) -> RepositoryContext | None:
    """Resolve optional repository hints from dashboard/MCP-compatible headers."""
    repository_context = await RepositoryResolver.resolve_repository_context(
        org_id=actor_context.org_id,
        repository_input=RepositoryRemoteInput(
            explicit_repo_id=AuthContextService.parse_uuid(
                request.headers.get(REPOSITORY_ID_HEADER)
            ),
            origin_url=request.headers.get(REPOSITORY_ORIGIN_URL_HEADER),
            git_root_basename=request.headers.get(REPOSITORY_PATH_HEADER),
            branch=request.headers.get(REPOSITORY_BRANCH_HEADER),
            commit_sha=request.headers.get(REPOSITORY_COMMIT_HEADER),
        ),
    )
    ActorContextService.set_repository_context(repository_context)
    return repository_context
