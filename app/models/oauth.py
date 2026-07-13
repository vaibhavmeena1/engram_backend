"""OAuth facade persistence models for external MCP connector flows."""

from tortoise import fields

from app.models.base import EngramModel


class OAuthClient(EngramModel):
    client_id = fields.CharField(max_length=255, unique=True)
    client_name = fields.CharField(max_length=255, null=True)
    redirect_uris = fields.JSONField(default=list)
    grant_types = fields.JSONField(default=lambda: ["authorization_code"])
    response_types = fields.JSONField(default=lambda: ["code"])
    token_endpoint_auth_method = fields.CharField(max_length=64, default="none")
    metadata = fields.JSONField(default=dict)
    last_seen_at = fields.DatetimeField(null=True)

    class Meta:
        table = "engram_oauth_clients"


class OAuthAuthorizationCode(EngramModel):
    expires_at = fields.DatetimeField()
    used_at = fields.DatetimeField(null=True)
    code_hash = fields.CharField(max_length=128, unique=True)
    client_id = fields.CharField(max_length=255)
    redirect_uri = fields.TextField()
    scope = fields.CharField(max_length=255, default="mcp")
    code_challenge = fields.CharField(max_length=255)
    code_challenge_method = fields.CharField(max_length=16, default="S256")
    resource = fields.TextField(null=True)
    user = fields.ForeignKeyField(
        "dao.User", related_name="oauth_authorization_codes", on_delete=fields.CASCADE
    )
    org = fields.ForeignKeyField(
        "dao.Organization",
        related_name="oauth_authorization_codes",
        on_delete=fields.CASCADE,
    )
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_oauth_authorization_codes"
        indexes = (
            ("expires_at",),
            ("used_at",),
            ("user", "org"),
        )
