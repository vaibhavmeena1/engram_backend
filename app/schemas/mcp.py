"""Compact MCP-facing schemas for agent tool responses."""

from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.base import EngramBaseSchema
from app.schemas.context import ActorContext
from app.schemas.enums import (
    AuthClientType,
    MemoryStatus,
    ProposalStatus,
    ProposalType,
    ScopeType,
)
from app.schemas.repository import RepositoryContext


class McpMemoryFactInput(EngramBaseSchema):
    """Typed input for one durable fact saved through the MCP batch tool."""

    content: str = Field(
        description="One concise, standalone durable fact to remember."
    )
    rationale: str = Field(
        description="Why this fact is durable, well-supported, and useful in future work."
    )
    scope: str | None = Field(
        default=None,
        description="Optional override: user, repo, org, or auto. Uses default_scope when omitted.",
    )
    summary: str | None = Field(
        default=None,
        description="Optional short searchable label for the fact.",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Optional lowercase classification tags; up to 20.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional non-sensitive supporting metadata. Do not include extraction_reason.",
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Optional stable retry key for proposal creation.",
    )


class McpRepositoryMetadata(EngramBaseSchema):
    """Manual repository fallback; hooks can inject richer local Git metadata."""

    model_config = ConfigDict(
        extra="allow",
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    origin_url: str | None = Field(
        default=None,
        description="Current Git remote URL. Use only when session context says repository resolution is unavailable.",
    )


class McpResolvedContext(EngramBaseSchema):
    actor: ActorContext
    repository: RepositoryContext | None = None


class McpContextStatusResult(EngramBaseSchema):
    actor_user_id: UUID
    email: str
    org_id: UUID
    org_slug: str
    client_name: str | None = None
    client_type: AuthClientType | None = None
    repository: RepositoryContext | None = None


class McpToolError(EngramBaseSchema):
    ok: bool = False
    code: str
    message: str


class McpMemoryResult(EngramBaseSchema):
    id: UUID
    scope_type: ScopeType
    content: str
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    score: float = 1.0
    match_reason: str | None = None
    updated_at: str | None = None


class McpProposalToolResult(EngramBaseSchema):
    accepted: bool
    proposal_id: UUID
    memory_id: UUID | None = None
    proposal_type: ProposalType
    status: ProposalStatus
    message: str


class McpProposalStatusResult(EngramBaseSchema):
    proposal_id: UUID
    memory_id: UUID | None = None
    proposal_type: ProposalType
    status: ProposalStatus
    scope_type: ScopeType
    scope_id: UUID
    contains_possible_secret: bool = False
    created_at: str
    updated_at: str


class McpBatchMemoryItemResult(EngramBaseSchema):
    index: int
    accepted: bool = False
    status: MemoryStatus | ProposalStatus | None = None
    scope_type: ScopeType | None = None
    memory_id: UUID | None = None
    proposal_id: UUID | None = None
    message: str
    error_code: str | None = None


class McpBatchSaveMemoriesResult(EngramBaseSchema):
    accepted: bool
    saved_count: int = 0
    proposal_count: int = 0
    error_count: int = 0
    results: list[McpBatchMemoryItemResult] = Field(default_factory=list)


class McpReviewStatusResult(EngramBaseSchema):
    ok: bool = True
    results: list[McpProposalStatusResult] = Field(default_factory=list)
    limit: int


class McpSearchMemoriesResult(EngramBaseSchema):
    results: list[McpMemoryResult] = Field(default_factory=list)
    limit: int


class McpToolSuccess(EngramBaseSchema):
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
