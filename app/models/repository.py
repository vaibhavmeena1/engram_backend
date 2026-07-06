"""Repository identity models backed by canonical Git remote resolution."""

from tortoise import fields

from app.models.base import EngramModel


class Repository(EngramModel):
    org = fields.ForeignKeyField(
        "dao.Organization", related_name="repositories", on_delete=fields.CASCADE
    )
    provider = fields.CharField(max_length=64)
    host = fields.CharField(max_length=255)
    workspace = fields.CharField(max_length=255)
    repo_slug = fields.CharField(max_length=255)
    repository_key = fields.CharField(max_length=512)
    display_name = fields.CharField(max_length=255, null=True)
    canonical_remote_url = fields.CharField(max_length=1024, null=True)
    resolver_source = fields.CharField(max_length=64)
    resolver_confidence = fields.FloatField(default=1.0)
    is_active = fields.BooleanField(default=True)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_repositories"
        unique_together = (("org", "repository_key"),)


class RepositoryAlias(EngramModel):
    org = fields.ForeignKeyField(
        "dao.Organization", related_name="repository_aliases", on_delete=fields.CASCADE
    )
    repository = fields.ForeignKeyField(
        "dao.Repository", related_name="aliases", on_delete=fields.CASCADE
    )
    alias_key = fields.CharField(max_length=512)
    alias_remote_url = fields.CharField(max_length=1024, null=True)
    source = fields.CharField(max_length=64)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_repository_aliases"
        unique_together = (("org", "alias_key"),)
