"""OAuth authorize and token exchange logic for MCP connector flows."""

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import RedirectResponse
from tortoise.transactions import in_transaction

from app.models.oauth import OAuthAuthorizationCode
from app.schemas.auth import OAuthTokenResponse
from app.services.config_service import EngramConfigService
from app.services.google_oauth_service import GoogleOAuthService
from app.services.oauth_client_service import OAuthClientService
from app.services.personal_access_token_service import PersonalAccessTokenService
from app.services.session_service import SessionService
from app.services.vortex_http import (
    bad_request,
    forbidden,
    internal_server_error,
    unauthorized,
)


@dataclass(frozen=True)
class ValidatedAuthorizeRequest:
    client_id: str
    redirect_uri: str
    scope: str
    state: str | None
    code_challenge: str
    code_challenge_method: str
    resource: str | None


class OAuthAuthorizationService:
    """Implements public-client authorization-code flow with PKCE S256."""

    SUPPORTED_SCOPE = "mcp"
    SUPPORTED_RESPONSE_TYPE = "code"
    SUPPORTED_GRANT_TYPE = "authorization_code"
    SUPPORTED_CODE_CHALLENGE_METHOD = "S256"

    @classmethod
    async def authorize(
        cls,
        *,
        request: Request,
        response_type: str | None,
        client_id: str | None,
        redirect_uri: str | None,
        state: str | None,
        scope: str | None,
        code_challenge: str | None,
        code_challenge_method: str | None,
        resource: str | None,
    ) -> RedirectResponse:
        if not EngramConfigService.oauth().enabled:
            raise forbidden("OAuth connector flow is disabled")

        validated_request = await cls.validate_authorize_request(
            response_type=response_type,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            resource=resource,
        )

        settings = EngramConfigService.auth()
        session_cookie = request.cookies.get(settings.session_cookie_name)
        if not session_cookie:
            return GoogleOAuthService.build_login_redirect(return_to=str(request.url))

        try:
            verified_session = await SessionService.verify_session_token(session_cookie)
        except Exception:  # noqa: BLE001 - invalid sessions restart browser login.
            return GoogleOAuthService.build_login_redirect(return_to=str(request.url))

        if (
            not verified_session.user.is_active
            or not verified_session.organization.is_active
        ):
            raise forbidden("Authenticated user or organization is inactive")

        authorization_code = await cls.create_authorization_code(
            validated_request=validated_request,
            user_id=str(verified_session.user.id),
            org_id=str(verified_session.organization.id),
        )
        return cls.authorization_success_redirect(
            redirect_uri=validated_request.redirect_uri,
            code=authorization_code,
            state=validated_request.state,
        )

    @classmethod
    async def redeem_token(
        cls,
        *,
        grant_type: str | None,
        code: str | None,
        client_id: str | None,
        redirect_uri: str | None,
        code_verifier: str | None,
    ) -> OAuthTokenResponse:
        if not EngramConfigService.oauth().enabled:
            raise forbidden("OAuth connector flow is disabled")
        if (grant_type or "").strip() != cls.SUPPORTED_GRANT_TYPE:
            raise bad_request("Only authorization_code grant is supported")
        normalized_code = cls.required_value(code, "code")
        normalized_client_id = cls.required_value(client_id, "client_id")
        normalized_redirect_uri = cls.required_value(redirect_uri, "redirect_uri")
        normalized_code_verifier = cls.required_value(code_verifier, "code_verifier")

        code_hash = cls.hash_authorization_code(normalized_code)
        async with in_transaction():
            authorization_code = await (
                OAuthAuthorizationCode.filter(code_hash=code_hash)
                .select_related("user", "org")
                .first()
            )
            if not authorization_code:
                raise unauthorized("Invalid authorization code")
            if authorization_code.used_at is not None:
                raise unauthorized("Authorization code has already been used")
            if authorization_code.expires_at <= datetime.now(UTC):
                raise unauthorized("Authorization code has expired")
            if authorization_code.client_id != normalized_client_id:
                raise unauthorized("Authorization code client does not match")
            if authorization_code.redirect_uri != normalized_redirect_uri:
                raise unauthorized("Authorization code redirect_uri does not match")
            cls.validate_pkce(
                code_verifier=normalized_code_verifier,
                code_challenge=authorization_code.code_challenge,
            )

            await OAuthClientService.get_validated_client(
                normalized_client_id, normalized_redirect_uri
            )
            authorization_code.used_at = datetime.now(UTC)
            await authorization_code.save(update_fields=["used_at", "updated_at"])

        client = await OAuthClientService.get_validated_client(
            normalized_client_id, normalized_redirect_uri
        )
        created_token = await PersonalAccessTokenService.create_oauth_mcp_access_token(
            user=authorization_code.user,
            organization=authorization_code.org,
            client_id=normalized_client_id,
            client_name=client.client_name or "Claude Desktop OAuth",
            redirect_uri=normalized_redirect_uri,
        )
        return OAuthTokenResponse(
            access_token=created_token.token,
            expires_in=EngramConfigService.oauth().default_mcp_access_token_ttl_seconds,
            scope=authorization_code.scope,
        )

    @classmethod
    async def validate_authorize_request(
        cls,
        *,
        response_type: str | None,
        client_id: str | None,
        redirect_uri: str | None,
        state: str | None,
        scope: str | None,
        code_challenge: str | None,
        code_challenge_method: str | None,
        resource: str | None,
    ) -> ValidatedAuthorizeRequest:
        if (response_type or "").strip() != cls.SUPPORTED_RESPONSE_TYPE:
            raise bad_request("Only code response_type is supported")
        normalized_client_id = cls.required_value(client_id, "client_id")
        normalized_redirect_uri = cls.required_value(redirect_uri, "redirect_uri")
        normalized_scope = cls.normalize_scope(scope)
        normalized_code_challenge = cls.required_value(code_challenge, "code_challenge")
        normalized_code_challenge_method = (code_challenge_method or "").strip()
        if normalized_code_challenge_method != cls.SUPPORTED_CODE_CHALLENGE_METHOD:
            raise bad_request("Only S256 PKCE code challenge method is supported")

        await OAuthClientService.get_validated_client(
            normalized_client_id, normalized_redirect_uri
        )
        return ValidatedAuthorizeRequest(
            client_id=normalized_client_id,
            redirect_uri=normalized_redirect_uri,
            scope=normalized_scope,
            state=(state or "").strip() or None,
            code_challenge=normalized_code_challenge,
            code_challenge_method=normalized_code_challenge_method,
            resource=(resource or "").strip() or None,
        )

    @classmethod
    async def create_authorization_code(
        cls,
        *,
        validated_request: ValidatedAuthorizeRequest,
        user_id: str,
        org_id: str,
    ) -> str:
        raw_code = secrets.token_urlsafe(48)
        settings = EngramConfigService.oauth()
        await OAuthAuthorizationCode.create(
            expires_at=datetime.now(UTC)
            + timedelta(seconds=settings.authorization_code_ttl_seconds),
            code_hash=cls.hash_authorization_code(raw_code),
            client_id=validated_request.client_id,
            redirect_uri=validated_request.redirect_uri,
            scope=validated_request.scope,
            code_challenge=validated_request.code_challenge,
            code_challenge_method=validated_request.code_challenge_method,
            resource=validated_request.resource,
            user_id=user_id,
            org_id=org_id,
            metadata={"source": "claude_desktop_connector"},
        )
        return raw_code

    @classmethod
    def authorization_success_redirect(
        cls, *, redirect_uri: str, code: str, state: str | None
    ) -> RedirectResponse:
        query_params = {"code": code}
        if state:
            query_params["state"] = state
        separator = "&" if "?" in redirect_uri else "?"
        return RedirectResponse(f"{redirect_uri}{separator}{urlencode(query_params)}")

    @classmethod
    def validate_pkce(cls, *, code_verifier: str, code_challenge: str) -> None:
        computed_challenge = cls.base64_url_encode(
            hashlib.sha256(code_verifier.encode()).digest()
        )
        if not hmac.compare_digest(computed_challenge, code_challenge):
            raise unauthorized("PKCE verification failed")

    @classmethod
    def hash_authorization_code(cls, raw_code: str) -> str:
        hash_secret = EngramConfigService.oauth().authorization_code_hash_secret.strip()
        if not hash_secret:
            raise internal_server_error(
                "OAuth authorization code hash secret is not configured"
            )
        return hmac.new(
            hash_secret.encode(), raw_code.encode(), hashlib.sha256
        ).hexdigest()

    @classmethod
    def normalize_scope(cls, scope: str | None) -> str:
        requested_scopes = {
            requested_scope.strip().lower()
            for requested_scope in (scope or cls.SUPPORTED_SCOPE).split()
            if requested_scope.strip()
        }
        if cls.SUPPORTED_SCOPE not in requested_scopes:
            raise bad_request("mcp scope is required")
        return cls.SUPPORTED_SCOPE

    @classmethod
    def required_value(cls, value: str | None, field_name: str) -> str:
        normalized_value = (value or "").strip()
        if not normalized_value:
            raise bad_request(f"{field_name} is required")
        return normalized_value

    @classmethod
    def base64_url_encode(cls, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
