"""Actor and request context schemas used across service boundaries."""

from uuid import UUID

from pydantic import Field

from app.schemas.base import EngramBaseSchema
from app.schemas.enums import AuthClientType, AuthMethod


class ActorContext(EngramBaseSchema):
    actor_user_id: UUID
    email: str
    org_id: UUID
    org_slug: str
    client_name: str | None = None
    request_id: str | None = None
    auth_method: AuthMethod = AuthMethod.PHASE1_HEADER
    session_id: UUID | None = None
    personal_access_token_id: UUID | None = None
    client_type: AuthClientType | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class RequestContext(EngramBaseSchema):
    actor: ActorContext
    repository_id: UUID | None = None
    repository_key: str | None = None
