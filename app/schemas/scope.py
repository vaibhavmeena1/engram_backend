"""Scope discovery schemas for dashboard memory creation."""

from uuid import UUID

from pydantic import Field

from app.schemas.base import EngramBaseSchema
from app.schemas.enums import ScopeType


class ScopeOptionResponse(EngramBaseSchema):
    scope_type: ScopeType
    scope_id: UUID
    label: str
    detail: str | None = None
    metadata: dict = Field(default_factory=dict)


class ScopeOptionsResponse(EngramBaseSchema):
    current_user: ScopeOptionResponse
    organizations: list[ScopeOptionResponse] = Field(default_factory=list)
    repositories: list[ScopeOptionResponse] = Field(default_factory=list)
