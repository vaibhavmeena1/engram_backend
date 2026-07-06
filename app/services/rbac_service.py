"""Centralized phase-1 permission checks for memory operations."""

from uuid import UUID

from app.models.memory import MemoryFact
from app.models.review import MemoryProposal
from app.schemas.context import ActorContext
from app.schemas.enums import MemoryStatus, ScopeType


class RbacService:
    """Keeps permission logic out of routers, MCP tools, and memory services."""

    ADMIN_ROLE = "admin"

    @classmethod
    def is_admin(cls, actor: ActorContext) -> bool:
        return cls.ADMIN_ROLE in set(actor.roles)

    @classmethod
    def can_read_memory(cls, actor: ActorContext, memory: MemoryFact) -> bool:
        if memory.org_id != actor.org_id:
            return False
        if memory.status != MemoryStatus.APPROVED:
            return cls.is_admin(actor)
        if memory.scope_type == ScopeType.USER:
            return memory.scope_id == actor.actor_user_id or cls.is_admin(actor)
        if memory.scope_type in {ScopeType.REPO, ScopeType.ORG}:
            return True
        return False

    @classmethod
    def can_create_memory(
        cls, actor: ActorContext, scope_type: ScopeType, scope_id: UUID
    ) -> bool:
        if scope_type == ScopeType.USER:
            return scope_id == actor.actor_user_id or cls.is_admin(actor)
        return cls.is_admin(actor)

    @classmethod
    def can_propose_memory(
        cls, actor: ActorContext, scope_type: ScopeType, scope_id: UUID
    ) -> bool:  # noqa: ARG003
        if scope_type == ScopeType.USER:
            return scope_id == actor.actor_user_id or cls.is_admin(actor)
        if scope_type in {ScopeType.REPO, ScopeType.ORG}:
            return True
        return False

    @classmethod
    def can_approve_memory(
        cls, actor: ActorContext, proposal_or_memory: MemoryProposal | MemoryFact
    ) -> bool:
        return proposal_or_memory.org_id == actor.org_id and cls.is_admin(actor)

    @classmethod
    def can_edit_memory(cls, actor: ActorContext, memory: MemoryFact) -> bool:
        if memory.org_id != actor.org_id:
            return False
        if cls.is_admin(actor):
            return True
        return (
            memory.scope_type == ScopeType.USER
            and memory.scope_id == actor.actor_user_id
        )

    @classmethod
    def can_delete_memory(cls, actor: ActorContext, memory: MemoryFact) -> bool:
        if memory.org_id != actor.org_id:
            return False
        if cls.is_admin(actor):
            return True
        return (
            memory.scope_type == ScopeType.USER
            and memory.scope_id == actor.actor_user_id
        )

    @classmethod
    def can_manage_tags(cls, actor: ActorContext, org_id: UUID) -> bool:
        return actor.org_id == org_id and cls.is_admin(actor)
