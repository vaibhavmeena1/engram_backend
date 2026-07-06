"""Admin dashboard schemas for identity and role inspection."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import EngramBaseSchema


class UserResponse(EngramBaseSchema):
    id: UUID
    email: str
    display_name: str | None = None
    is_active: bool
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class RoleResponse(EngramBaseSchema):
    id: UUID
    org_id: UUID
    slug: str
    name: str
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)
    is_system: bool
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class RoleAssignmentCreateRequest(EngramBaseSchema):
    user_id: UUID
    role_id: UUID
    scope_type: str | None = Field(default=None, max_length=32)
    scope_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)


class RoleAssignmentResponse(EngramBaseSchema):
    id: UUID
    org_id: UUID
    user_id: UUID
    role_id: UUID
    assigned_by_id: UUID | None = None
    scope_type: str | None = None
    scope_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    user_email: str | None = None
    role_slug: str | None = None
    role_name: str | None = None
