"""Identity, role, and authentication persistence models for Engram."""

from tortoise import fields

from app.models.base import EngramModel


class Organization(EngramModel):
    name = fields.CharField(max_length=255)
    slug = fields.CharField(max_length=120, unique=True)
    is_active = fields.BooleanField(default=True)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_organizations"


class User(EngramModel):
    email = fields.CharField(max_length=320, unique=True)
    display_name = fields.CharField(max_length=255, null=True)
    is_active = fields.BooleanField(default=True)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_users"


class UserIdentity(EngramModel):
    user = fields.ForeignKeyField(
        "dao.User", related_name="identities", on_delete=fields.CASCADE
    )
    provider = fields.CharField(max_length=64)
    provider_subject = fields.CharField(max_length=255)
    email_at_login = fields.CharField(max_length=320)
    email_verified = fields.BooleanField(default=False)
    hosted_domain = fields.CharField(max_length=255, null=True)
    profile = fields.JSONField(default=dict)

    class Meta:
        table = "engram_user_identities"
        unique_together = (("provider", "provider_subject"),)


class Session(EngramModel):
    user = fields.ForeignKeyField(
        "dao.User", related_name="sessions", on_delete=fields.CASCADE
    )
    org = fields.ForeignKeyField(
        "dao.Organization", related_name="sessions", on_delete=fields.CASCADE
    )
    client_type = fields.CharField(max_length=32, default="web")
    jwt_id_hash = fields.CharField(max_length=128, unique=True)
    last_seen_at = fields.DatetimeField(null=True)
    expires_at = fields.DatetimeField()
    revoked_at = fields.DatetimeField(null=True)
    revoked_reason = fields.TextField(null=True)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_sessions"
        indexes = (("user", "org", "revoked_at"), ("expires_at",))


class PersonalAccessToken(EngramModel):
    user = fields.ForeignKeyField(
        "dao.User", related_name="personal_access_tokens", on_delete=fields.CASCADE
    )
    org = fields.ForeignKeyField(
        "dao.Organization",
        related_name="personal_access_tokens",
        on_delete=fields.CASCADE,
    )
    name = fields.CharField(max_length=255)
    key_prefix = fields.CharField(max_length=64, index=True)
    token_hash = fields.CharField(max_length=128, unique=True)
    client_type = fields.CharField(max_length=32, default="mcp")
    scopes = fields.JSONField(default=list)
    last_used_at = fields.DatetimeField(null=True)
    expires_at = fields.DatetimeField(null=True)
    revoked_at = fields.DatetimeField(null=True)
    revoked_reason = fields.TextField(null=True)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_personal_access_tokens"
        indexes = (("user", "org", "revoked_at"), ("expires_at",))


class Role(EngramModel):
    org = fields.ForeignKeyField(
        "dao.Organization", related_name="roles", on_delete=fields.CASCADE
    )
    slug = fields.CharField(max_length=120)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    permissions = fields.JSONField(default=list)
    is_system = fields.BooleanField(default=False)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_roles"
        unique_together = (("org", "slug"),)


class RoleAssignment(EngramModel):
    org = fields.ForeignKeyField(
        "dao.Organization", related_name="role_assignments", on_delete=fields.CASCADE
    )
    user = fields.ForeignKeyField(
        "dao.User", related_name="role_assignments", on_delete=fields.CASCADE
    )
    role = fields.ForeignKeyField(
        "dao.Role", related_name="assignments", on_delete=fields.CASCADE
    )
    assigned_by = fields.ForeignKeyField(
        "dao.User",
        related_name="assigned_role_assignments",
        null=True,
        on_delete=fields.SET_NULL,
    )
    scope_type = fields.CharField(max_length=32, null=True)
    scope_id = fields.UUIDField(null=True)
    metadata = fields.JSONField(default=dict)

    class Meta:
        table = "engram_role_assignments"
        unique_together = (("org", "user", "role", "scope_type", "scope_id"),)
