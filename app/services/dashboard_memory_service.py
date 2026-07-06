"""Dashboard-facing memory fact and proposal query helpers."""

from uuid import UUID

from tortoise.expressions import Q

from app.models.identity import Organization, User
from app.models.memory import MemoryFact, MemoryFactTag, Tag
from app.models.repository import Repository
from app.models.review import MemoryProposal
from app.schemas.context import ActorContext
from app.schemas.enums import (
    MemoryListSection,
    MemoryStatus,
    ProposalStatus,
    ProposalType,
    ScopeType,
)
from app.schemas.memory import (
    MemoryDeletionProposalRequest,
    MemoryDisplayContextResponse,
    MemoryDisplayEntityResponse,
    MemoryFactResponse,
    MemoryListRequest,
    MemoryProposalResponse,
    MemoryStatusChangeRequest,
    MemoryUpdateProposalRequest,
)
from app.services.audit_service import AuditService
from app.services.memory_retrieval_service import MemoryRetrievalService
from app.services.memory_service import MemoryService
from app.services.rbac_service import RbacService
from app.services.vortex_http import bad_request, forbidden, not_found


class DashboardMemoryService:
    """Read/query boundary for dashboard REST APIs."""

    @classmethod
    async def list_memories(
        cls, actor: ActorContext, request: MemoryListRequest
    ) -> list[MemoryFactResponse]:
        cls._ensure_org_filter_is_allowed(actor, request.org_id)
        filters = cls._memory_filters(actor, request)
        memory_facts = await (
            MemoryFact.filter(filters)
            .prefetch_related("fact_tags__tag")
            .distinct()
            .order_by("-updated_at", "-created_at")
            .offset(request.offset)
            .limit(request.limit)
        )
        results = [
            cls._memory_fact_response(memory_fact) for memory_fact in memory_facts
        ]
        await AuditService.log_dashboard_memory_list(actor, request, results)
        return results

    @classmethod
    async def get_memory(
        cls, actor: ActorContext, memory_id: UUID
    ) -> MemoryFactResponse:
        memory_fact = await cls._get_readable_memory_fact(actor, memory_id)
        response = await cls._enriched_memory_fact_response(memory_fact)
        await AuditService.log_memory_read(actor, response)
        return response

    @classmethod
    async def propose_memory_update(
        cls,
        actor: ActorContext,
        memory_id: UUID,
        request: MemoryUpdateProposalRequest,
    ) -> MemoryProposalResponse:
        if request.memory_fact_id != memory_id:
            raise bad_request("Path memory id must match request memory_fact_id")
        return await MemoryService.create_update_proposal(actor, request)

    @classmethod
    async def delete_memory(
        cls,
        actor: ActorContext,
        memory_id: UUID,
        request: MemoryStatusChangeRequest,
    ) -> MemoryFactResponse | MemoryProposalResponse:
        memory_fact = await cls._get_readable_memory_fact(actor, memory_id)
        if memory_fact.scope_type == ScopeType.USER:
            return await MemoryService.delete_user_memory(actor, memory_id, request)

        deletion_request = MemoryDeletionProposalRequest(
            memory_fact_id=memory_id,
            reason=request.reason,
            metadata=request.metadata,
        )
        return await MemoryService.create_deletion_proposal(actor, deletion_request)

    @classmethod
    async def attach_tag(
        cls, actor: ActorContext, memory_id: UUID, tag_id: UUID
    ) -> MemoryFactResponse:
        memory_fact = await cls._get_readable_memory_fact(actor, memory_id)
        cls._ensure_can_tag_memory(actor, memory_fact)
        tag = await cls._get_tag(actor, tag_id)
        await MemoryFactTag.get_or_create(
            org_id=actor.org_id,
            fact_id=memory_fact.id,
            tag_id=tag.id,
            defaults={"metadata": {"assigned_by_user_id": str(actor.actor_user_id)}},
        )
        return await cls._enriched_memory_fact_response(
            await cls._get_readable_memory_fact(actor, memory_id)
        )

    @classmethod
    async def detach_tag(
        cls, actor: ActorContext, memory_id: UUID, tag_id: UUID
    ) -> MemoryFactResponse:
        memory_fact = await cls._get_readable_memory_fact(actor, memory_id)
        cls._ensure_can_tag_memory(actor, memory_fact)
        tag = await cls._get_tag(actor, tag_id)
        await MemoryFactTag.filter(
            org_id=actor.org_id, fact_id=memory_fact.id, tag_id=tag.id
        ).delete()
        return await cls._enriched_memory_fact_response(
            await cls._get_readable_memory_fact(actor, memory_id)
        )

    @classmethod
    async def list_proposals(
        cls,
        actor: ActorContext,
        proposal_status: ProposalStatus | None = None,
        proposal_type: ProposalType | None = None,
        scope_type: ScopeType | None = None,
        scope_id: UUID | None = None,
        fact_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryProposalResponse]:
        filters = Q(org_id=actor.org_id)
        if proposal_status:
            filters &= Q(status=proposal_status)
        if proposal_type:
            filters &= Q(proposal_type=proposal_type)
        if scope_type:
            filters &= Q(scope_type=scope_type)
        if scope_id:
            filters &= Q(scope_id=scope_id)
        if fact_id:
            filters &= Q(fact_id=fact_id)

        proposals = await (
            MemoryProposal.filter(filters)
            .order_by("-updated_at", "-created_at")
            .offset(offset)
            .limit(limit)
        )
        return [
            MemoryService._memory_proposal_response(proposal)
            for proposal in proposals
            if cls._can_read_proposal(actor, proposal)
        ]

    @classmethod
    async def get_proposal(
        cls, actor: ActorContext, proposal_id: UUID
    ) -> MemoryProposalResponse:
        proposal = await MemoryProposal.get_or_none(id=proposal_id, org_id=actor.org_id)
        if not proposal:
            raise not_found("Memory proposal not found")
        if not cls._can_read_proposal(actor, proposal):
            raise forbidden("Actor cannot read this proposal")
        return MemoryService._memory_proposal_response(proposal)

    @classmethod
    def _memory_filters(cls, actor: ActorContext, request: MemoryListRequest) -> Q:
        filters = Q(org_id=actor.org_id)
        if request.section:
            filters &= cls._section_memory_filter(actor, request.section)
        filters &= cls._readable_memory_filter(actor)

        # Keep the existing narrow filters for callers that need precise scoping,
        # while the dashboard uses `section` for the primary memory grouping.
        if request.scope_type:
            filters &= Q(scope_type=request.scope_type)
        if request.scope_id:
            filters &= Q(scope_id=request.scope_id)
        if request.repo_id:
            filters &= Q(repository_id=request.repo_id)
        if request.owner_user_id:
            filters &= Q(owner_user_id=request.owner_user_id)
        if request.status:
            filters &= Q(status=request.status)
        if request.tag:
            normalized_tag = request.tag.strip().lower()
            filters &= Q(fact_tags__tag__slug__icontains=normalized_tag) | Q(
                fact_tags__tag__label__icontains=normalized_tag
            )
        if request.created_by:
            filters &= Q(created_by_id=request.created_by)
        if request.approved_by:
            filters &= Q(approved_by_id=request.approved_by)
        if request.created_from:
            filters &= Q(created_at__gte=request.created_from)
        if request.created_to:
            filters &= Q(created_at__lte=request.created_to)
        if request.updated_from:
            filters &= Q(updated_at__gte=request.updated_from)
        if request.updated_to:
            filters &= Q(updated_at__lte=request.updated_to)
        if request.query:
            query_text = " ".join(request.query.strip().split())
            filters &= Q(content__icontains=query_text) | Q(
                summary__icontains=query_text
            )
        return filters

    @classmethod
    def _section_memory_filter(
        cls, actor: ActorContext, section: MemoryListSection
    ) -> Q:
        if section == MemoryListSection.MY:
            return Q(scope_type=ScopeType.USER, scope_id=actor.actor_user_id)
        if section == MemoryListSection.ALL:
            if not RbacService.is_admin(actor):
                raise forbidden("Admin access is required to list all memories")
            return Q()
        if section == MemoryListSection.REPO:
            return Q(scope_type=ScopeType.REPO)
        if section == MemoryListSection.ORG:
            return Q(scope_type=ScopeType.ORG)
        raise bad_request("Unknown memory section")

    @classmethod
    def _readable_memory_filter(cls, actor: ActorContext) -> Q:
        if RbacService.is_admin(actor):
            return Q()

        return Q(status=MemoryStatus.APPROVED) & (
            Q(scope_type=ScopeType.USER, scope_id=actor.actor_user_id)
            | Q(scope_type=ScopeType.REPO)
            | Q(scope_type=ScopeType.ORG)
        )

    @classmethod
    async def _get_readable_memory_fact(
        cls, actor: ActorContext, memory_id: UUID
    ) -> MemoryFact:
        memory_fact = await (
            MemoryFact.filter(id=memory_id, org_id=actor.org_id)
            .prefetch_related("fact_tags__tag")
            .first()
        )
        if not memory_fact:
            raise not_found("Memory fact not found")
        if not RbacService.can_read_memory(actor, memory_fact):
            raise forbidden("Actor cannot read this memory")
        return memory_fact

    @classmethod
    async def _get_tag(cls, actor: ActorContext, tag_id: UUID) -> Tag:
        tag = await Tag.get_or_none(id=tag_id, org_id=actor.org_id)
        if not tag:
            raise not_found("Tag not found")
        return tag

    @classmethod
    def _ensure_org_filter_is_allowed(
        cls, actor: ActorContext, requested_org_id: UUID | None
    ) -> None:
        if requested_org_id and requested_org_id != actor.org_id:
            raise forbidden("Actor cannot read another organization")

    @classmethod
    def _ensure_can_tag_memory(
        cls, actor: ActorContext, memory_fact: MemoryFact
    ) -> None:
        if not RbacService.can_edit_memory(actor, memory_fact):
            raise forbidden("Actor cannot tag this memory")

    @classmethod
    def _can_read_proposal(cls, actor: ActorContext, proposal: MemoryProposal) -> bool:
        if proposal.org_id != actor.org_id:
            return False
        return proposal.created_by_id == actor.actor_user_id or RbacService.is_admin(
            actor
        )

    @classmethod
    def _memory_fact_response(cls, memory_fact: MemoryFact) -> MemoryFactResponse:
        response = MemoryService._memory_fact_response(memory_fact)
        return response.model_copy(
            update={"tags": MemoryRetrievalService._tags_from_memory(memory_fact)}
        )

    @classmethod
    async def _enriched_memory_fact_response(
        cls, memory_fact: MemoryFact
    ) -> MemoryFactResponse:
        response = cls._memory_fact_response(memory_fact)
        display_context = await cls._memory_display_context(response)
        return response.model_copy(update={"display_context": display_context})

    @classmethod
    async def _memory_display_context(
        cls, memory: MemoryFactResponse
    ) -> MemoryDisplayContextResponse:
        organization = await cls._resolve_organization(memory.org_id)
        repository = await cls._resolve_repository(memory)
        owner_user = await cls._resolve_owner_user(memory)
        scope = await cls._resolve_scope(memory, organization, repository, owner_user)

        return MemoryDisplayContextResponse(
            organization=cls._organization_entity(organization),
            repository=cls._repository_entity(repository),
            owner_user=cls._user_entity(owner_user),
            scope=scope,
        )

    @classmethod
    async def _resolve_organization(cls, org_id: UUID) -> Organization | None:
        return await Organization.get_or_none(id=org_id)

    @classmethod
    async def _resolve_repository(cls, memory: MemoryFactResponse) -> Repository | None:
        repository_id = memory.repository_id
        if memory.scope_type == ScopeType.REPO:
            repository_id = repository_id or memory.scope_id
        if not repository_id:
            return None
        return await Repository.get_or_none(id=repository_id, org_id=memory.org_id)

    @classmethod
    async def _resolve_owner_user(cls, memory: MemoryFactResponse) -> User | None:
        if not memory.owner_user_id:
            return None
        return await User.get_or_none(id=memory.owner_user_id)

    @classmethod
    async def _resolve_scope(
        cls,
        memory: MemoryFactResponse,
        organization: Organization | None,
        repository: Repository | None,
        owner_user: User | None,
    ) -> MemoryDisplayEntityResponse | None:
        if memory.scope_type == ScopeType.ORG:
            scope_organization = organization
            if not scope_organization or scope_organization.id != memory.scope_id:
                scope_organization = await Organization.get_or_none(id=memory.scope_id)
            return cls._organization_entity(scope_organization)

        if memory.scope_type == ScopeType.REPO:
            scope_repository = repository
            if not scope_repository or scope_repository.id != memory.scope_id:
                scope_repository = await Repository.get_or_none(
                    id=memory.scope_id, org_id=memory.org_id
                )
            return cls._repository_entity(scope_repository)

        scope_user = owner_user
        if not scope_user or scope_user.id != memory.scope_id:
            scope_user = await User.get_or_none(id=memory.scope_id)
        return cls._user_entity(scope_user)

    @classmethod
    def _organization_entity(
        cls, organization: Organization | None
    ) -> MemoryDisplayEntityResponse | None:
        if not organization:
            return None
        return MemoryDisplayEntityResponse(
            id=organization.id,
            label=organization.name,
            detail=organization.slug,
            metadata={"slug": organization.slug, "is_active": organization.is_active},
        )

    @classmethod
    def _repository_entity(
        cls, repository: Repository | None
    ) -> MemoryDisplayEntityResponse | None:
        if not repository:
            return None
        return MemoryDisplayEntityResponse(
            id=repository.id,
            label=repository.display_name or repository.repo_slug,
            detail=repository.repository_key,
            metadata={
                "provider": repository.provider,
                "host": repository.host,
                "workspace": repository.workspace,
                "repo_slug": repository.repo_slug,
                "repository_key": repository.repository_key,
                "canonical_remote_url": repository.canonical_remote_url,
                "is_active": repository.is_active,
            },
        )

    @classmethod
    def _user_entity(cls, user: User | None) -> MemoryDisplayEntityResponse | None:
        if not user:
            return None
        return MemoryDisplayEntityResponse(
            id=user.id,
            label=user.display_name or user.email,
            detail=user.email,
            metadata={
                "email": user.email,
                "display_name": user.display_name,
                "is_active": user.is_active,
            },
        )
