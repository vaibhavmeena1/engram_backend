"""Authentication and Personal Access Token API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import EngramBaseSchema
from app.schemas.enums import AuthClientType, AuthMethod


class AuthProfileResponse(EngramBaseSchema):
    id: UUID
    email: str
    display_name: str | None = None
    org_id: UUID
    org_slug: str
    client_type: AuthClientType | None = None
    auth_method: AuthMethod
    roles: list[str] = Field(default_factory=list)


class PersonalAccessTokenCreateRequest(EngramBaseSchema):
    name: str = Field(min_length=1, max_length=255)
    client_type: AuthClientType = AuthClientType.MCP
    expires_in_seconds: int | None = Field(default=None, ge=1)
    scopes: list[str] = Field(default_factory=lambda: ["mcp"])
    metadata: dict = Field(default_factory=dict)


class PersonalAccessTokenCreateResponse(EngramBaseSchema):
    id: UUID
    name: str
    client_type: AuthClientType
    key_prefix: str
    token: str
    expires_at: datetime | None = None
    scopes: list[str] = Field(default_factory=list)


class PersonalAccessTokenResponse(EngramBaseSchema):
    id: UUID
    name: str
    client_type: AuthClientType
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    scopes: list[str] = Field(default_factory=list)
