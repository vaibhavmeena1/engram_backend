"""Personal Access Token generation, storage, verification, and revocation."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models.identity import Organization, PersonalAccessToken, User
from app.schemas.auth import (
    PersonalAccessTokenCreateRequest,
    PersonalAccessTokenCreateResponse,
    PersonalAccessTokenResponse,
)
from app.schemas.context import ActorContext
from app.schemas.enums import AuthClientType, AuthMethod
from app.services.config_service import EngramConfigService
from app.services.rbac_service import RbacService
from app.services.vortex_http import (
    bad_request,
    forbidden,
    internal_server_error,
    not_found,
    unauthorized,
)


@dataclass(frozen=True)
class VerifiedPersonalAccessToken:
    token: PersonalAccessToken
    user: User
    organization: Organization


class PersonalAccessTokenService:
    """Owns user-scoped PAT lifecycle and keeps raw tokens out of storage."""

    DEFAULT_SCOPE = "mcp"

    @classmethod
    async def create_personal_access_token(
        cls,
        actor: ActorContext,
        request: PersonalAccessTokenCreateRequest,
    ) -> PersonalAccessTokenCreateResponse:
        cls._ensure_pat_management_actor(actor)
        settings = EngramConfigService.auth()
        if not settings.personal_access_tokens_enabled:
            raise forbidden("Personal Access Tokens are disabled")

        expires_in_seconds = cls._effective_ttl_seconds(request.expires_in_seconds)
        expires_at = (
            datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
            if expires_in_seconds
            else None
        )
        scopes = cls._normalize_scopes(request.scopes)
        client_type = cls._normalize_client_type(request.client_type)
        cls._validate_scope_for_client_type(client_type, scopes)

        raw_token, key_prefix = cls._generate_raw_token()
        token = await PersonalAccessToken.create(
            user_id=actor.actor_user_id,
            org_id=actor.org_id,
            name=request.name,
            key_prefix=key_prefix,
            token_hash=cls.hash_token(raw_token),
            client_type=client_type.value,
            scopes=scopes,
            expires_at=expires_at,
            metadata=request.metadata,
        )
        return PersonalAccessTokenCreateResponse(
            id=token.id,
            name=token.name,
            client_type=client_type,
            key_prefix=token.key_prefix,
            token=raw_token,
            expires_at=token.expires_at,
            scopes=token.scopes or [],
        )

    @classmethod
    async def list_personal_access_tokens(
        cls, actor: ActorContext
    ) -> list[PersonalAccessTokenResponse]:
        cls._ensure_pat_management_actor(actor)
        tokens = await PersonalAccessToken.filter(
            user_id=actor.actor_user_id, org_id=actor.org_id
        ).order_by("-created_at")
        return [cls._response(token) for token in tokens]

    @classmethod
    async def revoke_personal_access_token(
        cls, actor: ActorContext, token_id: UUID
    ) -> PersonalAccessTokenResponse:
        cls._ensure_pat_management_actor(actor)
        token = await PersonalAccessToken.get_or_none(id=token_id, org_id=actor.org_id)
        if not token:
            raise not_found("Personal Access Token not found")
        if token.user_id != actor.actor_user_id and not RbacService.is_admin(actor):
            raise forbidden("Personal Access Token does not belong to the current user")

        if token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)
            token.revoked_reason = "revoked_by_user"
            await token.save(
                update_fields=["revoked_at", "revoked_reason", "updated_at"]
            )
        return cls._response(token)

    @classmethod
    async def verify_bearer_token(
        cls,
        raw_token: str,
        required_scope: str | None = None,
    ) -> VerifiedPersonalAccessToken:
        settings = EngramConfigService.auth()
        if not settings.personal_access_tokens_enabled:
            raise forbidden("Personal Access Tokens are disabled")
        if not cls._has_expected_prefix(raw_token):
            raise unauthorized("Invalid bearer token")

        token = await (
            PersonalAccessToken.filter(token_hash=cls.hash_token(raw_token))
            .select_related("user", "org")
            .first()
        )
        if not token:
            raise unauthorized("Invalid bearer token")
        if token.revoked_at is not None:
            raise unauthorized("Invalid bearer token")
        if token.expires_at is not None and token.expires_at <= datetime.now(UTC):
            raise unauthorized("Invalid bearer token")

        scopes = cls._normalize_scopes(token.scopes or [])
        if required_scope and required_scope not in scopes:
            raise forbidden("Bearer token scope is not allowed")

        user = token.user
        organization = token.org
        if not user.is_active:
            raise forbidden("User is not active")
        if not organization.is_active:
            raise forbidden("Organization is not active")

        token.last_used_at = datetime.now(UTC)
        await token.save(update_fields=["last_used_at", "updated_at"])
        return VerifiedPersonalAccessToken(
            token=token, user=user, organization=organization
        )

    @classmethod
    def hash_token(cls, raw_token: str) -> str:
        hash_secret = (
            EngramConfigService.auth().personal_access_token_hash_secret.strip()
        )
        if not hash_secret:
            raise internal_server_error(
                "Personal Access Token hash secret is not configured"
            )
        return hmac.new(
            hash_secret.encode(), raw_token.encode(), hashlib.sha256
        ).hexdigest()

    @classmethod
    def _ensure_pat_management_actor(cls, actor: ActorContext) -> None:
        if actor.auth_method != AuthMethod.OAUTH_WEB_COOKIE:
            raise forbidden("Dashboard web session is required")

    @classmethod
    def _effective_ttl_seconds(cls, requested_ttl_seconds: int | None) -> int:
        settings = EngramConfigService.auth()
        ttl_seconds = (
            requested_ttl_seconds or settings.personal_access_token_default_ttl_seconds
        )
        if ttl_seconds > settings.personal_access_token_max_ttl_seconds:
            raise bad_request(
                "Personal Access Token expiry exceeds the configured maximum"
            )
        return ttl_seconds

    @classmethod
    def _normalize_scopes(cls, scopes: list[str]) -> list[str]:
        normalized_scopes = []
        for scope in scopes:
            normalized_scope = str(scope).strip().lower()
            if normalized_scope and normalized_scope not in normalized_scopes:
                normalized_scopes.append(normalized_scope)
        return normalized_scopes or [cls.DEFAULT_SCOPE]

    @classmethod
    def _normalize_client_type(
        cls, client_type: AuthClientType | str
    ) -> AuthClientType:
        if isinstance(client_type, AuthClientType):
            return client_type
        try:
            return AuthClientType(str(client_type))
        except ValueError as exc:
            raise bad_request("Invalid Personal Access Token client type") from exc

    @classmethod
    def _validate_scope_for_client_type(
        cls, client_type: AuthClientType, scopes: list[str]
    ) -> None:
        if client_type == AuthClientType.MCP and cls.DEFAULT_SCOPE not in scopes:
            raise bad_request("MCP Personal Access Tokens require the mcp scope")

    @classmethod
    def _generate_raw_token(cls) -> tuple[str, str]:
        settings = EngramConfigService.auth()
        environment = (
            "dev" if EngramConfigService.raw_config().get("DEV_MODE") else "live"
        )
        token_secret = secrets.token_hex(32)
        key_prefix = (
            f"{settings.personal_access_token_prefix}_{environment}_{token_secret[:8]}"
        )
        raw_token = (
            f"{settings.personal_access_token_prefix}_{environment}_{token_secret}"
        )
        return raw_token, key_prefix

    @classmethod
    def _has_expected_prefix(cls, raw_token: str) -> bool:
        token_prefix = EngramConfigService.auth().personal_access_token_prefix.strip()
        return bool(token_prefix and raw_token.startswith(f"{token_prefix}_"))

    @classmethod
    def _response(cls, token: PersonalAccessToken) -> PersonalAccessTokenResponse:
        return PersonalAccessTokenResponse(
            id=token.id,
            name=token.name,
            client_type=AuthClientType(token.client_type),
            key_prefix=token.key_prefix,
            created_at=token.created_at,
            last_used_at=token.last_used_at,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
            scopes=token.scopes or [],
        )
