"""MCP request context resolution helpers."""

import json
from typing import Any
from uuid import UUID

from fastapi import Request
from fastmcp.server.dependencies import get_http_request

from app.schemas.context import ActorContext
from app.schemas.enums import AuthClientType, AuthMethod
from app.schemas.mcp import McpResolvedContext
from app.schemas.repository import RepositoryContext, RepositoryRemoteInput
from app.services.actor_context import ActorContextService
from app.services.auth_context_service import AuthContextService
from app.services.repository_resolver import RepositoryResolver
from app.services.vortex_http import forbidden, service_unavailable

REPOSITORY_METADATA_HEADER = "x-engram-repository"
REPOSITORY_ID_HEADER = "x-engram-repository-id"
REPOSITORY_ORIGIN_URL_HEADER = "x-engram-repository-origin-url"
REPOSITORY_PATH_HEADER = "x-engram-repository-path"
REPOSITORY_BRANCH_HEADER = "x-engram-repository-branch"
REPOSITORY_COMMIT_HEADER = "x-engram-repository-commit"

# Local/client fallback only. This is intentionally not a durable identity by itself.
REPOSITORY_FALLBACK_HEADER = "x-engram-repo"


class McpContextService:
    """Builds trusted actor and repository context for MCP tool execution."""

    @classmethod
    async def resolve_current_context(
        cls, repository_metadata: dict[str, Any] | None = None
    ) -> McpResolvedContext:
        request = cls.current_http_request()
        actor = await AuthContextService.resolve_actor_context(
            request, required_pat_scope="mcp"
        )
        cls.ensure_mcp_actor(actor)
        repository_context = await cls.resolve_repository_context(
            request, actor.org_id, repository_metadata
        )
        ActorContextService.set_repository_context(repository_context)
        return McpResolvedContext(actor=actor, repository=repository_context)

    @classmethod
    def current_http_request(cls) -> Request:
        try:
            return get_http_request()
        except RuntimeError as exc:
            raise service_unavailable(
                "MCP HTTP request context is unavailable"
            ) from exc

    @classmethod
    def ensure_mcp_actor(cls, actor: ActorContext) -> None:
        if actor.auth_method != AuthMethod.PERSONAL_ACCESS_TOKEN:
            raise forbidden("MCP requests require Personal Access Token authentication")
        if actor.client_type and actor.client_type not in {
            AuthClientType.MCP,
            AuthClientType.CLI,
            AuthClientType.AUTOMATION,
        }:
            raise forbidden("Personal Access Token client type is not allowed for MCP")

    @classmethod
    async def resolve_repository_context(
        cls,
        request: Request,
        org_id: UUID,
        repository_metadata: dict[str, Any] | None = None,
    ) -> RepositoryContext | None:
        request_metadata = cls._repository_metadata_from_request(request)
        # HTTP headers are client/hook-owned transport context. A tool argument is
        # only a fallback for runtimes without hooks and must not override it.
        merged_metadata = cls._normalize_metadata(repository_metadata)
        merged_metadata.update(request_metadata)

        repository_input = RepositoryRemoteInput(
            explicit_repo_id=cls._metadata_uuid(
                merged_metadata, "repo_id", "repository_id", "id"
            ),
            origin_url=cls._metadata_str(
                merged_metadata, "origin_url", "remote_origin_url", "remote_url"
            ),
            git_root_basename=cls._repository_basename_hint(merged_metadata),
            branch=cls._metadata_str(merged_metadata, "branch", "current_branch"),
            commit_sha=cls._metadata_str(
                merged_metadata, "commit_sha", "commit", "sha"
            ),
        )
        return await RepositoryResolver.resolve_repository_context(
            org_id=org_id, repository_input=repository_input
        )

    @classmethod
    def _repository_metadata_from_request(cls, request: Request) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        metadata.update(
            cls._json_header(request.headers.get(REPOSITORY_METADATA_HEADER))
        )
        metadata.update(
            cls._without_empty_values(
                {
                    "repo_id": request.headers.get(REPOSITORY_ID_HEADER),
                    "origin_url": request.headers.get(REPOSITORY_ORIGIN_URL_HEADER),
                    "git_root": request.headers.get(REPOSITORY_PATH_HEADER),
                    "branch": request.headers.get(REPOSITORY_BRANCH_HEADER),
                    "commit_sha": request.headers.get(REPOSITORY_COMMIT_HEADER),
                    "repo_hint": request.headers.get(REPOSITORY_FALLBACK_HEADER),
                }
            )
        )
        return metadata

    @classmethod
    def _json_header(cls, value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed_value, dict):
            return {}
        repository_metadata = parsed_value.get("repository", parsed_value)
        return cls._normalize_metadata(repository_metadata)

    @classmethod
    def _normalize_metadata(cls, metadata: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(metadata, dict):
            return {}
        repository_metadata = metadata.get("repository", metadata)
        if not isinstance(repository_metadata, dict):
            return {}
        return cls._without_empty_values(dict(repository_metadata))

    @classmethod
    def _without_empty_values(cls, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in metadata.items()
            if value is not None and str(value).strip()
        }

    @classmethod
    def _metadata_str(cls, metadata: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = metadata.get(key)
            if value is None:
                continue
            normalized_value = str(value).strip()
            if normalized_value:
                return normalized_value
        return None

    @classmethod
    def _metadata_uuid(cls, metadata: dict[str, Any], *keys: str) -> UUID | None:
        for key in keys:
            parsed_uuid = AuthContextService.parse_uuid(
                cls._metadata_str(metadata, key)
            )
            if parsed_uuid:
                return parsed_uuid
        return None

    @classmethod
    def _repository_basename_hint(cls, metadata: dict[str, Any]) -> str | None:
        explicit_basename = cls._metadata_str(
            metadata, "repo_dir_name", "git_root_basename", "repo_slug"
        )
        if explicit_basename:
            return cls._basename(explicit_basename)

        path_hint = cls._metadata_str(
            metadata, "git_root", "repository_path", "path", "repo_hint"
        )
        if path_hint:
            return cls._basename(path_hint)
        return None

    @classmethod
    def _basename(cls, value: str) -> str:
        normalized_value = str(value).strip().rstrip("/\\")
        if not normalized_value:
            return ""
        return normalized_value.replace("\\", "/").rsplit("/", 1)[-1]
