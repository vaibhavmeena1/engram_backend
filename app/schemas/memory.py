"""Memory request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import EngramBaseSchema
from app.schemas.enums import (
    MemoryListSection,
    MemorySource,
    MemoryStatus,
    ProposalStatus,
    ProposalType,
    RetrievalMode,
    ScopeType,
)


class MemoryScope(EngramBaseSchema):
    scope_type: ScopeType
    scope_id: UUID


class MemoryCreateRequest(MemoryScope):
    content: str = Field(min_length=1)
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: MemorySource = MemorySource.DASHBOARD
    metadata: dict = Field(default_factory=dict)
    idempotency_key: str | None = None


class MemoryProposalCreateRequest(MemoryCreateRequest):
    proposal_type: ProposalType = ProposalType.CREATE
    observation_id: UUID | None = None


class MemoryUpdateProposalRequest(EngramBaseSchema):
    memory_fact_id: UUID
    content: str = Field(min_length=1)
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: MemorySource = MemorySource.DASHBOARD
    metadata: dict = Field(default_factory=dict)
    observation_id: UUID | None = None
    idempotency_key: str | None = None


class MemoryDeletionProposalRequest(EngramBaseSchema):
    memory_fact_id: UUID
    reason: str | None = None
    source: MemorySource = MemorySource.DASHBOARD
    metadata: dict = Field(default_factory=dict)
    observation_id: UUID | None = None
    idempotency_key: str | None = None


class MemoryStatusChangeRequest(EngramBaseSchema):
    reason: str | None = None
    metadata: dict = Field(default_factory=dict)


class MemorySearchRequest(EngramBaseSchema):
    query: str | None = None
    retrieval_mode: RetrievalMode = RetrievalMode.LEXICAL
    scopes: list[MemoryScope] = Field(default_factory=list)
    include_user_scope: bool = True
    include_repo_scope: bool = True
    include_org_scope: bool = True
    limit: int = Field(default=20, ge=1, le=100)


class MemoryListRequest(EngramBaseSchema):
    section: MemoryListSection | None = None
    scope_type: ScopeType | None = None
    scope_id: UUID | None = None
    org_id: UUID | None = None
    repo_id: UUID | None = None
    owner_user_id: UUID | None = None
    status: MemoryStatus | None = None
    tag: str | None = None
    created_by: UUID | None = None
    approved_by: UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    updated_from: datetime | None = None
    updated_to: datetime | None = None
    query: str | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class MemoryDisplayEntityResponse(EngramBaseSchema):
    id: UUID
    label: str
    detail: str | None = None
    metadata: dict = Field(default_factory=dict)


class MemoryDisplayContextResponse(EngramBaseSchema):
    organization: MemoryDisplayEntityResponse | None = None
    repository: MemoryDisplayEntityResponse | None = None
    owner_user: MemoryDisplayEntityResponse | None = None
    scope: MemoryDisplayEntityResponse | None = None


class MemoryFactResponse(MemoryScope):
    id: UUID
    org_id: UUID
    repository_id: UUID | None = None
    owner_user_id: UUID | None = None
    status: MemoryStatus
    content: str
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: MemorySource
    metadata: dict = Field(default_factory=dict)
    display_context: MemoryDisplayContextResponse | None = None
    created_at: datetime
    updated_at: datetime


class MemorySearchResult(MemoryFactResponse):
    score: float = 1.0
    match_reason: str | None = None


class MemoryProposalResponse(MemoryScope):
    id: UUID
    org_id: UUID
    fact_id: UUID | None = None
    observation_id: UUID | None = None
    repository_id: UUID | None = None
    proposal_type: ProposalType
    status: ProposalStatus
    proposed_content: str | None = None
    proposed_summary: str | None = None
    contains_possible_secret: bool = False
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
