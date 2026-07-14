"""Authentication and Personal Access Token API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

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


class OAuthProtectedResourceMetadataResponse(EngramBaseSchema):
    resource: str
    authorization_servers: list[str]
    scopes_supported: list[str] = Field(default_factory=lambda: ["mcp"])
    bearer_methods_supported: list[str] = Field(default_factory=lambda: ["header"])


class OAuthAuthorizationServerMetadataResponse(EngramBaseSchema):
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str
    response_types_supported: list[str] = Field(default_factory=lambda: ["code"])
    grant_types_supported: list[str] = Field(
        default_factory=lambda: ["authorization_code"]
    )
    code_challenge_methods_supported: list[str] = Field(
        default_factory=lambda: ["S256"]
    )
    token_endpoint_auth_methods_supported: list[str] = Field(
        default_factory=lambda: ["none"]
    )
    scopes_supported: list[str] = Field(default_factory=lambda: ["mcp"])


class OAuthClientRegistrationRequest(EngramBaseSchema):
    model_config = ConfigDict(
        extra="allow",
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    client_name: str | None = Field(default=None, max_length=255)
    redirect_uris: list[str] = Field(min_length=1)
    grant_types: list[str] = Field(default_factory=lambda: ["authorization_code"])
    response_types: list[str] = Field(default_factory=lambda: ["code"])
    token_endpoint_auth_method: str = "none"
    scope: str | None = None
    metadata: dict = Field(default_factory=dict)

    @field_validator("redirect_uris")
    @classmethod
    def validate_redirect_uris(cls, redirect_uris: list[str]) -> list[str]:
        normalized_redirect_uris = []
        for redirect_uri in redirect_uris:
            normalized_redirect_uri = str(redirect_uri or "").strip()
            if (
                normalized_redirect_uri
                and normalized_redirect_uri not in normalized_redirect_uris
            ):
                normalized_redirect_uris.append(normalized_redirect_uri)
        if not normalized_redirect_uris:
            raise ValueError("At least one redirect URI is required")
        return normalized_redirect_uris


class OAuthClientRegistrationResponse(EngramBaseSchema):
    client_id: str
    client_name: str | None = None
    redirect_uris: list[str]
    grant_types: list[str] = Field(default_factory=lambda: ["authorization_code"])
    response_types: list[str] = Field(default_factory=lambda: ["code"])
    token_endpoint_auth_method: str = "none"


class OAuthTokenResponse(EngramBaseSchema):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str = "mcp"
