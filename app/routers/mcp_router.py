"""MCP server and tools for agent memory access."""

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated, Any
from uuid import UUID

from fastmcp import FastMCP
from pydantic import ValidationError, WithJsonSchema
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import StreamingResponse
from vortex.exceptions import VortexException

from app.schemas.enums import MemorySource, ProposalStatus, RetrievalMode, ScopeType
from app.schemas.mcp import (
    McpBatchMemoryItemResult,
    McpBatchSaveMemoriesResult,
    McpContextStatusResult,
    McpProposalStatusResult,
    McpProposalToolResult,
    McpRepositoryMetadata,
    McpReviewStatusResult,
    McpSaveMemoryResult,
    McpSearchMemoriesResult,
    McpToolError,
)
from app.schemas.memory import (
    MemoryCreateRequest,
    MemoryDeletionProposalRequest,
    MemoryProposalResponse,
    MemoryScope,
    MemorySearchRequest,
    MemoryUpdateProposalRequest,
)
from app.services.config_service import EngramConfigService
from app.services.dashboard_memory_service import DashboardMemoryService
from app.services.mcp_context_service import McpContextService
from app.services.memory_retrieval_service import MemoryRetrievalService
from app.services.memory_service import MemoryService
from app.services.vortex_http import bad_request

MAX_CONTENT_CHARS = 12_000
MAX_SUMMARY_CHARS = 1_000
MAX_REASON_CHARS = 1_000
MAX_TAGS = 20
MAX_TAG_CHARS = 80
MAX_METADATA_KEYS = 50
MAX_METADATA_VALUE_CHARS = 2_000
MAX_REPOSITORY_METADATA_KEYS = 20
MAX_REPOSITORY_METADATA_VALUE_CHARS = 2_000
MIN_AUTO_REPO_RESOLVER_CONFIDENCE = 0.8
MAX_TOOL_LIMIT = 100
MAX_BATCH_MEMORY_FACTS = 20
DEFAULT_MEMORY_CONTEXT_LIMIT = 8
DEFAULT_REVIEW_STATUS_LIMIT = 20
MAX_REVIEW_STATUS_LIMIT = 50

# Claude Code currently renders nullable/union JSON Schema shapes like
# ``anyOf: [{type: ...}, {type: null}]`` as "unknown" in tool details. These
# aliases preserve nullable runtime validation while emitting simple MCP-facing
# schema types for optional parameters.
McpOptionalTextParam = Annotated[str | None, WithJsonSchema({"type": "string"})]
McpOptionalStringListParam = Annotated[
    list[str] | None,
    WithJsonSchema({"type": "array", "items": {"type": "string"}}),
]
McpOptionalObjectParam = Annotated[
    dict[str, Any] | None,
    WithJsonSchema({"type": "object", "additionalProperties": True}),
]
McpMemoryFactsParam = Annotated[
    list[dict[str, Any]],
    WithJsonSchema(
        {
            "type": "array",
            "items": {"type": "object", "additionalProperties": True},
        }
    ),
]
McpRepositoryParam = Annotated[
    McpRepositoryMetadata | dict[str, Any] | None,
    WithJsonSchema({"type": "object", "additionalProperties": True}),
]

mcp_server = FastMCP(EngramConfigService.engram().mcp_server_name)


def _dump(schema: Any) -> dict[str, Any]:
    """Return JSON-serializable data for MCP clients."""
    if hasattr(schema, "model_dump"):
        return schema.model_dump(mode="json")
    return schema


def _ok(schema: Any) -> dict[str, Any]:
    data = _dump(schema)
    if isinstance(data, dict):
        return {"ok": True, **data}
    return {"ok": True, "data": data}


def _error(code: str, message: str) -> dict[str, Any]:
    return _dump(McpToolError(code=code, message=message))


def _safe_exception_response(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, VortexException):
        return _error(_http_error_code(exc.status_code), _safe_vortex_detail(exc))

    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        detail = getattr(exc, "detail", None)
        return _error(
            _http_error_code(status_code), _safe_exception_detail(status_code, detail)
        )

    if isinstance(exc, ValidationError):
        return _error("invalid_request", _validation_message(exc))
    if isinstance(exc, (TypeError, ValueError)):
        return _error("invalid_request", str(exc) or "Invalid MCP tool input")
    return _error(
        "service_unavailable", "Memory service is unavailable. Try again later."
    )


def _http_error_code(status_code: int) -> str:
    if status_code == 400:
        return "invalid_request"
    if status_code == 401:
        return "unauthorized"
    if status_code == 403:
        return "forbidden"
    if status_code == 404:
        return "not_found"
    if status_code == 409:
        return "conflict"
    if status_code in {500, 503}:
        return "service_unavailable"
    return "request_failed"


def _safe_vortex_detail(exc: VortexException) -> str:
    return _safe_exception_detail(exc.status_code, exc.error)


def _safe_exception_detail(status_code: int, detail: Any) -> str:
    if status_code >= 500:
        return "Memory service is unavailable. Try again later."
    if isinstance(detail, str) and detail.strip():
        return detail
    return "Request could not be completed."


def _validation_message(exc: ValidationError) -> str:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(
        str(part) for part in first_error.get("loc", []) if part != "body"
    )
    message = str(first_error.get("msg") or "Invalid MCP tool input")
    return f"{location}: {message}" if location else message


async def _run_tool(handler: Callable[[], Awaitable[Any]]) -> dict[str, Any]:
    try:
        return _ok(await handler())
    except Exception as exc:  # noqa: BLE001 - MCP tools must return safe agent-readable failures.
        return _safe_exception_response(exc)


def _bounded_text(
    value: str, field_name: str, max_chars: int, required: bool = False
) -> str:
    normalized_value = str(value or "").strip()
    if required and not normalized_value:
        raise bad_request(f"{field_name} is required")
    if len(normalized_value) > max_chars:
        raise bad_request(f"{field_name} exceeds {max_chars} characters")
    return normalized_value


def _bounded_optional_text(
    value: str | None, field_name: str, max_chars: int
) -> str | None:
    if value is None:
        return None
    normalized_value = _bounded_text(value, field_name, max_chars)
    return normalized_value or None


def _bounded_tags(tags: list[str] | None) -> list[str]:
    if tags is None:
        return []
    if not isinstance(tags, list):
        raise bad_request("tags must be a list")

    normalized_tags = []
    seen_tags = set()
    for tag in tags or []:
        normalized_tag = str(tag).strip().lower()
        if not normalized_tag:
            continue
        if len(normalized_tag) > MAX_TAG_CHARS:
            raise bad_request(f"tags cannot exceed {MAX_TAG_CHARS} characters")
        if normalized_tag not in seen_tags:
            seen_tags.add(normalized_tag)
            normalized_tags.append(normalized_tag)
        if len(normalized_tags) > MAX_TAGS:
            raise bad_request(f"At most {MAX_TAGS} tags are allowed")
    return normalized_tags


def _bounded_metadata(
    metadata: dict[str, Any] | None, tool_name: str
) -> dict[str, Any]:
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise bad_request("metadata must be an object")
    if len(metadata) > MAX_METADATA_KEYS:
        raise bad_request(f"metadata cannot exceed {MAX_METADATA_KEYS} keys")

    bounded_metadata: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        if len(str(value)) > MAX_METADATA_VALUE_CHARS:
            raise bad_request(
                f"metadata.{normalized_key} exceeds {MAX_METADATA_VALUE_CHARS} characters"
            )
        bounded_metadata[normalized_key] = value
    bounded_metadata["mcp_tool"] = tool_name
    return bounded_metadata


def _bounded_repository_metadata(
    repository: McpRepositoryMetadata | dict[str, Any] | None,
) -> dict[str, Any] | None:
    if repository is None:
        return None
    if hasattr(repository, "model_dump"):
        repository = repository.model_dump(exclude_none=True)
    if not isinstance(repository, dict):
        raise bad_request("repository must be an object")
    if len(repository) > MAX_REPOSITORY_METADATA_KEYS:
        raise bad_request(
            f"repository cannot exceed {MAX_REPOSITORY_METADATA_KEYS} keys"
        )

    bounded_repository: dict[str, Any] = {}
    for key, value in repository.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        if isinstance(value, dict):
            bounded_repository[normalized_key] = (
                _bounded_repository_metadata(value) or {}
            )
            continue
        if len(str(value)) > MAX_REPOSITORY_METADATA_VALUE_CHARS:
            raise bad_request(
                f"repository.{normalized_key} exceeds {MAX_REPOSITORY_METADATA_VALUE_CHARS} characters"
            )
        bounded_repository[normalized_key] = value
    return bounded_repository


async def _resolve_mcp_context(
    repository: McpRepositoryMetadata | dict[str, Any] | None,
):
    return await McpContextService.resolve_current_context(
        _bounded_repository_metadata(repository)
    )


def _bounded_limit(limit: int | None, max_limit: int = MAX_TOOL_LIMIT) -> int:
    configured_max = EngramConfigService.engram().max_search_results
    effective_max = max(1, min(configured_max, max_limit))
    if limit is None:
        return effective_max
    try:
        normalized_limit = int(limit)
    except (TypeError, ValueError) as exc:
        raise bad_request("limit must be an integer") from exc
    return max(1, min(normalized_limit, effective_max))


def _parse_uuid(value: str | UUID, field_name: str) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise bad_request(f"{field_name} must be a valid UUID") from exc


def _parse_scope(scope: str) -> str:
    normalized_scope = (scope or "auto").strip().lower()
    if normalized_scope not in {"auto", "user", "repo", "org"}:
        raise bad_request("scope must be one of auto, user, repo, or org")
    return normalized_scope


def _memory_scope_for_save(scope: str, context) -> MemoryScope:
    normalized_scope = _parse_scope(scope)
    if normalized_scope == "auto":
        if _has_high_confidence_repo_context(context):
            return MemoryScope(
                scope_type=ScopeType.REPO, scope_id=context.repository.repo_id
            )
        return MemoryScope(
            scope_type=ScopeType.USER, scope_id=context.actor.actor_user_id
        )
    if normalized_scope == "user":
        return MemoryScope(
            scope_type=ScopeType.USER, scope_id=context.actor.actor_user_id
        )
    if normalized_scope == "org":
        return MemoryScope(scope_type=ScopeType.ORG, scope_id=context.actor.org_id)
    return MemoryScope(scope_type=ScopeType.REPO, scope_id=_require_repo_id(context))


def _search_scopes_for_request(scope: str, context) -> list[MemoryScope]:
    normalized_scope = _parse_scope(scope)
    if normalized_scope == "auto":
        return []
    if normalized_scope == "user":
        return [
            MemoryScope(scope_type=ScopeType.USER, scope_id=context.actor.actor_user_id)
        ]
    if normalized_scope == "org":
        return [MemoryScope(scope_type=ScopeType.ORG, scope_id=context.actor.org_id)]
    return [MemoryScope(scope_type=ScopeType.REPO, scope_id=_require_repo_id(context))]


def _require_repo_id(context) -> UUID:
    if context.repository and context.repository.repo_id:
        return context.repository.repo_id
    raise bad_request("Repository context is required for repo scope")


def _has_high_confidence_repo_context(context) -> bool:
    return bool(
        context.repository
        and context.repository.repo_id
        and context.repository.resolver_confidence >= MIN_AUTO_REPO_RESOLVER_CONFIDENCE
    )


def _effective_include_repo(scope: str, include_repo_scope: bool, context) -> bool:
    if _parse_scope(scope) != "auto":
        return False
    return bool(include_repo_scope and _has_high_confidence_repo_context(context))


def _proposal_tool_result(
    proposal: MemoryProposalResponse, message: str
) -> McpProposalToolResult:
    return McpProposalToolResult(
        accepted=True,
        proposal_id=proposal.id,
        memory_id=proposal.fact_id,
        proposal_type=proposal.proposal_type,
        status=proposal.status,
        message=message,
    )


def _proposal_status_result(
    proposal: MemoryProposalResponse,
) -> McpProposalStatusResult:
    return McpProposalStatusResult(
        proposal_id=proposal.id,
        memory_id=proposal.fact_id,
        proposal_type=proposal.proposal_type,
        status=proposal.status,
        scope_type=proposal.scope_type,
        scope_id=proposal.scope_id,
        contains_possible_secret=proposal.contains_possible_secret,
        created_at=proposal.created_at.isoformat(),
        updated_at=proposal.updated_at.isoformat(),
    )


def _bounded_memory_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(facts, list):
        raise bad_request("facts must be a list")
    if not facts:
        raise bad_request("facts must contain at least one memory fact")
    if len(facts) > MAX_BATCH_MEMORY_FACTS:
        raise bad_request(f"At most {MAX_BATCH_MEMORY_FACTS} memory facts are allowed")

    bounded_facts = []
    for index, fact in enumerate(facts, start=1):
        if not isinstance(fact, dict):
            raise bad_request(f"facts[{index}] must be an object")
        bounded_facts.append(fact)
    return bounded_facts


def _memory_create_request_from_fact(
    fact: dict[str, Any],
    default_scope: str,
    context,
    index: int,
) -> MemoryCreateRequest:
    fact_scope = str(fact.get("scope") or default_scope or "user")
    memory_scope = _memory_scope_for_save(fact_scope, context)
    metadata = _bounded_metadata(fact.get("metadata"), "save_memory_facts")
    metadata["batch_index"] = index
    return MemoryCreateRequest(
        scope_type=memory_scope.scope_type,
        scope_id=memory_scope.scope_id,
        content=_bounded_text(
            str(fact.get("content") or ""),
            f"facts[{index}].content",
            MAX_CONTENT_CHARS,
            required=True,
        ),
        summary=_bounded_optional_text(
            fact.get("summary"), f"facts[{index}].summary", MAX_SUMMARY_CHARS
        ),
        tags=_bounded_tags(fact.get("tags")),
        source=MemorySource.MCP,
        metadata=metadata,
        idempotency_key=_bounded_optional_text(
            fact.get("idempotency_key"), f"facts[{index}].idempotency_key", 255
        ),
    )


async def _save_memory_fact_item(
    context,
    fact: dict[str, Any],
    default_scope: str,
    index: int,
) -> McpBatchMemoryItemResult:
    request = _memory_create_request_from_fact(fact, default_scope, context, index)
    result = await MemoryService.create_memory(context.actor, request)
    if isinstance(result, MemoryProposalResponse):
        return McpBatchMemoryItemResult(
            index=index,
            accepted=True,
            status=result.status,
            scope_type=result.scope_type,
            proposal_id=result.id,
            memory_id=result.fact_id,
            message="Memory proposal created and is pending review.",
        )
    return McpBatchMemoryItemResult(
        index=index,
        accepted=True,
        status=result.status,
        scope_type=result.scope_type,
        memory_id=result.id,
        message="Memory saved.",
    )


@mcp_server.tool(
    name="get_current_context",
    description=(
        "Return the authenticated actor, organization, and auto-resolved repository context. "
        "User and org come from the access token; repository is injected by hooks."
    ),
)
async def get_current_context(repository: McpRepositoryParam = None) -> dict[str, Any]:
    async def handler() -> McpContextStatusResult:
        context = await _resolve_mcp_context(repository)
        return McpContextStatusResult(
            actor_user_id=context.actor.actor_user_id,
            email=context.actor.email,
            org_id=context.actor.org_id,
            org_slug=context.actor.org_slug,
            client_name=context.actor.client_name,
            client_type=context.actor.client_type,
            repository=context.repository,
        )

    return await _run_tool(handler)


@mcp_server.tool(
    name="save_memory",
    description=(
        "Add one durable memory fact. Defaults to the current user's own memories. "
        "Use scope='repo' or scope='org' for shared facts; no user_id or org_id input is required."
    ),
)
async def save_memory(
    content: str,
    scope: str = "user",
    summary: McpOptionalTextParam = None,
    tags: McpOptionalStringListParam = None,
    metadata: McpOptionalObjectParam = None,
    idempotency_key: McpOptionalTextParam = None,
    repository: McpRepositoryParam = None,
) -> dict[str, Any]:
    async def handler() -> McpSaveMemoryResult:
        context = await _resolve_mcp_context(repository)
        memory_scope = _memory_scope_for_save(scope, context)
        request = MemoryCreateRequest(
            scope_type=memory_scope.scope_type,
            scope_id=memory_scope.scope_id,
            content=_bounded_text(content, "content", MAX_CONTENT_CHARS, required=True),
            summary=_bounded_optional_text(summary, "summary", MAX_SUMMARY_CHARS),
            tags=_bounded_tags(tags),
            source=MemorySource.MCP,
            metadata=_bounded_metadata(metadata, "save_memory"),
            idempotency_key=_bounded_optional_text(
                idempotency_key, "idempotency_key", 255
            ),
        )
        result = await MemoryService.create_memory(context.actor, request)
        if isinstance(result, MemoryProposalResponse):
            return McpSaveMemoryResult(
                accepted=True,
                status=result.status,
                proposal_id=result.id,
                message="Memory proposal created and is pending review.",
            )
        return McpSaveMemoryResult(
            accepted=True,
            status=result.status,
            memory_id=result.id,
            message="Memory saved.",
        )

    return await _run_tool(handler)


@mcp_server.tool(
    name="save_memory_facts",
    description=(
        "Add up to 20 extracted durable memory facts in one call. "
        "default_scope applies to any fact that omits its own scope field; it defaults to 'user'. "
        "Each fact may override scope with 'user', 'repo', or 'org'. "
        "No user_id or org_id input is required."
    ),
)
async def save_memory_facts(
    facts: McpMemoryFactsParam,
    default_scope: str = "user",
    repository: McpRepositoryParam = None,
) -> dict[str, Any]:
    async def handler() -> McpBatchSaveMemoriesResult:
        context = await _resolve_mcp_context(repository)
        bounded_facts = _bounded_memory_facts(facts)
        results: list[McpBatchMemoryItemResult] = []
        for index, fact in enumerate(bounded_facts, start=1):
            try:
                results.append(
                    await _save_memory_fact_item(context, fact, default_scope, index)
                )
            except Exception as exc:  # noqa: BLE001 - batch calls should report item failures without dropping successes.
                error = _safe_exception_response(exc)
                results.append(
                    McpBatchMemoryItemResult(
                        index=index,
                        accepted=False,
                        message=str(
                            error.get("message") or "Memory fact could not be saved."
                        ),
                        error_code=str(error.get("code") or "request_failed"),
                    )
                )

        saved_count = sum(
            1 for result in results if result.memory_id and not result.proposal_id
        )
        proposal_count = sum(1 for result in results if result.proposal_id)
        error_count = sum(1 for result in results if not result.accepted)
        return McpBatchSaveMemoriesResult(
            accepted=saved_count + proposal_count > 0,
            saved_count=saved_count,
            proposal_count=proposal_count,
            error_count=error_count,
            results=results,
        )

    return await _run_tool(handler)


@mcp_server.tool(
    name="get_memory_context",
    description=(
        "Retrieve compact approved facts relevant to a request across the current user's memories, "
        "current organization, and high-confidence current repository. User/org context comes from auth."
    ),
)
async def get_memory_context(
    query: str,
    limit: int = DEFAULT_MEMORY_CONTEXT_LIMIT,
    repository: McpRepositoryParam = None,
) -> dict[str, Any]:
    async def handler() -> McpSearchMemoriesResult:
        context = await _resolve_mcp_context(repository)
        request = MemorySearchRequest(
            query=_bounded_text(query, "query", 1_000, required=True),
            retrieval_mode=RetrievalMode.LEXICAL,
            scopes=[],
            include_user_scope=True,
            include_repo_scope=_effective_include_repo("auto", True, context),
            include_org_scope=True,
            limit=_bounded_limit(limit),
        )
        return await MemoryRetrievalService.search_memories_for_mcp(
            context.actor, request, context.repository
        )

    return await _run_tool(handler)


@mcp_server.tool(
    name="search_memories",
    description=(
        "Search approved memories. Use scope='user' (default) for personal memories, "
        "scope='repo' for current repository, scope='org' for organization-wide, "
        "or scope='auto' to combine all. No user_id/org_id input is needed."
    ),
)
async def search_memories(
    query: str,
    scope: str = "user",
    limit: int = 20,
    repository: McpRepositoryParam = None,
) -> dict[str, Any]:
    async def handler() -> McpSearchMemoriesResult:
        context = await _resolve_mcp_context(repository)
        normalized_scope = _parse_scope(scope)
        request = MemorySearchRequest(
            query=_bounded_text(query, "query", 1_000, required=True),
            retrieval_mode=RetrievalMode.LEXICAL,
            scopes=_search_scopes_for_request(normalized_scope, context),
            include_user_scope=True if normalized_scope == "auto" else False,
            include_repo_scope=_effective_include_repo(normalized_scope, True, context),
            include_org_scope=True if normalized_scope == "auto" else False,
            limit=_bounded_limit(limit),
        )
        return await MemoryRetrievalService.search_memories_for_mcp(
            context.actor, request, context.repository
        )

    return await _run_tool(handler)


@mcp_server.tool(
    name="list_memories",
    description=(
        "List recent approved memories. Use scope='user' (default) for personal memories, "
        "scope='repo' for current repository, scope='org' for organization-wide, "
        "or scope='auto' to combine all. No user_id/org_id input is needed."
    ),
)
async def list_memories(
    scope: str = "user",
    limit: int = 20,
    repository: McpRepositoryParam = None,
) -> dict[str, Any]:
    async def handler() -> McpSearchMemoriesResult:
        context = await _resolve_mcp_context(repository)
        normalized_scope = _parse_scope(scope)
        request = MemorySearchRequest(
            query=None,
            retrieval_mode=RetrievalMode.ALL_SCOPED,
            scopes=_search_scopes_for_request(normalized_scope, context),
            include_user_scope=True if normalized_scope == "auto" else False,
            include_repo_scope=_effective_include_repo(normalized_scope, True, context),
            include_org_scope=True if normalized_scope == "auto" else False,
            limit=_bounded_limit(limit),
        )
        return await MemoryRetrievalService.search_memories_for_mcp(
            context.actor, request, context.repository
        )

    return await _run_tool(handler)


@mcp_server.tool(
    name="propose_memory_update",
    description=(
        "Create a review proposal to update a visible approved memory by memory_id. "
        "Actor and organization are resolved from auth; repository metadata is optional and usually hook-supplied."
    ),
)
async def propose_memory_update(
    memory_id: str,
    content: str,
    summary: McpOptionalTextParam = None,
    tags: McpOptionalStringListParam = None,
    metadata: McpOptionalObjectParam = None,
    idempotency_key: McpOptionalTextParam = None,
    repository: McpRepositoryParam = None,
) -> dict[str, Any]:
    async def handler() -> McpProposalToolResult:
        context = await _resolve_mcp_context(repository)
        request = MemoryUpdateProposalRequest(
            memory_fact_id=_parse_uuid(memory_id, "memory_id"),
            content=_bounded_text(content, "content", MAX_CONTENT_CHARS, required=True),
            summary=_bounded_optional_text(summary, "summary", MAX_SUMMARY_CHARS),
            tags=_bounded_tags(tags),
            source=MemorySource.MCP,
            metadata=_bounded_metadata(metadata, "propose_memory_update"),
            idempotency_key=_bounded_optional_text(
                idempotency_key, "idempotency_key", 255
            ),
        )
        proposal = await MemoryService.create_update_proposal(context.actor, request)
        return _proposal_tool_result(
            proposal, "Memory update proposal created and is pending review."
        )

    return await _run_tool(handler)


@mcp_server.tool(
    name="propose_memory_deletion",
    description=(
        "Create a review proposal to delete a visible approved memory by memory_id. "
        "Actor and organization are resolved from auth; repository metadata is optional and usually hook-supplied."
    ),
)
async def propose_memory_deletion(
    memory_id: str,
    reason: McpOptionalTextParam = None,
    metadata: McpOptionalObjectParam = None,
    idempotency_key: McpOptionalTextParam = None,
    repository: McpRepositoryParam = None,
) -> dict[str, Any]:
    async def handler() -> McpProposalToolResult:
        context = await _resolve_mcp_context(repository)
        request = MemoryDeletionProposalRequest(
            memory_fact_id=_parse_uuid(memory_id, "memory_id"),
            reason=_bounded_optional_text(reason, "reason", MAX_REASON_CHARS),
            source=MemorySource.MCP,
            metadata=_bounded_metadata(metadata, "propose_memory_deletion"),
            idempotency_key=_bounded_optional_text(
                idempotency_key, "idempotency_key", 255
            ),
        )
        proposal = await MemoryService.create_deletion_proposal(context.actor, request)
        return _proposal_tool_result(
            proposal, "Memory deletion proposal created and is pending review."
        )

    return await _run_tool(handler)


@mcp_server.tool(
    name="get_memory_review_status",
    description=(
        "Get compact review status for proposals created by the current actor. "
        "No user_id or org_id input is required; status can be filtered by proposal_id, memory_id, or status."
    ),
)
async def get_memory_review_status(
    proposal_id: McpOptionalTextParam = None,
    memory_id: McpOptionalTextParam = None,
    status: McpOptionalTextParam = None,
    limit: int = DEFAULT_REVIEW_STATUS_LIMIT,
    repository: McpRepositoryParam = None,
) -> dict[str, Any]:
    async def handler() -> McpReviewStatusResult:
        context = await _resolve_mcp_context(repository)
        effective_limit = _bounded_limit(limit, MAX_REVIEW_STATUS_LIMIT)
        proposal_status = _parse_proposal_status(status)

        if proposal_id:
            proposal = await DashboardMemoryService.get_proposal(
                context.actor, _parse_uuid(proposal_id, "proposal_id")
            )
            return McpReviewStatusResult(
                results=[_proposal_status_result(proposal)], limit=1
            )

        proposals = await DashboardMemoryService.list_proposals(
            actor=context.actor,
            proposal_status=proposal_status,
            fact_id=_parse_uuid(memory_id, "memory_id") if memory_id else None,
            limit=effective_limit,
            offset=0,
        )
        return McpReviewStatusResult(
            results=[
                _proposal_status_result(proposal)
                for proposal in proposals[:effective_limit]
            ],
            limit=effective_limit,
        )

    return await _run_tool(handler)


def _parse_proposal_status(value: str | None) -> ProposalStatus | None:
    normalized_value = (value or "").strip().lower()
    if not normalized_value:
        return None
    try:
        return ProposalStatus(normalized_value)
    except ValueError as exc:
        allowed_statuses = ", ".join(status.value for status in ProposalStatus)
        raise bad_request(f"status must be one of {allowed_statuses}") from exc


_mcp_session_ids_by_client: dict[str, str] = {}


def _mcp_client_key(request: Request) -> str | None:
    authorization_header = (request.headers.get("authorization") or "").strip()
    client_name = (request.headers.get("x-engram-client") or "").strip().lower()
    if not authorization_header:
        return None
    return f"{client_name}:{authorization_header}" if client_name else authorization_header


def _inject_request_header(request: Request, header_name: str, header_value: str) -> None:
    encoded_name = header_name.lower().encode()
    encoded_value = header_value.encode()
    filtered_headers = [
        (name, value)
        for name, value in request.scope.get("headers", [])
        if name.lower() != encoded_name
    ]
    filtered_headers.append((encoded_name, encoded_value))
    request.scope["headers"] = filtered_headers


def _jsonrpc_method_from_body(body: bytes) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        method = payload.get("method")
        return str(method) if method else None
    return None


async def _empty_sse_probe() -> AsyncIterator[str]:
    yield ": engram-mcp-get-probe\n\n"


async def _mcp_http_compatibility_middleware(request: Request, call_next):
    client_key = _mcp_client_key(request)
    remembered_session_id = (
        _mcp_session_ids_by_client.get(client_key) if client_key else None
    )
    request_session_id = request.headers.get("mcp-session-id")

    if not request_session_id and remembered_session_id:
        _inject_request_header(request, "mcp-session-id", remembered_session_id)
        request_session_id = remembered_session_id

    if request.method == "GET" and not request_session_id:
        return StreamingResponse(
            _empty_sse_probe(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
            },
        )

    if request.method == "POST" and not request_session_id:
        request_body = await request.body()
        if _jsonrpc_method_from_body(request_body) != "initialize" and client_key:
            stale_session_id = _mcp_session_ids_by_client.pop(client_key, None)
            if stale_session_id:
                _inject_request_header(request, "mcp-session-id", stale_session_id)

    response = await call_next(request)

    response_session_id = response.headers.get("mcp-session-id")
    if client_key and response_session_id:
        _mcp_session_ids_by_client[client_key] = response_session_id
    elif client_key and response.status_code == 404:
        _mcp_session_ids_by_client.pop(client_key, None)

    return response


mcp_http_app = mcp_server.http_app(path="/http", transport="http")
mcp_http_app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=_mcp_http_compatibility_middleware,
)


def lifespan():
    """Expose the FastMCP HTTP lifespan so the parent app initializes streamable HTTP state."""
    return mcp_http_app.lifespan


def mount_mcp_http_app(app) -> None:
    """Mount the generic streamable HTTP MCP endpoint on the parent FastAPI app."""
    app.mount("/mcp", mcp_http_app, name="engram-mcp")
