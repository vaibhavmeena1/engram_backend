"""Tag management schemas for dashboard APIs."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import EngramBaseSchema


class TagCreateRequest(EngramBaseSchema):
    label: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    color: str | None = Field(default=None, max_length=32)
    metadata: dict = Field(default_factory=dict)


class TagUpdateRequest(EngramBaseSchema):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    color: str | None = Field(default=None, max_length=32)
    metadata: dict | None = None


class TagResponse(EngramBaseSchema):
    id: UUID
    org_id: UUID
    slug: str
    label: str
    description: str | None = None
    color: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
