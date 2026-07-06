"""Repository identity schemas."""

from uuid import UUID

from pydantic import Field

from app.schemas.base import EngramBaseSchema


class RepositoryRemoteInput(EngramBaseSchema):
    origin_url: str | None = None
    git_root_basename: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    explicit_repo_id: UUID | None = None


class RepositoryIdentity(EngramBaseSchema):
    provider: str
    host: str
    workspace: str
    repo_slug: str
    repository_key: str
    canonical_remote_url: str | None = None
    resolver_source: str
    resolver_confidence: float = Field(ge=0.0, le=1.0)


class RepositoryContext(RepositoryIdentity):
    repo_id: UUID | None = None
    org_id: UUID
    branch: str | None = None
    commit_sha: str | None = None
    metadata: dict = Field(default_factory=dict)
