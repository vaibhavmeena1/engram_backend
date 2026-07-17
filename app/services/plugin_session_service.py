"""Repository-aware status data for agent plugin session startup."""

from app.models.memory import MemoryFact
from app.schemas.context import ActorContext
from app.schemas.enums import MemoryStatus, ScopeType
from app.schemas.plugin import PluginSessionStatusResponse
from app.schemas.repository import RepositoryContext


class PluginSessionService:
    """Build compact startup status without exposing memory contents."""

    MIN_REPOSITORY_CONFIDENCE = 0.8

    @classmethod
    async def get_session_status(
        cls,
        actor: ActorContext,
        repository_context: RepositoryContext | None,
    ) -> PluginSessionStatusResponse:
        repository_resolved = bool(
            repository_context
            and repository_context.repo_id
            and repository_context.resolver_confidence
            >= cls.MIN_REPOSITORY_CONFIDENCE
        )
        if not repository_resolved or not repository_context:
            return PluginSessionStatusResponse(
                repository_resolved=False,
                repository=repository_context,
            )

        user_memory_count = await MemoryFact.filter(
            org_id=actor.org_id,
            scope_type=ScopeType.USER,
            scope_id=actor.actor_user_id,
            status=MemoryStatus.APPROVED,
        ).count()
        repository_memory_count = await MemoryFact.filter(
            org_id=actor.org_id,
            scope_type=ScopeType.REPO,
            scope_id=repository_context.repo_id,
            status=MemoryStatus.APPROVED,
        ).count()
        organization_memory_count = await MemoryFact.filter(
            org_id=actor.org_id,
            scope_type=ScopeType.ORG,
            scope_id=actor.org_id,
            status=MemoryStatus.APPROVED,
        ).count()
        return PluginSessionStatusResponse(
            repository_resolved=True,
            user_memory_count=user_memory_count,
            repository_memory_count=repository_memory_count,
            organization_memory_count=organization_memory_count,
            repository=repository_context,
        )