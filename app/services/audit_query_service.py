"""Read-only dashboard queries for audit data."""

from uuid import UUID

from app.models.audit import MemoryAccessLog
from app.models.memory import MemoryFactVersion
from app.schemas.audit import MemoryAccessLogResponse, MemoryFactVersionResponse
from app.schemas.context import ActorContext
from app.services.rbac_service import RbacService
from app.services.vortex_http import forbidden


class AuditQueryService:
    """Exposes audit rows to dashboard admins without coupling routers to ORM models."""

    @classmethod
    async def list_memory_access_logs(
        cls,
        actor: ActorContext,
        action: str | None = None,
        memory_fact_id: UUID | None = None,
        proposal_id: UUID | None = None,
        request_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MemoryAccessLogResponse]:
        cls._ensure_admin(actor)
        query = MemoryAccessLog.filter(org_id=actor.org_id)
        if action:
            query = query.filter(action=action)
        if memory_fact_id:
            query = query.filter(memory_fact_id=memory_fact_id)
        if proposal_id:
            query = query.filter(proposal_id=proposal_id)
        if request_id:
            query = query.filter(request_id=request_id)

        logs = await query.order_by("-created_at").offset(offset).limit(limit)
        return [cls._access_log_response(log) for log in logs]

    @classmethod
    async def list_memory_fact_versions(
        cls,
        actor: ActorContext,
        fact_id: UUID | None = None,
        proposal_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MemoryFactVersionResponse]:
        cls._ensure_admin(actor)
        query = MemoryFactVersion.filter(fact__org_id=actor.org_id)
        if fact_id:
            query = query.filter(fact_id=fact_id)
        if proposal_id:
            query = query.filter(proposal_id=proposal_id)

        versions = (
            await query.order_by("-created_at", "-version_number")
            .offset(offset)
            .limit(limit)
        )
        return [cls._fact_version_response(version) for version in versions]

    @classmethod
    def _ensure_admin(cls, actor: ActorContext) -> None:
        if not RbacService.is_admin(actor):
            raise forbidden("Admin access is required")

    @classmethod
    def _access_log_response(cls, log: MemoryAccessLog) -> MemoryAccessLogResponse:
        return MemoryAccessLogResponse(
            id=log.id,
            org_id=log.org_id,
            actor_user_id=log.actor_user_id,
            repository_id=log.repository_id,
            memory_fact_id=log.memory_fact_id,
            proposal_id=log.proposal_id,
            action=log.action,
            auth_method=log.auth_method,
            client_type=log.client_type,
            session_id=log.session_id,
            personal_access_token_id=log.personal_access_token_id,
            client_name=log.client_name,
            request_id=log.request_id,
            query_hash=log.query_hash,
            returned_memory_ids=log.returned_memory_ids or [],
            scope_filters=log.scope_filters or {},
            scores=log.scores or {},
            metadata=log.metadata or {},
            created_at=log.created_at,
            updated_at=log.updated_at,
        )

    @classmethod
    def _fact_version_response(
        cls, version: MemoryFactVersion
    ) -> MemoryFactVersionResponse:
        return MemoryFactVersionResponse(
            id=version.id,
            fact_id=version.fact_id,
            proposal_id=version.proposal_id,
            version_number=version.version_number,
            status=version.status,
            content=version.content,
            summary=version.summary,
            content_hash=version.content_hash,
            change_reason=version.change_reason,
            changed_by_id=version.changed_by_id,
            metadata=version.metadata or {},
            created_at=version.created_at,
            updated_at=version.updated_at,
        )
