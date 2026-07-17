"""Audit dashboard response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import EngramBaseSchema
from app.schemas.enums import AuthClientType, AuthMethod, MemoryStatus


class MemoryAccessLogResponse(EngramBaseSchema):
    id: UUID
    org_id: UUID | None = None
    actor_user_id: UUID | None = None
    repository_id: UUID | None = None
    memory_fact_id: UUID | None = None
    proposal_id: UUID | None = None
    action: str
    auth_method: AuthMethod | None = None
    client_type: AuthClientType | None = None
    session_id: UUID | None = None
    personal_access_token_id: UUID | None = None
    client_name: str | None = None
    request_id: str | None = None
    query_hash: str | None = None
    returned_memory_ids: list = Field(default_factory=list)
    scope_filters: dict = Field(default_factory=dict)
    scores: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MemoryFactVersionResponse(EngramBaseSchema):
    id: UUID
    fact_id: UUID
    proposal_id: UUID | None = None
    version_number: int
    status: MemoryStatus
    content: str
    rationale: str | None = None
    summary: str | None = None
    content_hash: str
    change_reason: str | None = None
    changed_by_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
