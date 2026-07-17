"""Contracts used by agent plugin lifecycle integrations."""

from app.schemas.base import EngramBaseSchema
from app.schemas.repository import RepositoryContext


class PluginSessionStatusResponse(EngramBaseSchema):
    repository_resolved: bool
    user_memory_count: int | None = None
    repository_memory_count: int | None = None
    organization_memory_count: int | None = None
    repository: RepositoryContext | None = None