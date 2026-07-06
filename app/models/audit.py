"""Audit models for memory access and mutation events."""

from tortoise import fields

from app.models.base import EngramModel


class MemoryAccessLog(EngramModel):
    org = fields.ForeignKeyField(
        "dao.Organization",
        related_name="memory_access_logs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    actor_user = fields.ForeignKeyField(
        "dao.User",
        related_name="memory_access_logs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    repository = fields.ForeignKeyField(
        "dao.Repository",
        related_name="memory_access_logs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    memory_fact = fields.ForeignKeyField(
        "dao.MemoryFact",
        related_name="access_logs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    proposal = fields.ForeignKeyField(
        "dao.MemoryProposal",
        related_name="access_logs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    action = fields.CharField(max_length=64)
    auth_method = fields.CharField(max_length=64, null=True, index=True)
    client_type = fields.CharField(max_length=32, null=True, index=True)
    session_id = fields.UUIDField(null=True, index=True)
    personal_access_token_id = fields.UUIDField(null=True, index=True)
    client_name = fields.CharField(max_length=120, null=True)
    request_id = fields.CharField(max_length=120, null=True, index=True)
    query_hash = fields.CharField(max_length=128, null=True)
    returned_memory_ids = fields.JSONField(default=list)
    scope_filters = fields.JSONField(default=dict)
    scores = fields.JSONField(default=dict)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_memory_access_logs"
        indexes = (("org", "action", "created_at"),)
