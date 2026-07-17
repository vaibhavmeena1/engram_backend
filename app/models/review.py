"""Review workflow models for repo/org memory governance."""

from tortoise import fields

from app.models.base import EngramModel
from app.schemas.enums import MemorySource, ProposalStatus, ProposalType, ScopeType


class MemoryProposal(EngramModel):
    org = fields.ForeignKeyField(
        "dao.Organization", related_name="memory_proposals", on_delete=fields.CASCADE
    )
    fact = fields.ForeignKeyField(
        "dao.MemoryFact",
        related_name="proposals",
        null=True,
        on_delete=fields.SET_NULL,
    )
    observation = fields.ForeignKeyField(
        "dao.MemoryObservation",
        related_name="proposals",
        null=True,
        on_delete=fields.SET_NULL,
    )
    repository = fields.ForeignKeyField(
        "dao.Repository",
        related_name="memory_proposals",
        null=True,
        on_delete=fields.SET_NULL,
    )
    scope_type = fields.CharEnumField(ScopeType, max_length=16)
    scope_id = fields.UUIDField()
    proposal_type = fields.CharEnumField(ProposalType, max_length=16)
    status = fields.CharEnumField(
        ProposalStatus, max_length=16, default=ProposalStatus.PENDING
    )
    proposed_content = fields.TextField(null=True)
    proposed_rationale = fields.TextField(null=True)
    proposed_summary = fields.TextField(null=True)
    proposed_metadata = fields.JSONField(default=dict)
    content_hash = fields.CharField(max_length=128, null=True, index=True)
    contains_possible_secret = fields.BooleanField(default=False)
    source = fields.CharEnumField(MemorySource, max_length=32, default=MemorySource.MCP)
    idempotency_key = fields.CharField(max_length=255, null=True, unique=True)
    review_notes = fields.TextField(null=True)
    created_by = fields.ForeignKeyField(
        "dao.User",
        related_name="created_memory_proposals",
        null=True,
        on_delete=fields.SET_NULL,
    )
    reviewed_by = fields.ForeignKeyField(
        "dao.User",
        related_name="reviewed_memory_proposals",
        null=True,
        on_delete=fields.SET_NULL,
    )
    reviewed_at = fields.DatetimeField(null=True)
    applied_at = fields.DatetimeField(null=True)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_memory_proposals"
        indexes = (("org", "scope_type", "scope_id", "status"),)
