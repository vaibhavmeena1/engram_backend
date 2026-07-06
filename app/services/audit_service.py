"""Non-fatal audit logging for memory access and mutation events."""

import hashlib
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from app.models.audit import MemoryAccessLog
from app.schemas.context import ActorContext
from app.schemas.memory import (
    MemoryFactResponse,
    MemoryListRequest,
    MemoryProposalResponse,
    MemorySearchRequest,
    MemorySearchResult,
)
from app.schemas.repository import RepositoryContext


class AuditService:
    """Writes best-effort audit rows without coupling product flows to logging success."""

    @classmethod
    async def log_memory_search(
        cls,
        actor: ActorContext,
        request: MemorySearchRequest,
        results: list[MemorySearchResult],
        repository_context: RepositoryContext | None = None,
        action: str = "memory_search",
    ) -> None:
        await cls.log_memory_event(
            actor=actor,
            action=action,
            repository_id=repository_context.repo_id if repository_context else None,
            query_text=request.query,
            returned_memory_ids=[result.id for result in results],
            scope_filters=cls._schema_dump(request),
            scores={str(result.id): result.score for result in results},
            metadata={
                "retrieval_mode": cls._jsonable(request.retrieval_mode),
                "result_count": len(results),
            },
        )

    @classmethod
    async def log_dashboard_memory_list(
        cls,
        actor: ActorContext,
        request: MemoryListRequest,
        results: list[MemoryFactResponse],
    ) -> None:
        await cls.log_memory_event(
            actor=actor,
            action="memory_list",
            repository_id=request.repo_id,
            query_text=request.query,
            returned_memory_ids=[result.id for result in results],
            scope_filters=cls._schema_dump(request),
            metadata={"result_count": len(results)},
        )

    @classmethod
    async def log_memory_read(
        cls, actor: ActorContext, memory_fact: MemoryFactResponse
    ) -> None:
        await cls.log_memory_event(
            actor=actor,
            action="memory_read",
            memory_fact_id=memory_fact.id,
            repository_id=memory_fact.repository_id,
            returned_memory_ids=[memory_fact.id],
            scope_filters={
                "scope_type": memory_fact.scope_type,
                "scope_id": memory_fact.scope_id,
            },
            metadata={"status": memory_fact.status},
        )

    @classmethod
    async def log_memory_create(
        cls, actor: ActorContext, memory_fact: MemoryFactResponse
    ) -> None:
        await cls.log_memory_event(
            actor=actor,
            action="memory_create",
            memory_fact_id=memory_fact.id,
            repository_id=memory_fact.repository_id,
            returned_memory_ids=[memory_fact.id],
            scope_filters={
                "scope_type": memory_fact.scope_type,
                "scope_id": memory_fact.scope_id,
            },
            metadata={"status": memory_fact.status, "source": memory_fact.source},
        )

    @classmethod
    async def log_proposal_create(
        cls, actor: ActorContext, proposal: MemoryProposalResponse
    ) -> None:
        await cls.log_memory_event(
            actor=actor,
            action="proposal_create",
            proposal_id=proposal.id,
            memory_fact_id=proposal.fact_id,
            repository_id=proposal.repository_id,
            scope_filters={
                "scope_type": proposal.scope_type,
                "scope_id": proposal.scope_id,
            },
            metadata={
                "proposal_type": proposal.proposal_type,
                "status": proposal.status,
                "contains_possible_secret": proposal.contains_possible_secret,
            },
        )

    @classmethod
    async def log_proposal_review(
        cls,
        actor: ActorContext,
        proposal_id: UUID,
        memory_fact_id: UUID | None,
        action: str,
        status: str,
        applied: bool,
        metadata: dict | None = None,
    ) -> None:
        await cls.log_memory_event(
            actor=actor,
            action=action,
            proposal_id=proposal_id,
            memory_fact_id=memory_fact_id,
            returned_memory_ids=[memory_fact_id] if memory_fact_id else [],
            metadata={"status": status, "applied": applied, **(metadata or {})},
        )

    @classmethod
    async def log_memory_delete(
        cls,
        actor: ActorContext,
        memory_fact_id: UUID,
        action: str = "memory_delete",
        repository_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> None:
        await cls.log_memory_event(
            actor=actor,
            action=action,
            memory_fact_id=memory_fact_id,
            repository_id=repository_id,
            returned_memory_ids=[memory_fact_id],
            metadata=metadata or {},
        )

    @classmethod
    async def log_memory_event(
        cls,
        actor: ActorContext,
        action: str,
        memory_fact_id: UUID | None = None,
        proposal_id: UUID | None = None,
        repository_id: UUID | None = None,
        query_text: str | None = None,
        returned_memory_ids: list[UUID | str] | None = None,
        scope_filters: dict | None = None,
        scores: dict | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Persist one audit event; failures are intentionally non-fatal."""
        try:
            await MemoryAccessLog.create(
                org_id=actor.org_id,
                actor_user_id=actor.actor_user_id,
                repository_id=repository_id,
                memory_fact_id=memory_fact_id,
                proposal_id=proposal_id,
                action=action,
                auth_method=actor.auth_method.value if actor.auth_method else None,
                client_type=actor.client_type.value if actor.client_type else None,
                session_id=actor.session_id,
                personal_access_token_id=actor.personal_access_token_id,
                client_name=actor.client_name,
                request_id=actor.request_id,
                query_hash=cls._query_hash(query_text),
                returned_memory_ids=cls._jsonable(returned_memory_ids or []),
                scope_filters=cls._jsonable(scope_filters or {}),
                scores=cls._jsonable(scores or {}),
                metadata=cls._jsonable(metadata or {}),
            )
        except Exception:  # noqa: BLE001 - audit logging must never break memory operations.
            return

    @classmethod
    def _query_hash(cls, query_text: str | None) -> str | None:
        normalized_query = " ".join((query_text or "").strip().split())
        if not normalized_query:
            return None
        return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()

    @classmethod
    def _schema_dump(cls, schema: Any) -> dict:
        if hasattr(schema, "model_dump"):
            return schema.model_dump(mode="json")
        if isinstance(schema, dict):
            return schema
        return {}

    @classmethod
    def _jsonable(cls, value: Any) -> Any:
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime | date):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(key): cls._jsonable(item) for key, item in value.items()}
        if isinstance(value, list | tuple | set):
            return [cls._jsonable(item) for item in value]
        return value
