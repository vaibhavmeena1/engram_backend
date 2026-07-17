"""Memory fact, observation, version, and tag models."""

from tortoise import fields

from app.models.base import EngramModel
from app.schemas.enums import MemorySource, MemoryStatus, ScopeType


class MemoryFact(EngramModel):
    org = fields.ForeignKeyField(
        "dao.Organization", related_name="memory_facts", on_delete=fields.CASCADE
    )
    owner_user = fields.ForeignKeyField(
        "dao.User",
        related_name="owned_memory_facts",
        null=True,
        on_delete=fields.SET_NULL,
    )
    repository = fields.ForeignKeyField(
        "dao.Repository",
        related_name="memory_facts",
        null=True,
        on_delete=fields.SET_NULL,
    )
    scope_type = fields.CharEnumField(ScopeType, max_length=16)
    scope_id = fields.UUIDField()
    status = fields.CharEnumField(
        MemoryStatus, max_length=32, default=MemoryStatus.PENDING_REVIEW
    )
    content = fields.TextField()
    rationale = fields.TextField(null=True)
    summary = fields.TextField(null=True)
    content_hash = fields.CharField(max_length=128, index=True)
    source = fields.CharEnumField(
        MemorySource, max_length=32, default=MemorySource.SYSTEM
    )
    source_ref = fields.CharField(max_length=255, null=True)
    metadata = fields.JSONField(default=dict)
    created_by = fields.ForeignKeyField(
        "dao.User",
        related_name="created_memory_facts",
        null=True,
        on_delete=fields.SET_NULL,
    )
    updated_by = fields.ForeignKeyField(
        "dao.User",
        related_name="updated_memory_facts",
        null=True,
        on_delete=fields.SET_NULL,
    )
    approved_by = fields.ForeignKeyField(
        "dao.User",
        related_name="approved_memory_facts",
        null=True,
        on_delete=fields.SET_NULL,
    )
    approved_at = fields.DatetimeField(null=True)

    class Meta:
        table = "engram_memory_facts"
        indexes = (("org", "scope_type", "scope_id", "status"),)


class MemoryObservation(EngramModel):
    org = fields.ForeignKeyField(
        "dao.Organization", related_name="memory_observations", on_delete=fields.CASCADE
    )
    actor_user = fields.ForeignKeyField(
        "dao.User",
        related_name="memory_observations",
        null=True,
        on_delete=fields.SET_NULL,
    )
    repository = fields.ForeignKeyField(
        "dao.Repository",
        related_name="memory_observations",
        null=True,
        on_delete=fields.SET_NULL,
    )
    scope_type = fields.CharEnumField(ScopeType, max_length=16)
    scope_id = fields.UUIDField()
    raw_content = fields.TextField()
    source = fields.CharEnumField(MemorySource, max_length=32, default=MemorySource.MCP)
    source_metadata = fields.JSONField(default=dict)
    contains_possible_secret = fields.BooleanField(default=False)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_memory_observations"
        indexes = (("org", "scope_type", "scope_id"),)


class MemoryFactVersion(EngramModel):
    fact = fields.ForeignKeyField(
        "dao.MemoryFact", related_name="versions", on_delete=fields.CASCADE
    )
    proposal = fields.ForeignKeyField(
        "dao.MemoryProposal",
        related_name="created_versions",
        null=True,
        on_delete=fields.SET_NULL,
    )
    version_number = fields.IntField()
    status = fields.CharEnumField(MemoryStatus, max_length=32)
    content = fields.TextField()
    rationale = fields.TextField(null=True)
    summary = fields.TextField(null=True)
    content_hash = fields.CharField(max_length=128)
    change_reason = fields.TextField(null=True)
    changed_by = fields.ForeignKeyField(
        "dao.User",
        related_name="memory_fact_versions",
        null=True,
        on_delete=fields.SET_NULL,
    )
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_memory_fact_versions"
        unique_together = (("fact", "version_number"),)


class Tag(EngramModel):
    org = fields.ForeignKeyField(
        "dao.Organization", related_name="tags", on_delete=fields.CASCADE
    )
    slug = fields.CharField(max_length=120)
    label = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    color = fields.CharField(max_length=32, null=True)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_tags"
        unique_together = (("org", "slug"),)


class MemoryFactTag(EngramModel):
    org = fields.ForeignKeyField(
        "dao.Organization", related_name="memory_fact_tags", on_delete=fields.CASCADE
    )
    fact = fields.ForeignKeyField(
        "dao.MemoryFact", related_name="fact_tags", on_delete=fields.CASCADE
    )
    tag = fields.ForeignKeyField(
        "dao.Tag", related_name="tagged_facts", on_delete=fields.CASCADE
    )
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_memory_fact_tags"
        unique_together = (("fact", "tag"),)
