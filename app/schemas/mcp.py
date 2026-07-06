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


class McpRepositoryMetadata(EngramBaseSchema):
    """Repository hints supplied by local MCP clients/plugins.

    Extra keys are accepted so newer plugins can send additional Git facts without
    breaking older backend deployments. The backend still bounds and normalizes
    this metadata before resolving repository scope.
    """

    model_config = ConfigDict(
        extra="allow",
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    repo_id: UUID | None = None
    repository_id: UUID | None = None
    id: UUID | None = None
    origin_url: str | None = None
    remote_origin_url: str | None = None
    remote_url: str | None = None
    git_root: str | None = None
    repository_path: str | None = None
    path: str | None = None
    repo_hint: str | None = None
    repo_dir_name: str | None = None
    git_root_basename: str | None = None
    repo_slug: str | None = None
    branch: str | None = None
    current_branch: str | None = None
    commit_sha: str | None = None
    commit: str | None = None
    sha: str | None = None


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


class McpSaveMemoryResult(EngramBaseSchema):
    accepted: bool
    status: MemoryStatus | ProposalStatus
    memory_id: UUID | None = None
    proposal_id: UUID | None = None
    message: str


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
