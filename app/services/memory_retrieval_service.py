"""DB-backed lexical retrieval for approved memory facts."""

import re
from dataclasses import dataclass
from uuid import UUID

from tortoise.expressions import Q

from app.models.memory import MemoryFact
from app.schemas.context import ActorContext
from app.schemas.enums import MemoryStatus, RetrievalMode, ScopeType
from app.schemas.mcp import McpMemoryResult, McpSearchMemoriesResult
from app.schemas.memory import MemoryScope, MemorySearchRequest, MemorySearchResult
from app.schemas.repository import RepositoryContext
from app.services.audit_service import AuditService
from app.services.config_service import EngramConfigService
from app.services.rbac_service import RbacService
from app.services.vortex_http import bad_request


@dataclass(frozen=True)
class _SearchScope:
    """Internal normalized scope used to keep query construction simple."""

    scope_type: ScopeType
    scope_id: UUID


@dataclass(frozen=True)
class _ScoredMemory:
    """Pairs a memory fact with its lexical score and match explanation."""

    memory_fact: MemoryFact
    score: float
    match_reason: str


class MemoryRetrievalService:
    """Searches approved memory facts without relying on Qdrant or embeddings."""

    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100
    CANDIDATE_MULTIPLIER = 5
    MAX_CANDIDATES = 500

    @classmethod
    async def search_memories(
        cls,
        actor: ActorContext,
        request: MemorySearchRequest,
        repository_context: RepositoryContext | None = None,
    ) -> list[MemorySearchResult]:
        """Return approved, readable memories ranked by simple lexical relevance."""
        cls._ensure_supported_retrieval_mode(request.retrieval_mode)
        limit = cls._effective_limit(request.limit)
        scopes = cls._resolve_search_scopes(actor, request, repository_context)
        query_text = cls._normalize_query(request.query)
        action = cls._audit_action(request, query_text)
        if not scopes:
            await AuditService.log_memory_search(
                actor, request, [], repository_context, action=action
            )
            return []

        candidate_limit = cls._candidate_limit(limit)
        memory_facts = await cls._fetch_candidates(
            actor, scopes, query_text, candidate_limit
        )
        readable_memory_facts = [
            memory_fact
            for memory_fact in memory_facts
            if RbacService.can_read_memory(actor, memory_fact)
        ]

        scored_memories = [
            cls._score_memory(memory_fact, query_text)
            for memory_fact in readable_memory_facts
        ]
        if query_text:
            scored_memories = [
                scored_memory
                for scored_memory in scored_memories
                if scored_memory.score > 0
            ]

        scored_memories.sort(
            key=lambda scored_memory: (
                scored_memory.score,
                scored_memory.memory_fact.updated_at,
                scored_memory.memory_fact.created_at,
            ),
            reverse=True,
        )
        scoped_scored_memories = cls._apply_per_scope_limit(scored_memories)
        results = [
            cls._memory_search_result(scored_memory)
            for scored_memory in scoped_scored_memories[:limit]
        ]
        await AuditService.log_memory_search(
            actor, request, results, repository_context, action=action
        )
        return results

    @classmethod
    async def search_memories_for_mcp(
        cls,
        actor: ActorContext,
        request: MemorySearchRequest,
        repository_context: RepositoryContext | None = None,
    ) -> McpSearchMemoriesResult:
        """Return compact MCP-facing search results."""
        limit = cls._effective_limit(request.limit)
        search_results = await cls.search_memories(actor, request, repository_context)
        return McpSearchMemoriesResult(
            results=[
                cls._mcp_memory_result(search_result)
                for search_result in search_results
            ],
            limit=limit,
        )

    @classmethod
    async def list_scoped_memories(
        cls,
        actor: ActorContext,
        request: MemorySearchRequest,
        repository_context: RepositoryContext | None = None,
    ) -> list[MemorySearchResult]:
        """List approved scoped memories without requiring a query string."""
        list_request = request.model_copy(
            update={"query": None, "retrieval_mode": RetrievalMode.ALL_SCOPED}
        )
        return await cls.search_memories(actor, list_request, repository_context)

    @classmethod
    def _ensure_supported_retrieval_mode(cls, retrieval_mode: RetrievalMode) -> None:
        if retrieval_mode not in {
            RetrievalMode.AUTO,
            RetrievalMode.LEXICAL,
            RetrievalMode.ALL_SCOPED,
        }:
            raise bad_request(
                "Only auto, lexical, and all_scoped retrieval are available before semantic retrieval is wired"
            )

    @classmethod
    def _audit_action(cls, request: MemorySearchRequest, query_text: str) -> str:
        if request.retrieval_mode == RetrievalMode.ALL_SCOPED and not query_text:
            return "memory_list"
        return "memory_search"

    @classmethod
    def _effective_limit(cls, requested_limit: int | None) -> int:
        settings = EngramConfigService.engram()
        configured_max = min(settings.max_search_results, cls.MAX_LIMIT)
        default_limit = min(cls.DEFAULT_LIMIT, configured_max)
        if requested_limit is None:
            return default_limit
        return max(1, min(requested_limit, configured_max))

    @classmethod
    def _candidate_limit(cls, result_limit: int) -> int:
        return min(
            max(result_limit * cls.CANDIDATE_MULTIPLIER, result_limit),
            cls.MAX_CANDIDATES,
        )

    @classmethod
    def _apply_per_scope_limit(
        cls, scored_memories: list[_ScoredMemory]
    ) -> list[_ScoredMemory]:
        per_scope_limit = EngramConfigService.engram().per_scope_search_results
        if not per_scope_limit:
            return scored_memories

        scoped_counts: dict[tuple[ScopeType, UUID], int] = {}
        bounded_scored_memories = []
        for scored_memory in scored_memories:
            memory_fact = scored_memory.memory_fact
            scope_key = (memory_fact.scope_type, memory_fact.scope_id)
            current_count = scoped_counts.get(scope_key, 0)
            if current_count < per_scope_limit:
                scoped_counts[scope_key] = current_count + 1
                bounded_scored_memories.append(scored_memory)
        return bounded_scored_memories

    @classmethod
    def _resolve_search_scopes(
        cls,
        actor: ActorContext,
        request: MemorySearchRequest,
        repository_context: RepositoryContext | None,
    ) -> list[_SearchScope]:
        scopes: list[_SearchScope] = []

        for requested_scope in request.scopes:
            cls._append_scope(
                scopes, requested_scope.scope_type, requested_scope.scope_id
            )

        if not request.scopes:
            if (
                request.include_repo_scope
                and repository_context
                and repository_context.repo_id
            ):
                cls._append_scope(scopes, ScopeType.REPO, repository_context.repo_id)
            if request.include_user_scope:
                cls._append_scope(scopes, ScopeType.USER, actor.actor_user_id)
            if request.include_org_scope:
                cls._append_scope(scopes, ScopeType.ORG, actor.org_id)

        return scopes

    @classmethod
    def _append_scope(
        cls, scopes: list[_SearchScope], scope_type: ScopeType, scope_id: UUID
    ) -> None:
        scope = _SearchScope(scope_type=scope_type, scope_id=scope_id)
        if scope not in scopes:
            scopes.append(scope)

    @classmethod
    async def _fetch_candidates(
        cls,
        actor: ActorContext,
        scopes: list[_SearchScope],
        query_text: str,
        candidate_limit: int,
    ) -> list[MemoryFact]:
        scope_filter = cls._scope_filter(scopes)
        base_filters = (
            Q(org_id=actor.org_id) & Q(status=MemoryStatus.APPROVED) & scope_filter
        )
        query_filter = cls._query_filter(query_text)

        if not query_filter:
            return await cls._fetch_candidate_batch(base_filters, candidate_limit)

        matched_candidates = await cls._fetch_candidate_batch(
            base_filters & query_filter, candidate_limit
        )
        recent_candidates = await cls._fetch_candidate_batch(
            base_filters, candidate_limit
        )
        return cls._dedupe_candidates([*matched_candidates, *recent_candidates])[
            :candidate_limit
        ]

    @classmethod
    async def _fetch_candidate_batch(
        cls, filters: Q, candidate_limit: int
    ) -> list[MemoryFact]:
        return await (
            MemoryFact.filter(filters)
            .select_related("repository")
            .prefetch_related("fact_tags__tag")
            .distinct()
            .order_by("-updated_at", "-created_at")
            .limit(candidate_limit)
        )

    @classmethod
    def _dedupe_candidates(cls, memory_facts: list[MemoryFact]) -> list[MemoryFact]:
        deduped_memory_facts = []
        seen_memory_fact_ids = set()
        for memory_fact in memory_facts:
            if memory_fact.id not in seen_memory_fact_ids:
                seen_memory_fact_ids.add(memory_fact.id)
                deduped_memory_facts.append(memory_fact)
        return deduped_memory_facts

    @classmethod
    def _scope_filter(cls, scopes: list[_SearchScope]) -> Q:
        scope_filter = Q()
        for scope in scopes:
            scope_filter |= Q(scope_type=scope.scope_type, scope_id=scope.scope_id)
        return scope_filter

    @classmethod
    def _query_filter(cls, query_text: str) -> Q | None:
        if not query_text:
            return None

        query_filter = Q(content__icontains=query_text) | Q(
            summary__icontains=query_text
        )
        for token in cls._query_tokens(query_text):
            query_filter |= Q(content__icontains=token)
            query_filter |= Q(summary__icontains=token)
            query_filter |= Q(repository__display_name__icontains=token)
            query_filter |= Q(repository__repository_key__icontains=token)
            query_filter |= Q(repository__repo_slug__icontains=token)
            query_filter |= Q(fact_tags__tag__slug__icontains=token)
            query_filter |= Q(fact_tags__tag__label__icontains=token)
        return query_filter

    @classmethod
    def _score_memory(cls, memory_fact: MemoryFact, query_text: str) -> _ScoredMemory:
        if not query_text:
            return _ScoredMemory(
                memory_fact=memory_fact,
                score=1.0,
                match_reason="recent approved scoped memory",
            )

        searchable_text = cls._searchable_text(memory_fact)
        searchable_text_lower = searchable_text.lower()
        query_text_lower = query_text.lower()
        score = 0.0
        reasons: list[str] = []

        if query_text_lower in cls._safe_lower(memory_fact.content):
            score += 5.0
            reasons.append("content phrase")
        if query_text_lower in cls._safe_lower(memory_fact.summary):
            score += 4.0
            reasons.append("summary phrase")

        tags = cls._tags_from_memory(memory_fact)
        tag_text = " ".join(tags).lower()
        if query_text_lower in tag_text:
            score += 3.0
            reasons.append("tag phrase")

        repository_text = cls._repository_text(memory_fact).lower()
        if query_text_lower in repository_text:
            score += 2.0
            reasons.append("repository phrase")

        matched_tokens = 0
        for token in cls._query_tokens(query_text):
            token_score = cls._score_token(
                token, memory_fact, searchable_text_lower, tag_text, repository_text
            )
            if token_score > 0:
                matched_tokens += 1
                score += token_score

        if matched_tokens:
            reasons.append(
                f"{matched_tokens} token match"
                if matched_tokens == 1
                else f"{matched_tokens} token matches"
            )

        return _ScoredMemory(
            memory_fact=memory_fact,
            score=round(score, 4),
            match_reason=", ".join(reasons) if reasons else "no lexical match",
        )

    @classmethod
    def _score_token(
        cls,
        token: str,
        memory_fact: MemoryFact,
        searchable_text_lower: str,
        tag_text: str,
        repository_text: str,
    ) -> float:
        token_score = 0.0
        if token in cls._safe_lower(memory_fact.content):
            token_score += 1.5
        if token in cls._safe_lower(memory_fact.summary):
            token_score += 1.25
        if token in tag_text:
            token_score += 1.0
        if token in repository_text:
            token_score += 0.75
        if token in searchable_text_lower:
            token_score += 0.25
        return token_score

    @classmethod
    def _memory_search_result(cls, scored_memory: _ScoredMemory) -> MemorySearchResult:
        memory_fact = scored_memory.memory_fact
        return MemorySearchResult(
            id=memory_fact.id,
            org_id=memory_fact.org_id,
            repository_id=memory_fact.repository_id,
            owner_user_id=memory_fact.owner_user_id,
            scope_type=memory_fact.scope_type,
            scope_id=memory_fact.scope_id,
            status=memory_fact.status,
            content=memory_fact.content,
            summary=memory_fact.summary,
            tags=cls._tags_from_memory(memory_fact),
            source=memory_fact.source,
            metadata=memory_fact.metadata or {},
            created_at=memory_fact.created_at,
            updated_at=memory_fact.updated_at,
            score=scored_memory.score,
            match_reason=scored_memory.match_reason,
        )

    @classmethod
    def _mcp_memory_result(cls, search_result: MemorySearchResult) -> McpMemoryResult:
        return McpMemoryResult(
            id=search_result.id,
            scope_type=search_result.scope_type,
            content=search_result.content,
            summary=search_result.summary,
            tags=search_result.tags,
            score=search_result.score,
            match_reason=search_result.match_reason,
            updated_at=search_result.updated_at.isoformat(),
        )

    @classmethod
    def _searchable_text(cls, memory_fact: MemoryFact) -> str:
        parts = [
            memory_fact.content,
            memory_fact.summary or "",
            " ".join(cls._tags_from_memory(memory_fact)),
            cls._repository_text(memory_fact),
        ]
        return "\n".join(part for part in parts if part)

    @classmethod
    def _repository_text(cls, memory_fact: MemoryFact) -> str:
        repository = getattr(memory_fact, "repository", None)
        if not repository:
            return ""
        parts = [
            repository.display_name or "",
            repository.repository_key or "",
            repository.host or "",
            repository.workspace or "",
            repository.repo_slug or "",
        ]
        return " ".join(part for part in parts if part)

    @classmethod
    def _tags_from_memory(cls, memory_fact: MemoryFact) -> list[str]:
        tags = cls._tags_from_metadata(memory_fact.metadata)
        related_tags = cls._tags_from_prefetched_relations(memory_fact)
        return cls._normalize_tags([*tags, *related_tags])

    @classmethod
    def _tags_from_metadata(cls, metadata: dict | None) -> list[str]:
        tags = (metadata or {}).get("tags", [])
        if not isinstance(tags, list):
            return []
        return cls._normalize_tags(tags)

    @classmethod
    def _tags_from_prefetched_relations(cls, memory_fact: MemoryFact) -> list[str]:
        relation_container = getattr(memory_fact, "fact_tags", None)
        if not relation_container:
            return []

        # Tortoise stores prefetched reverse relations in a list-like container.
        tag_labels = []
        for fact_tag in relation_container:
            tag = getattr(fact_tag, "tag", None)
            if tag:
                tag_labels.extend([tag.slug, tag.label])
        return cls._normalize_tags(tag_labels)

    @classmethod
    def _normalize_tags(cls, tags: list[str]) -> list[str]:
        normalized_tags = []
        seen_tags = set()
        for tag in tags:
            normalized_tag = str(tag).strip().lower()
            if normalized_tag and normalized_tag not in seen_tags:
                seen_tags.add(normalized_tag)
                normalized_tags.append(normalized_tag)
        return normalized_tags

    @classmethod
    def _normalize_query(cls, query: str | None) -> str:
        return " ".join((query or "").strip().split())

    @classmethod
    def _query_tokens(cls, query_text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_.:/-]*", query_text.lower())
        deduped_tokens = []
        seen_tokens = set()
        for token in tokens:
            if token not in seen_tokens:
                seen_tokens.add(token)
                deduped_tokens.append(token)
        return deduped_tokens

    @classmethod
    def _safe_lower(cls, value: str | None) -> str:
        return (value or "").lower()

    @classmethod
    def default_search_request(
        cls,
        query: str | None,
        limit: int | None = None,
        scopes: list[MemoryScope] | None = None,
    ) -> MemorySearchRequest:
        """Small convenience constructor for future REST/MCP callers."""
        return MemorySearchRequest(
            query=query,
            retrieval_mode=RetrievalMode.LEXICAL,
            scopes=scopes or [],
            include_user_scope=True,
            include_repo_scope=True,
            include_org_scope=True,
            limit=limit or cls.DEFAULT_LIMIT,
        )
