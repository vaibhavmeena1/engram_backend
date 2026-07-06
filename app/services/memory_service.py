"""Core memory creation, mutation, and review workflows."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from tortoise.transactions import in_transaction

from app.models.identity import User
from app.models.memory import (
    MemoryFact,
    MemoryFactTag,
    MemoryFactVersion,
    MemoryObservation,
    Tag,
)
from app.models.repository import Repository
from app.models.review import MemoryProposal
from app.schemas.context import ActorContext
from app.schemas.enums import MemoryStatus, ProposalStatus, ProposalType, ScopeType
from app.schemas.memory import (
    MemoryCreateRequest,
    MemoryDeletionProposalRequest,
    MemoryFactResponse,
    MemoryProposalCreateRequest,
    MemoryProposalResponse,
    MemoryStatusChangeRequest,
    MemoryUpdateProposalRequest,
)
from app.schemas.review import (
    ProposalApplyEditedRequest,
    ProposalReviewRequest,
    ProposalReviewResult,
)
from app.services.audit_service import AuditService
from app.services.config_service import EngramConfigService
from app.services.rbac_service import RbacService
from app.services.safety_service import SafetyCheckResult, SafetyService
from app.services.tag_service import TagService
from app.services.vortex_http import bad_request, conflict, forbidden, not_found


class MemoryService:
    """Coordinates memory writes, proposals, review decisions, and version rows."""

    @classmethod
    async def create_memory(
        cls,
        actor: ActorContext,
        request: MemoryCreateRequest,
    ) -> MemoryFactResponse | MemoryProposalResponse:
        """Create memory directly unless the configured scope policy requires review."""
        if cls._requires_create_review(request.scope_type):
            proposal_request = MemoryProposalCreateRequest(
                **request.model_dump(), proposal_type=ProposalType.CREATE
            )
            return await cls.create_memory_proposal(actor, proposal_request)

        return await cls.create_direct_memory(actor, request)

    @classmethod
    async def create_direct_user_memory(
        cls,
        actor: ActorContext,
        request: MemoryCreateRequest,
    ) -> MemoryFactResponse:
        """Create an approved user-scoped memory fact and its initial version row."""
        cls._ensure_user_scope(request.scope_type)
        return await cls.create_direct_memory(actor, request)

    @classmethod
    async def create_direct_memory(
        cls,
        actor: ActorContext,
        request: MemoryCreateRequest,
    ) -> MemoryFactResponse:
        """Create an approved memory fact directly when review policy allows it."""
        cls._ensure_scope_can_be_created(actor, request.scope_type, request.scope_id)
        cls._ensure_valid_memory_scope(actor, request.scope_type, request.scope_id)
        owner_user = (
            await cls._resolve_user_scope(actor, request.scope_id)
            if request.scope_type == ScopeType.USER
            else None
        )
        repository = await cls._resolve_repository_for_scope(
            actor.org_id, request.scope_type, request.scope_id
        )

        safety_result = SafetyService.analyze_memory_payload(
            request.content, request.summary, request.metadata
        )
        cls._ensure_safe_for_auto_approval(safety_result)

        normalized_tags = cls._normalize_tags(request.tags)
        metadata = cls._metadata_with_safety(
            cls._metadata_with_tags(request.metadata, normalized_tags), safety_result
        )
        content_hash = cls.generate_content_hash(request.content, request.summary)
        now = cls._utcnow()

        async with in_transaction() as connection:
            memory_fact = await MemoryFact.create(
                org_id=actor.org_id,
                owner_user_id=owner_user.id if owner_user else None,
                repository_id=repository.id if repository else None,
                scope_type=request.scope_type,
                scope_id=request.scope_id,
                status=MemoryStatus.APPROVED,
                content=request.content,
                summary=request.summary,
                content_hash=content_hash,
                source=request.source,
                metadata=metadata,
                created_by_id=actor.actor_user_id,
                updated_by_id=actor.actor_user_id,
                approved_by_id=actor.actor_user_id,
                approved_at=now,
                using_db=connection,
            )
            await cls._sync_fact_tags(
                actor=actor,
                memory_fact=memory_fact,
                tags=normalized_tags,
                using_db=connection,
            )
            await cls._create_fact_version(
                memory_fact=memory_fact,
                proposal=None,
                changed_by_id=actor.actor_user_id,
                change_reason=f"direct_{request.scope_type.value}_create",
                metadata={
                    "action": "create",
                    "review_required": False,
                    "scope_type": request.scope_type.value,
                    "source": request.source.value,
                    "safety": safety_result.to_metadata(),
                },
                using_db=connection,
            )

        response = cls._memory_fact_response(memory_fact)
        await AuditService.log_memory_create(actor, response)
        return response

    @classmethod
    async def create_memory_proposal(
        cls,
        actor: ActorContext,
        request: MemoryProposalCreateRequest,
    ) -> MemoryProposalResponse:
        """Create a pending proposal for repo/org memory creation."""
        if request.proposal_type != ProposalType.CREATE:
            raise bad_request(
                "Use the update/delete proposal methods for non-create proposals"
            )
        if request.scope_type not in {ScopeType.REPO, ScopeType.ORG}:
            raise bad_request(
                "Only repo and org memories should be proposed for creation"
            )
        if not RbacService.can_propose_memory(
            actor, request.scope_type, request.scope_id
        ):
            raise forbidden("Actor cannot propose memory for this scope")

        cls._ensure_valid_proposal_scope(actor, request.scope_type, request.scope_id)
        existing_proposal = await cls._get_existing_idempotent_proposal(
            actor, request.idempotency_key
        )
        if existing_proposal:
            response = cls._memory_proposal_response(existing_proposal)
            await AuditService.log_proposal_create(actor, response)
            return response

        repository = await cls._resolve_repository_for_scope(
            actor.org_id, request.scope_type, request.scope_id
        )
        observation = await cls._resolve_observation(
            actor, request.observation_id, request.scope_type, request.scope_id
        )
        safety_result = SafetyService.analyze_memory_payload(
            request.content, request.summary, request.metadata
        )
        normalized_tags = cls._normalize_tags(request.tags)
        await cls._ensure_tag_records(actor, normalized_tags)
        proposed_metadata = cls._metadata_with_safety(
            cls._metadata_with_tags(request.metadata, normalized_tags),
            safety_result,
        )
        content_hash = cls.generate_content_hash(request.content, request.summary)
        contains_possible_secret = cls._proposal_contains_possible_secret(
            safety_result, observation
        )

        proposal = await MemoryProposal.create(
            org_id=actor.org_id,
            fact_id=None,
            observation_id=observation.id if observation else None,
            repository_id=repository.id if repository else None,
            scope_type=request.scope_type,
            scope_id=request.scope_id,
            proposal_type=request.proposal_type,
            status=ProposalStatus.PENDING,
            proposed_content=request.content,
            proposed_summary=request.summary,
            proposed_metadata=proposed_metadata,
            content_hash=content_hash,
            contains_possible_secret=contains_possible_secret,
            source=request.source,
            idempotency_key=request.idempotency_key,
            created_by_id=actor.actor_user_id,
            metadata=cls._proposal_metadata(
                actor=actor,
                metadata=request.metadata,
                tags=normalized_tags,
                observation=observation,
                safety_result=safety_result,
            ),
        )
        response = cls._memory_proposal_response(proposal)
        await AuditService.log_proposal_create(actor, response)
        return response

    @classmethod
    async def create_update_proposal(
        cls,
        actor: ActorContext,
        request: MemoryUpdateProposalRequest,
    ) -> MemoryProposalResponse:
        """Create a pending update proposal without mutating the approved fact."""
        existing_proposal = await cls._get_existing_idempotent_proposal(
            actor, request.idempotency_key
        )
        if existing_proposal:
            response = cls._memory_proposal_response(existing_proposal)
            await AuditService.log_proposal_create(actor, response)
            return response

        memory_fact = await cls._get_readable_memory_fact(actor, request.memory_fact_id)
        cls._ensure_fact_can_receive_update_proposal(memory_fact)
        if not RbacService.can_propose_memory(
            actor, memory_fact.scope_type, memory_fact.scope_id
        ):
            raise forbidden("Actor cannot propose updates for this memory scope")

        observation = await cls._resolve_observation(
            actor, request.observation_id, memory_fact.scope_type, memory_fact.scope_id
        )
        safety_result = SafetyService.analyze_memory_payload(
            request.content, request.summary, request.metadata
        )
        proposed_metadata = cls._metadata_with_safety(
            cls._metadata_with_tags(request.metadata, request.tags),
            safety_result,
        )
        contains_possible_secret = cls._proposal_contains_possible_secret(
            safety_result, observation
        )

        proposal = await MemoryProposal.create(
            org_id=actor.org_id,
            fact_id=memory_fact.id,
            observation_id=observation.id if observation else None,
            repository_id=cls._foreign_key_id(memory_fact, "repository"),
            scope_type=memory_fact.scope_type,
            scope_id=memory_fact.scope_id,
            proposal_type=ProposalType.UPDATE,
            status=ProposalStatus.PENDING,
            proposed_content=request.content,
            proposed_summary=request.summary,
            proposed_metadata=proposed_metadata,
            content_hash=cls.generate_content_hash(request.content, request.summary),
            contains_possible_secret=contains_possible_secret,
            source=request.source,
            idempotency_key=request.idempotency_key,
            created_by_id=actor.actor_user_id,
            metadata=cls._proposal_metadata(
                actor=actor,
                metadata=request.metadata,
                tags=request.tags,
                observation=observation,
                safety_result=safety_result,
                extra_metadata={
                    "target_fact_id": str(memory_fact.id),
                    "current_content_hash": memory_fact.content_hash,
                },
            ),
        )
        response = cls._memory_proposal_response(proposal)
        await AuditService.log_proposal_create(actor, response)
        return response

    @classmethod
    async def create_deletion_proposal(
        cls,
        actor: ActorContext,
        request: MemoryDeletionProposalRequest,
    ) -> MemoryProposalResponse:
        """Create a pending deletion proposal without mutating the approved fact."""
        existing_proposal = await cls._get_existing_idempotent_proposal(
            actor, request.idempotency_key
        )
        if existing_proposal:
            response = cls._memory_proposal_response(existing_proposal)
            await AuditService.log_proposal_create(actor, response)
            return response

        memory_fact = await cls._get_readable_memory_fact(actor, request.memory_fact_id)
        cls._ensure_fact_can_receive_delete_proposal(memory_fact)
        if not RbacService.can_propose_memory(
            actor, memory_fact.scope_type, memory_fact.scope_id
        ):
            raise forbidden("Actor cannot propose deletion for this memory scope")

        observation = await cls._resolve_observation(
            actor, request.observation_id, memory_fact.scope_type, memory_fact.scope_id
        )
        safety_result = SafetyService.analyze_memory_payload(
            request.reason or "", None, request.metadata
        )
        proposed_metadata = cls._metadata_with_safety(
            cls._merge_metadata(
                request.metadata, {"reason": request.reason} if request.reason else {}
            ),
            safety_result,
        )
        contains_possible_secret = cls._proposal_contains_possible_secret(
            safety_result, observation
        )

        proposal = await MemoryProposal.create(
            org_id=actor.org_id,
            fact_id=memory_fact.id,
            observation_id=observation.id if observation else None,
            repository_id=cls._foreign_key_id(memory_fact, "repository"),
            scope_type=memory_fact.scope_type,
            scope_id=memory_fact.scope_id,
            proposal_type=ProposalType.DELETE,
            status=ProposalStatus.PENDING,
            proposed_content=None,
            proposed_summary=request.reason,
            proposed_metadata=proposed_metadata,
            content_hash=memory_fact.content_hash,
            contains_possible_secret=contains_possible_secret,
            source=request.source,
            idempotency_key=request.idempotency_key,
            created_by_id=actor.actor_user_id,
            metadata=cls._proposal_metadata(
                actor=actor,
                metadata=proposed_metadata,
                tags=[],
                observation=observation,
                safety_result=safety_result,
                extra_metadata={
                    "target_fact_id": str(memory_fact.id),
                    "current_content_hash": memory_fact.content_hash,
                    "reason": request.reason,
                },
            ),
        )
        response = cls._memory_proposal_response(proposal)
        await AuditService.log_proposal_create(actor, response)
        return response

    @classmethod
    async def archive_user_memory(
        cls,
        actor: ActorContext,
        memory_fact_id: UUID,
        request: MemoryStatusChangeRequest | None = None,
    ) -> MemoryFactResponse:
        """Archive a user-scoped memory directly and write a version row."""
        return await cls._set_direct_user_memory_status(
            actor=actor,
            memory_fact_id=memory_fact_id,
            target_status=MemoryStatus.ARCHIVED,
            action="archive",
            request=request or MemoryStatusChangeRequest(),
        )

    @classmethod
    async def delete_user_memory(
        cls,
        actor: ActorContext,
        memory_fact_id: UUID,
        request: MemoryStatusChangeRequest | None = None,
    ) -> MemoryFactResponse:
        """Soft-delete a user-scoped memory directly and write a version row."""
        return await cls._set_direct_user_memory_status(
            actor=actor,
            memory_fact_id=memory_fact_id,
            target_status=MemoryStatus.DELETED,
            action="delete",
            request=request or MemoryStatusChangeRequest(),
        )

    @classmethod
    async def approve_proposal(
        cls,
        actor: ActorContext,
        proposal_id: UUID,
        request: ProposalReviewRequest,
    ) -> ProposalReviewResult:
        """Approve and apply a pending proposal in an idempotent way."""
        async with in_transaction() as connection:
            proposal = await cls._get_locked_proposal(actor, proposal_id, connection)
            if not RbacService.can_approve_memory(actor, proposal):
                raise forbidden("Actor cannot approve this memory proposal")
            if proposal.status == ProposalStatus.APPLIED:
                result = ProposalReviewResult(
                    proposal_id=proposal.id,
                    memory_fact_id=cls._foreign_key_id(proposal, "fact"),
                    status=proposal.status.value,
                    applied=True,
                )
                await AuditService.log_proposal_review(
                    actor,
                    proposal_id=result.proposal_id,
                    memory_fact_id=result.memory_fact_id,
                    action="proposal_approve",
                    status=result.status,
                    applied=result.applied,
                    metadata={"idempotent_replay": True},
                )
                return result
            cls._ensure_proposal_can_be_applied(proposal)

            memory_fact = await cls._apply_proposal(
                actor, proposal, request, connection
            )
            await cls._mark_proposal_applied(actor, proposal, request, connection)

        result = ProposalReviewResult(
            proposal_id=proposal.id,
            memory_fact_id=memory_fact.id,
            status=proposal.status.value,
            applied=True,
        )
        await AuditService.log_proposal_review(
            actor,
            proposal_id=result.proposal_id,
            memory_fact_id=result.memory_fact_id,
            action="proposal_approve",
            status=result.status,
            applied=result.applied,
            metadata={"proposal_type": proposal.proposal_type},
        )
        if proposal.proposal_type == ProposalType.DELETE:
            await AuditService.log_memory_delete(
                actor,
                memory_fact.id,
                repository_id=cls._foreign_key_id(memory_fact, "repository"),
                metadata={"proposal_id": proposal.id, "via_proposal": True},
            )
        return result

    @classmethod
    async def apply_edited_proposal(
        cls,
        actor: ActorContext,
        proposal_id: UUID,
        request: ProposalApplyEditedRequest,
    ) -> ProposalReviewResult:
        """Approve a create/update proposal with reviewer-edited content."""
        async with in_transaction() as connection:
            proposal = await cls._get_locked_proposal(actor, proposal_id, connection)
            if not RbacService.can_approve_memory(actor, proposal):
                raise forbidden("Actor cannot apply this memory proposal")
            if proposal.status == ProposalStatus.APPLIED:
                result = ProposalReviewResult(
                    proposal_id=proposal.id,
                    memory_fact_id=cls._foreign_key_id(proposal, "fact"),
                    status=proposal.status.value,
                    applied=True,
                )
                await AuditService.log_proposal_review(
                    actor,
                    proposal_id=result.proposal_id,
                    memory_fact_id=result.memory_fact_id,
                    action="proposal_apply_edited",
                    status=result.status,
                    applied=result.applied,
                    metadata={"idempotent_replay": True},
                )
                return result
            cls._ensure_proposal_can_be_applied(proposal)
            if proposal.proposal_type not in {ProposalType.CREATE, ProposalType.UPDATE}:
                raise bad_request(
                    "Edited approval is only supported for create and update proposals"
                )

            safety_result = SafetyService.analyze_memory_payload(
                request.edited_content,
                request.edited_summary,
                request.edited_metadata,
            )
            cls._ensure_safe_for_approved_memory(safety_result)

            memory_fact = await cls._apply_edited_proposal(
                actor, proposal, request, safety_result, connection
            )
            proposal.content_hash = memory_fact.content_hash
            proposal.proposed_content = request.edited_content
            cls._set_tortoise_field(
                proposal, "proposed_summary", request.edited_summary
            )
            proposal.proposed_metadata = cls._metadata_with_safety(
                request.edited_metadata, safety_result
            )
            proposal.metadata = cls._merge_metadata(
                proposal.metadata,
                {
                    "edited_approval": True,
                    "edited_by_user_id": str(actor.actor_user_id),
                    "safety": safety_result.to_metadata(),
                },
            )
            await cls._mark_proposal_applied(actor, proposal, request, connection)

        result = ProposalReviewResult(
            proposal_id=proposal.id,
            memory_fact_id=memory_fact.id,
            status=proposal.status.value,
            applied=True,
        )
        await AuditService.log_proposal_review(
            actor,
            proposal_id=result.proposal_id,
            memory_fact_id=result.memory_fact_id,
            action="proposal_apply_edited",
            status=result.status,
            applied=result.applied,
            metadata={"proposal_type": proposal.proposal_type, "edited_approval": True},
        )
        return result

    @classmethod
    async def reject_proposal(
        cls,
        actor: ActorContext,
        proposal_id: UUID,
        request: ProposalReviewRequest,
    ) -> ProposalReviewResult:
        """Reject a pending proposal without creating or mutating a memory fact."""
        proposal = await MemoryProposal.get_or_none(id=proposal_id, org_id=actor.org_id)
        if not proposal:
            raise not_found("Memory proposal not found")
        if not RbacService.can_approve_memory(actor, proposal):
            raise forbidden("Actor cannot reject this memory proposal")
        if proposal.status == ProposalStatus.REJECTED:
            result = ProposalReviewResult(
                proposal_id=proposal.id,
                memory_fact_id=cls._foreign_key_id(proposal, "fact"),
                status=proposal.status.value,
                applied=False,
            )
            await AuditService.log_proposal_review(
                actor,
                proposal_id=result.proposal_id,
                memory_fact_id=result.memory_fact_id,
                action="proposal_reject",
                status=result.status,
                applied=result.applied,
                metadata={"idempotent_replay": True},
            )
            return result
        if proposal.status in {ProposalStatus.APPLIED, ProposalStatus.CANCELLED}:
            raise conflict("Proposal cannot be rejected from its current status")

        proposal.status = ProposalStatus.REJECTED
        proposal.reviewed_by_id = actor.actor_user_id
        proposal.reviewed_at = cls._utcnow()
        cls._set_tortoise_field(proposal, "review_notes", request.review_notes)
        proposal.metadata = cls._merge_metadata(
            proposal.metadata, {"review": request.metadata}
        )
        await proposal.save()

        result = ProposalReviewResult(
            proposal_id=proposal.id,
            memory_fact_id=cls._foreign_key_id(proposal, "fact"),
            status=proposal.status.value,
            applied=False,
        )
        await AuditService.log_proposal_review(
            actor,
            proposal_id=result.proposal_id,
            memory_fact_id=result.memory_fact_id,
            action="proposal_reject",
            status=result.status,
            applied=result.applied,
            metadata={"proposal_type": proposal.proposal_type},
        )
        return result

    @classmethod
    async def _apply_proposal(
        cls,
        actor: ActorContext,
        proposal: MemoryProposal,
        request: ProposalReviewRequest,
        connection,
    ) -> MemoryFact:
        if proposal.proposal_type == ProposalType.CREATE:
            return await cls._apply_create_proposal(
                actor, proposal, request, connection
            )
        if proposal.proposal_type == ProposalType.UPDATE:
            return await cls._apply_update_proposal(
                actor, proposal, request, connection
            )
        if proposal.proposal_type == ProposalType.DELETE:
            return await cls._apply_delete_proposal(
                actor, proposal, request, connection
            )
        raise bad_request("Unsupported proposal type for approval")

    @classmethod
    async def _apply_create_proposal(
        cls,
        actor: ActorContext,
        proposal: MemoryProposal,
        request: ProposalReviewRequest,
        connection,
    ) -> MemoryFact:
        cls._ensure_create_proposal(proposal)
        safety_result = SafetyService.analyze_memory_payload(
            proposal.proposed_content or "",
            proposal.proposed_summary,
            proposal.proposed_metadata,
        )
        cls._ensure_safe_for_approved_memory(safety_result)

        metadata = cls._metadata_with_safety(
            proposal.proposed_metadata or {}, safety_result
        )
        memory_fact = await MemoryFact.create(
            org_id=cls._required_foreign_key_id(proposal, "org"),
            owner_user_id=proposal.scope_id
            if proposal.scope_type == ScopeType.USER
            else None,
            repository_id=cls._foreign_key_id(proposal, "repository"),
            scope_type=proposal.scope_type,
            scope_id=proposal.scope_id,
            status=MemoryStatus.APPROVED,
            content=proposal.proposed_content or "",
            summary=proposal.proposed_summary,
            content_hash=proposal.content_hash
            or cls.generate_content_hash(
                proposal.proposed_content or "", proposal.proposed_summary
            ),
            source=proposal.source,
            metadata=metadata,
            created_by_id=cls._foreign_key_id(proposal, "created_by"),
            updated_by_id=actor.actor_user_id,
            approved_by_id=actor.actor_user_id,
            approved_at=cls._utcnow(),
            using_db=connection,
        )
        await cls._sync_fact_tags(
            actor=actor,
            memory_fact=memory_fact,
            tags=cls._tags_from_metadata(metadata),
            using_db=connection,
        )
        await cls._create_fact_version(
            memory_fact=memory_fact,
            proposal=proposal,
            changed_by_id=actor.actor_user_id,
            change_reason=request.review_notes or "proposal_approved",
            metadata={
                "action": "approve_create",
                "safety": safety_result.to_metadata(),
                **request.metadata,
            },
            using_db=connection,
        )
        cls._set_tortoise_field(proposal, "fact_id", memory_fact.id)
        return memory_fact

    @classmethod
    async def _apply_update_proposal(
        cls,
        actor: ActorContext,
        proposal: MemoryProposal,
        request: ProposalReviewRequest,
        connection,
    ) -> MemoryFact:
        cls._ensure_update_proposal(proposal)
        safety_result = SafetyService.analyze_memory_payload(
            proposal.proposed_content or "",
            proposal.proposed_summary,
            proposal.proposed_metadata,
        )
        cls._ensure_safe_for_approved_memory(safety_result)

        memory_fact = await cls._get_locked_fact_for_proposal(proposal, connection)
        cls._ensure_fact_can_be_mutated(memory_fact, "updated")
        memory_fact.content = proposal.proposed_content or ""
        cls._set_tortoise_field(memory_fact, "summary", proposal.proposed_summary)
        memory_fact.content_hash = proposal.content_hash or cls.generate_content_hash(
            memory_fact.content, memory_fact.summary
        )
        memory_fact.metadata = cls._metadata_with_safety(
            cls._merge_metadata(memory_fact.metadata, proposal.proposed_metadata or {}),
            safety_result,
        )
        await cls._sync_fact_tags(
            actor=actor,
            memory_fact=memory_fact,
            tags=cls._tags_from_metadata(memory_fact.metadata),
            using_db=connection,
            replace_existing=True,
        )
        memory_fact.updated_by_id = actor.actor_user_id
        memory_fact.approved_by_id = actor.actor_user_id
        memory_fact.approved_at = cls._utcnow()
        await memory_fact.save(using_db=connection)
        await cls._create_fact_version(
            memory_fact=memory_fact,
            proposal=proposal,
            changed_by_id=actor.actor_user_id,
            change_reason=request.review_notes or "proposal_update_approved",
            metadata={
                "action": "approve_update",
                "safety": safety_result.to_metadata(),
                **request.metadata,
            },
            using_db=connection,
        )
        return memory_fact

    @classmethod
    async def _apply_delete_proposal(
        cls,
        actor: ActorContext,
        proposal: MemoryProposal,
        request: ProposalReviewRequest,
        connection,
    ) -> MemoryFact:
        cls._ensure_delete_proposal(proposal)
        memory_fact = await cls._get_locked_fact_for_proposal(proposal, connection)
        cls._ensure_fact_can_be_deleted(memory_fact)
        memory_fact.status = MemoryStatus.DELETED
        memory_fact.updated_by_id = actor.actor_user_id
        memory_fact.metadata = cls._merge_metadata(
            memory_fact.metadata,
            {
                "lifecycle": {
                    "action": "delete",
                    "reason": request.review_notes or proposal.proposed_summary,
                    "proposal_id": str(proposal.id),
                    "changed_by_user_id": str(actor.actor_user_id),
                    "changed_at": cls._utcnow().isoformat(),
                }
            },
        )
        await memory_fact.save(using_db=connection)
        await cls._create_fact_version(
            memory_fact=memory_fact,
            proposal=proposal,
            changed_by_id=actor.actor_user_id,
            change_reason=request.review_notes
            or proposal.proposed_summary
            or "proposal_delete_approved",
            metadata={"action": "approve_delete", **request.metadata},
            using_db=connection,
        )
        return memory_fact

    @classmethod
    async def _apply_edited_proposal(
        cls,
        actor: ActorContext,
        proposal: MemoryProposal,
        request: ProposalApplyEditedRequest,
        safety_result: SafetyCheckResult,
        connection,
    ) -> MemoryFact:
        if proposal.proposal_type == ProposalType.CREATE:
            metadata = cls._metadata_with_safety(request.edited_metadata, safety_result)
            memory_fact = await MemoryFact.create(
                org_id=cls._required_foreign_key_id(proposal, "org"),
                owner_user_id=proposal.scope_id
                if proposal.scope_type == ScopeType.USER
                else None,
                repository_id=cls._foreign_key_id(proposal, "repository"),
                scope_type=proposal.scope_type,
                scope_id=proposal.scope_id,
                status=MemoryStatus.APPROVED,
                content=request.edited_content,
                summary=request.edited_summary,
                content_hash=cls.generate_content_hash(
                    request.edited_content, request.edited_summary
                ),
                source=proposal.source,
                metadata=metadata,
                created_by_id=cls._foreign_key_id(proposal, "created_by"),
                updated_by_id=actor.actor_user_id,
                approved_by_id=actor.actor_user_id,
                approved_at=cls._utcnow(),
                using_db=connection,
            )
            await cls._sync_fact_tags(
                actor=actor,
                memory_fact=memory_fact,
                tags=cls._tags_from_metadata(metadata),
                using_db=connection,
            )
            await cls._create_fact_version(
                memory_fact=memory_fact,
                proposal=proposal,
                changed_by_id=actor.actor_user_id,
                change_reason=request.review_notes or "proposal_edited_create_approved",
                metadata={
                    "action": "approve_edited_create",
                    "safety": safety_result.to_metadata(),
                    **request.metadata,
                },
                using_db=connection,
            )
            cls._set_tortoise_field(proposal, "fact_id", memory_fact.id)
            return memory_fact

        cls._ensure_update_proposal(proposal)
        memory_fact = await cls._get_locked_fact_for_proposal(proposal, connection)
        cls._ensure_fact_can_be_mutated(memory_fact, "updated")
        memory_fact.content = request.edited_content
        cls._set_tortoise_field(memory_fact, "summary", request.edited_summary)
        memory_fact.content_hash = cls.generate_content_hash(
            request.edited_content, request.edited_summary
        )
        memory_fact.metadata = cls._metadata_with_safety(
            cls._merge_metadata(memory_fact.metadata, request.edited_metadata),
            safety_result,
        )
        await cls._sync_fact_tags(
            actor=actor,
            memory_fact=memory_fact,
            tags=cls._tags_from_metadata(memory_fact.metadata),
            using_db=connection,
            replace_existing=True,
        )
        memory_fact.updated_by_id = actor.actor_user_id
        memory_fact.approved_by_id = actor.actor_user_id
        memory_fact.approved_at = cls._utcnow()
        await memory_fact.save(using_db=connection)
        await cls._create_fact_version(
            memory_fact=memory_fact,
            proposal=proposal,
            changed_by_id=actor.actor_user_id,
            change_reason=request.review_notes or "proposal_edited_update_approved",
            metadata={
                "action": "approve_edited_update",
                "safety": safety_result.to_metadata(),
                **request.metadata,
            },
            using_db=connection,
        )
        return memory_fact

    @classmethod
    async def _set_direct_user_memory_status(
        cls,
        actor: ActorContext,
        memory_fact_id: UUID,
        target_status: MemoryStatus,
        action: str,
        request: MemoryStatusChangeRequest,
    ) -> MemoryFactResponse:
        async with in_transaction() as connection:
            memory_fact = await (
                MemoryFact.filter(id=memory_fact_id, org_id=actor.org_id)
                .select_for_update()
                .using_db(connection)
                .first()
            )
            if not memory_fact:
                raise not_found("Memory fact not found")
            if memory_fact.scope_type != ScopeType.USER:
                raise bad_request(
                    "Direct archive/delete is only available for user-scoped memories"
                )
            if not RbacService.can_delete_memory(actor, memory_fact):
                raise forbidden("Actor cannot archive/delete this memory")
            if memory_fact.status == target_status:
                response = cls._memory_fact_response(memory_fact)
                await AuditService.log_memory_delete(
                    actor,
                    response.id,
                    action=f"memory_{action}",
                    repository_id=response.repository_id,
                    metadata={"status": response.status, "idempotent_replay": True},
                )
                return response
            cls._ensure_direct_status_transition(memory_fact, target_status)

            memory_fact.status = target_status
            memory_fact.updated_by_id = actor.actor_user_id
            memory_fact.metadata = cls._merge_metadata(
                memory_fact.metadata,
                {
                    "lifecycle": {
                        "action": action,
                        "reason": request.reason,
                        "changed_by_user_id": str(actor.actor_user_id),
                        "changed_at": cls._utcnow().isoformat(),
                    },
                    **request.metadata,
                },
            )
            await memory_fact.save(using_db=connection)
            await cls._create_fact_version(
                memory_fact=memory_fact,
                proposal=None,
                changed_by_id=actor.actor_user_id,
                change_reason=request.reason or f"direct_user_{action}",
                metadata={"action": action, **request.metadata},
                using_db=connection,
            )

        response = cls._memory_fact_response(memory_fact)
        await AuditService.log_memory_delete(
            actor,
            response.id,
            action=f"memory_{action}",
            repository_id=response.repository_id,
            metadata={"status": response.status, "reason": request.reason},
        )
        return response

    @classmethod
    async def _create_fact_version(
        cls,
        memory_fact: MemoryFact,
        proposal: MemoryProposal | None,
        changed_by_id: UUID,
        change_reason: str,
        metadata: dict,
        using_db,
    ) -> MemoryFactVersion:
        latest_version = await (
            MemoryFactVersion.filter(fact_id=memory_fact.id)
            .order_by("-version_number")
            .using_db(using_db)
            .first()
        )
        version_number = (latest_version.version_number + 1) if latest_version else 1
        return await MemoryFactVersion.create(
            fact_id=memory_fact.id,
            proposal_id=proposal.id if proposal else None,
            version_number=version_number,
            status=memory_fact.status,
            content=memory_fact.content,
            summary=memory_fact.summary,
            content_hash=memory_fact.content_hash,
            change_reason=change_reason,
            changed_by_id=changed_by_id,
            metadata=metadata,
            using_db=using_db,
        )

    @classmethod
    async def _ensure_tag_records(cls, actor: ActorContext, tags: list[str]) -> None:
        """Create managed tag rows for free-text memory/proposal tags."""
        for tag_label in cls._normalize_tags(tags):
            tag_slug = TagService._normalize_slug(tag_label)
            await Tag.get_or_create(
                org_id=actor.org_id,
                slug=tag_slug,
                defaults={
                    "label": tag_label,
                    "metadata": {
                        "source": "memory_request",
                        "created_by_user_id": str(actor.actor_user_id),
                    },
                },
            )

    @classmethod
    async def _sync_fact_tags(
        cls,
        actor: ActorContext,
        memory_fact: MemoryFact,
        tags: list[str],
        using_db,
        replace_existing: bool = False,
    ) -> None:
        """Materialize request/proposal tags into tag rows and fact-tag mappings."""
        normalized_tags = cls._normalize_tags(tags)
        if replace_existing:
            await (
                MemoryFactTag.filter(org_id=actor.org_id, fact_id=memory_fact.id)
                .using_db(using_db)
                .delete()
            )
        if not normalized_tags:
            return

        for tag_label in normalized_tags:
            tag_slug = TagService._normalize_slug(tag_label)
            tag, _ = await Tag.get_or_create(
                org_id=actor.org_id,
                slug=tag_slug,
                defaults={
                    "label": tag_label,
                    "metadata": {
                        "source": "memory_request",
                        "created_by_user_id": str(actor.actor_user_id),
                    },
                },
                using_db=using_db,
            )
            await MemoryFactTag.get_or_create(
                org_id=actor.org_id,
                fact_id=memory_fact.id,
                tag_id=tag.id,
                defaults={
                    "metadata": {"assigned_by_user_id": str(actor.actor_user_id)}
                },
                using_db=using_db,
            )

    @classmethod
    def generate_content_hash(cls, content: str, summary: str | None = None) -> str:
        """Generate a stable hash for memory content stored in facts/proposals."""
        canonical_payload = json.dumps(
            {
                "content": cls._normalize_hash_text(content),
                "summary": cls._normalize_hash_text(summary or ""),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        digest = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    @classmethod
    async def _get_locked_proposal(
        cls, actor: ActorContext, proposal_id: UUID, connection
    ) -> MemoryProposal:
        proposal = await (
            MemoryProposal.filter(id=proposal_id, org_id=actor.org_id)
            .select_for_update()
            .using_db(connection)
            .first()
        )
        if not proposal:
            raise not_found("Memory proposal not found")
        return proposal

    @classmethod
    async def _get_locked_fact_for_proposal(
        cls, proposal: MemoryProposal, connection
    ) -> MemoryFact:
        fact_id = cls._foreign_key_id(proposal, "fact")
        if not fact_id:
            raise bad_request("Proposal is not linked to a memory fact")
        memory_fact = await (
            MemoryFact.filter(
                id=fact_id, org_id=cls._required_foreign_key_id(proposal, "org")
            )
            .select_for_update()
            .using_db(connection)
            .first()
        )
        if not memory_fact:
            raise not_found("Linked memory fact not found")
        return memory_fact

    @classmethod
    async def _get_readable_memory_fact(
        cls, actor: ActorContext, memory_fact_id: UUID
    ) -> MemoryFact:
        memory_fact = await MemoryFact.get_or_none(
            id=memory_fact_id, org_id=actor.org_id
        )
        if not memory_fact:
            raise not_found("Memory fact not found")
        if not RbacService.can_read_memory(actor, memory_fact):
            raise forbidden("Actor cannot read this memory")
        return memory_fact

    @classmethod
    def _requires_create_review(cls, scope_type: ScopeType) -> bool:
        settings = EngramConfigService.engram()
        if scope_type == ScopeType.REPO:
            return settings.require_review_for_repo_memory
        if scope_type == ScopeType.ORG:
            return settings.require_review_for_org_memory
        return False

    @classmethod
    def _ensure_user_scope(cls, scope_type: ScopeType) -> None:
        if scope_type != ScopeType.USER:
            raise bad_request("Direct memory creation is only available for user scope")

    @classmethod
    def _ensure_scope_can_be_created(
        cls, actor: ActorContext, scope_type: ScopeType, scope_id: UUID
    ) -> None:
        if RbacService.can_create_memory(actor, scope_type, scope_id):
            return
        if not cls._requires_create_review(
            scope_type
        ) and RbacService.can_propose_memory(actor, scope_type, scope_id):
            return
        raise forbidden("Actor cannot create memory for this scope")

    @classmethod
    async def _resolve_user_scope(cls, actor: ActorContext, user_id: UUID) -> User:
        user = await User.get_or_none(id=user_id, is_active=True)
        if not user:
            raise bad_request("User scope is invalid")
        if user.id != actor.actor_user_id and not RbacService.is_admin(actor):
            raise forbidden("Actor cannot create memory for this user")
        return user

    @classmethod
    async def _get_existing_idempotent_proposal(
        cls,
        actor: ActorContext,
        idempotency_key: str | None,
    ) -> MemoryProposal | None:
        if not idempotency_key:
            return None

        existing_proposal = await MemoryProposal.get_or_none(
            idempotency_key=idempotency_key
        )
        if not existing_proposal:
            return None
        if (
            cls._required_foreign_key_id(existing_proposal, "org") != actor.org_id
            or cls._foreign_key_id(existing_proposal, "created_by")
            != actor.actor_user_id
        ):
            raise conflict("Idempotency key is already used by another proposal")
        return existing_proposal

    @classmethod
    def _ensure_valid_proposal_scope(
        cls, actor: ActorContext, scope_type: ScopeType, scope_id: UUID
    ) -> None:
        cls._ensure_valid_memory_scope(actor, scope_type, scope_id)

    @classmethod
    def _ensure_valid_memory_scope(
        cls, actor: ActorContext, scope_type: ScopeType, scope_id: UUID
    ) -> None:
        if scope_type == ScopeType.ORG and scope_id != actor.org_id:
            raise bad_request("Organization scope must match the actor organization")

    @classmethod
    async def _resolve_repository_for_scope(
        cls,
        org_id: UUID,
        scope_type: ScopeType,
        scope_id: UUID,
    ) -> Repository | None:
        if scope_type != ScopeType.REPO:
            return None
        repository = await Repository.get_or_none(
            id=scope_id, org_id=org_id, is_active=True
        )
        if not repository:
            raise bad_request("Repository scope is invalid for this organization")
        return repository

    @classmethod
    async def _resolve_observation(
        cls,
        actor: ActorContext,
        observation_id: UUID | None,
        scope_type: ScopeType,
        scope_id: UUID,
    ) -> MemoryObservation | None:
        if not observation_id:
            return None
        observation = await MemoryObservation.get_or_none(
            id=observation_id, org_id=actor.org_id
        )
        if not observation:
            raise bad_request("Observation does not exist")
        if observation.scope_type != scope_type or observation.scope_id != scope_id:
            raise bad_request("Observation scope does not match proposal scope")
        return observation

    @classmethod
    def _ensure_proposal_can_be_applied(cls, proposal: MemoryProposal) -> None:
        if proposal.status in {ProposalStatus.REJECTED, ProposalStatus.CANCELLED}:
            raise conflict("Rejected or cancelled proposals cannot be applied")
        if proposal.status != ProposalStatus.PENDING:
            raise conflict("Proposal cannot be applied from its current status")

    @classmethod
    async def _mark_proposal_applied(
        cls,
        actor: ActorContext,
        proposal: MemoryProposal,
        request: ProposalReviewRequest,
        connection,
    ) -> None:
        now = cls._utcnow()
        proposal.status = ProposalStatus.APPLIED
        proposal.reviewed_by_id = actor.actor_user_id
        proposal.reviewed_at = now
        proposal.applied_at = now
        cls._set_tortoise_field(proposal, "review_notes", request.review_notes)
        proposal.metadata = cls._merge_metadata(
            proposal.metadata, {"review": request.metadata}
        )
        await proposal.save(using_db=connection)

    @classmethod
    def _ensure_create_proposal(cls, proposal: MemoryProposal) -> None:
        if proposal.proposal_type != ProposalType.CREATE:
            raise bad_request("Proposal is not a create proposal")
        if not proposal.proposed_content:
            raise bad_request("Create proposal must include proposed content")

    @classmethod
    def _ensure_update_proposal(cls, proposal: MemoryProposal) -> None:
        if proposal.proposal_type != ProposalType.UPDATE:
            raise bad_request("Proposal is not an update proposal")
        if not cls._foreign_key_id(proposal, "fact") or not proposal.proposed_content:
            raise bad_request(
                "Update proposal must include a target fact and proposed content"
            )

    @classmethod
    def _ensure_delete_proposal(cls, proposal: MemoryProposal) -> None:
        if proposal.proposal_type != ProposalType.DELETE:
            raise bad_request("Proposal is not a delete proposal")
        if not cls._foreign_key_id(proposal, "fact"):
            raise bad_request("Delete proposal must include a target fact")

    @classmethod
    def _ensure_fact_can_receive_update_proposal(cls, memory_fact: MemoryFact) -> None:
        if memory_fact.status != MemoryStatus.APPROVED:
            raise conflict("Only approved memories can receive update proposals")

    @classmethod
    def _ensure_fact_can_receive_delete_proposal(cls, memory_fact: MemoryFact) -> None:
        if memory_fact.status != MemoryStatus.APPROVED:
            raise conflict("Only approved memories can receive deletion proposals")

    @classmethod
    def _ensure_fact_can_be_mutated(cls, memory_fact: MemoryFact, action: str) -> None:
        if memory_fact.status != MemoryStatus.APPROVED:
            raise conflict(f"Only approved memories can be {action}")

    @classmethod
    def _ensure_fact_can_be_deleted(cls, memory_fact: MemoryFact) -> None:
        if memory_fact.status != MemoryStatus.APPROVED:
            raise conflict(
                "Only approved memories can be deleted through proposal approval"
            )

    @classmethod
    def _ensure_direct_status_transition(
        cls, memory_fact: MemoryFact, target_status: MemoryStatus
    ) -> None:
        if (
            target_status == MemoryStatus.ARCHIVED
            and memory_fact.status != MemoryStatus.APPROVED
        ):
            raise conflict("Only approved memories can be archived")
        if target_status == MemoryStatus.DELETED and memory_fact.status not in {
            MemoryStatus.APPROVED,
            MemoryStatus.ARCHIVED,
        }:
            raise conflict("Only approved or archived memories can be deleted")

    @classmethod
    def _ensure_safe_for_auto_approval(cls, safety_result: SafetyCheckResult) -> None:
        if safety_result.contains_possible_secret:
            raise bad_request(
                "Memory content appears to contain a possible secret and cannot be auto-approved"
            )

    @classmethod
    def _ensure_safe_for_approved_memory(cls, safety_result: SafetyCheckResult) -> None:
        if safety_result.contains_possible_secret:
            raise conflict(
                "Proposal content appears to contain a possible secret; apply an edited safe version or reject it"
            )

    @classmethod
    def _proposal_contains_possible_secret(
        cls,
        safety_result: SafetyCheckResult,
        observation: MemoryObservation | None,
    ) -> bool:
        return safety_result.contains_possible_secret or bool(
            observation and observation.contains_possible_secret
        )

    @classmethod
    def _metadata_with_tags(cls, metadata: dict, tags: list[str]) -> dict:
        merged_metadata = dict(metadata or {})
        if tags:
            merged_metadata["tags"] = cls._normalize_tags(tags)
        return merged_metadata

    @classmethod
    def _metadata_with_safety(
        cls, metadata: dict, safety_result: SafetyCheckResult
    ) -> dict:
        merged_metadata = dict(metadata or {})
        merged_metadata["contains_possible_secret"] = (
            safety_result.contains_possible_secret
        )
        merged_metadata["safety"] = safety_result.to_metadata()
        return merged_metadata

    @classmethod
    def _proposal_metadata(
        cls,
        actor: ActorContext,
        metadata: dict,
        tags: list[str],
        observation: MemoryObservation | None,
        safety_result: SafetyCheckResult | None = None,
        extra_metadata: dict | None = None,
    ) -> dict:
        proposal_metadata = cls._metadata_with_tags(metadata, tags)
        proposal_metadata["created_by_client"] = actor.client_name
        if actor.request_id:
            proposal_metadata["request_id"] = actor.request_id
        if observation:
            proposal_metadata["observation_id"] = str(observation.id)
            proposal_metadata["observation_contains_possible_secret"] = (
                observation.contains_possible_secret
            )
        if safety_result:
            proposal_metadata = cls._metadata_with_safety(
                proposal_metadata, safety_result
            )
        if extra_metadata:
            proposal_metadata = cls._merge_metadata(proposal_metadata, extra_metadata)
        return proposal_metadata

    @classmethod
    def _foreign_key_id(cls, model: object, relation_name: str) -> UUID | None:
        """Read Tortoise's dynamic `<relation>_id` attribute without confusing static analysis."""
        value = getattr(model, f"{relation_name}_id", None)
        return value if isinstance(value, UUID) else None

    @classmethod
    def _required_foreign_key_id(cls, model: object, relation_name: str) -> UUID:
        value = cls._foreign_key_id(model, relation_name)
        if value is None:
            raise bad_request(f"{relation_name} context is unavailable")
        return value

    @classmethod
    def _set_tortoise_field(cls, model: object, field_name: str, value: object) -> None:
        """Set Tortoise fields whose runtime nullability is not visible to Pyrefly."""
        setattr(model, field_name, value)

    @classmethod
    def _memory_fact_response(cls, memory_fact: MemoryFact) -> MemoryFactResponse:
        return MemoryFactResponse(
            id=memory_fact.id,
            org_id=cls._required_foreign_key_id(memory_fact, "org"),
            repository_id=cls._foreign_key_id(memory_fact, "repository"),
            owner_user_id=cls._foreign_key_id(memory_fact, "owner_user"),
            scope_type=memory_fact.scope_type,
            scope_id=memory_fact.scope_id,
            status=memory_fact.status,
            content=memory_fact.content,
            summary=memory_fact.summary,
            tags=cls._tags_from_metadata(memory_fact.metadata),
            source=memory_fact.source,
            metadata=memory_fact.metadata or {},
            created_at=memory_fact.created_at,
            updated_at=memory_fact.updated_at,
        )

    @classmethod
    def _memory_proposal_response(
        cls, proposal: MemoryProposal
    ) -> MemoryProposalResponse:
        return MemoryProposalResponse(
            id=proposal.id,
            org_id=cls._required_foreign_key_id(proposal, "org"),
            fact_id=cls._foreign_key_id(proposal, "fact"),
            observation_id=cls._foreign_key_id(proposal, "observation"),
            repository_id=cls._foreign_key_id(proposal, "repository"),
            scope_type=proposal.scope_type,
            scope_id=proposal.scope_id,
            proposal_type=proposal.proposal_type,
            status=proposal.status,
            proposed_content=proposal.proposed_content,
            proposed_summary=proposal.proposed_summary,
            contains_possible_secret=proposal.contains_possible_secret,
            metadata=proposal.metadata or {},
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
        )

    @classmethod
    def _tags_from_metadata(cls, metadata: dict | None) -> list[str]:
        tags = (metadata or {}).get("tags", [])
        if not isinstance(tags, list):
            return []
        return cls._normalize_tags(tags)

    @classmethod
    def _normalize_tags(cls, tags: list[str]) -> list[str]:
        normalized_tags = []
        seen_tags = set()
        for tag in tags:
            normalized_tag = tag.strip().lower()
            if normalized_tag and normalized_tag not in seen_tags:
                seen_tags.add(normalized_tag)
                normalized_tags.append(normalized_tag)
        return normalized_tags

    @classmethod
    def _merge_metadata(cls, current_metadata: dict | None, patch: dict) -> dict:
        merged_metadata = dict(current_metadata or {})
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(merged_metadata.get(key), dict):
                merged_metadata[key] = {**merged_metadata[key], **value}
            else:
                merged_metadata[key] = value
        return merged_metadata

    @classmethod
    def _normalize_hash_text(cls, value: str) -> str:
        return "\n".join(line.rstrip() for line in value.strip().splitlines())

    @classmethod
    def _utcnow(cls) -> datetime:
        return datetime.now(UTC)
