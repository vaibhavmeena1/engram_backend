"""Google Workspace OAuth URL and callback boundary."""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import Request
from fastapi.responses import RedirectResponse
from google.auth.transport import requests as google_auth_requests
from google.oauth2 import id_token as google_id_token

from app.services.config_service import EngramConfigService
from app.services.session_service import SessionService
from app.services.user_identity_service import UserIdentityService
from app.services.vortex_http import bad_request, service_unavailable, unauthorized

OAUTH_STATE_COOKIE = "engram_oauth_state"
OAUTH_NONCE_COOKIE = "engram_oauth_nonce"
OAUTH_RETURN_TO_COOKIE = "engram_oauth_return_to"
OAUTH_TEMP_COOKIE_TTL_SECONDS = 600
CSRF_TOKEN_BYTES = 32
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GoogleTokenResponse:
    id_token: str


class GoogleOAuthService:
    """Keeps OAuth/OIDC transport and verification details out of routers."""

    SCOPES = "openid email profile"

    @classmethod
    def build_login_redirect(cls, return_to: str | None = None) -> RedirectResponse:
        settings = EngramConfigService.auth()
        if not settings.google_client_id or not settings.google_client_secret:
            raise service_unavailable("Google OAuth is not configured")

        success_url = (
            cls._validated_return_to(return_to) or settings.dashboard_login_success_url
        )
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        authorization_url = cls._authorization_url(state=state, nonce=nonce)
        response = RedirectResponse(authorization_url)
        cls._set_short_lived_cookie(response, OAUTH_STATE_COOKIE, state)
        cls._set_short_lived_cookie(response, OAUTH_NONCE_COOKIE, nonce)
        cls._set_short_lived_cookie(response, OAUTH_RETURN_TO_COOKIE, success_url)
        return response

    @classmethod
    async def handle_callback(
        cls, request: Request, code: str | None, state: str | None
    ) -> RedirectResponse:
        settings = EngramConfigService.auth()
        failure_response = cls._failure_redirect()

        try:
            stored_state = cls._read_signed_cookie(request, OAUTH_STATE_COOKIE)
            stored_nonce = cls._read_signed_cookie(request, OAUTH_NONCE_COOKIE)
            return_to = cls._read_signed_cookie(request, OAUTH_RETURN_TO_COOKIE)

            if not code or not state or not stored_state or not stored_nonce:
                raise unauthorized("Invalid OAuth callback")
            if not hmac.compare_digest(state, stored_state):
                raise unauthorized("Invalid OAuth callback")

            token_response = await cls._exchange_authorization_code(code)
            id_token_payload = await cls._verify_id_token(token_response.id_token)
            cls._validate_nonce(id_token_payload, stored_nonce)

            identity_claims = UserIdentityService.google_claims_from_id_token_payload(
                id_token_payload
            )
            resolved_identity = await UserIdentityService.resolve_google_identity(
                identity_claims
            )
            created_session = await SessionService.create_web_session(
                user=resolved_identity.user,
                organization=resolved_identity.organization,
                metadata=cls._session_metadata(request),
            )

            success_url = (
                cls._validated_return_to(return_to)
                or settings.dashboard_login_success_url
            )
            response = RedirectResponse(success_url)
            cls._set_session_cookie(
                response, created_session.token, created_session.expires_at
            )
            cls._set_csrf_cookie(response, created_session.expires_at)
            cls._clear_oauth_temp_cookies(response)
            return response
        except Exception:  # noqa: BLE001
            # Browser callback errors should stay generic and redirect to the dashboard failure page.
            # Detailed exception text can include provider/token details, so do not expose it to users.
            logger.warning("Google OAuth callback failed", exc_info=True)
            cls._clear_oauth_temp_cookies(failure_response)
            return failure_response

    @classmethod
    def _authorization_url(cls, *, state: str, nonce: str) -> str:
        settings = EngramConfigService.auth()
        query_params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": cls.SCOPES,
            "state": state,
            "nonce": nonce,
            "hd": settings.google_hosted_domain,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{settings.google_authorization_endpoint}?{urlencode(query_params)}"

    @classmethod
    async def _exchange_authorization_code(cls, code: str) -> GoogleTokenResponse:
        settings = EngramConfigService.auth()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    settings.google_token_endpoint,
                    data={
                        "code": code,
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "redirect_uri": settings.google_redirect_uri,
                        "grant_type": "authorization_code",
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise unauthorized("Invalid OAuth callback") from exc

        id_token_value = payload.get("id_token")
        if not isinstance(id_token_value, str) or not id_token_value.strip():
            raise unauthorized("Invalid OAuth callback")
        return GoogleTokenResponse(id_token=id_token_value)

    @classmethod
    async def _verify_id_token(cls, raw_id_token: str) -> dict[str, Any]:
        settings = EngramConfigService.auth()
        if not settings.google_client_id:
            raise service_unavailable("Google OAuth is not configured")

        def verify_token() -> dict[str, Any]:
            verification_request = google_auth_requests.Request()
            payload = google_id_token.verify_oauth2_token(
                raw_id_token,
                verification_request,
                audience=settings.google_client_id,
            )
            if payload.get("iss") not in GOOGLE_ISSUERS:
                raise ValueError("Invalid Google issuer")
            return payload

        try:
            return await asyncio.to_thread(verify_token)
        except ValueError as exc:
            raise unauthorized("Invalid OAuth callback") from exc

    @classmethod
    def _validate_nonce(cls, payload: dict[str, Any], expected_nonce: str) -> None:
        actual_nonce = payload.get("nonce")
        if not isinstance(actual_nonce, str) or not hmac.compare_digest(
            actual_nonce, expected_nonce
        ):
            raise unauthorized("Invalid OAuth callback")

    @classmethod
    def _validated_return_to(cls, return_to: str | None) -> str | None:
        if not return_to:
            return None

        normalized_return_to = return_to.strip()
        if not normalized_return_to:
            return None

        allowed_origins = cls._allowed_return_to_origins()
        parsed_return_to = urlparse(normalized_return_to)
        return_to_origin = f"{parsed_return_to.scheme}://{parsed_return_to.netloc}"
        if (
            not parsed_return_to.scheme
            or not parsed_return_to.netloc
            or return_to_origin not in allowed_origins
        ):
            raise bad_request("return_to origin is not allowed")
        return normalized_return_to

    @classmethod
    def _allowed_return_to_origins(cls) -> set[str]:
        settings = EngramConfigService.auth()
        configured_origins = (
            settings.dashboard_allowed_return_to_origins
            or EngramConfigService.cors().allowed_origins
        )
        allowed_origins = {
            origin.rstrip("/") for origin in configured_origins if origin.strip()
        }

        for dashboard_url in (
            settings.dashboard_login_success_url,
            settings.dashboard_login_failure_url,
        ):
            parsed_url = urlparse(dashboard_url)
            if parsed_url.scheme and parsed_url.netloc:
                allowed_origins.add(f"{parsed_url.scheme}://{parsed_url.netloc}")
        return allowed_origins

    @classmethod
    def _set_short_lived_cookie(
        cls, response: RedirectResponse, name: str, value: str
    ) -> None:
        settings = EngramConfigService.auth()
        response.set_cookie(
            key=name,
            value=cls._signed_cookie_value(value),
            max_age=OAUTH_TEMP_COOKIE_TTL_SECONDS,
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite=settings.session_cookie_same_site,
            domain=settings.session_cookie_domain or None,
        )

    @classmethod
    def _read_signed_cookie(cls, request: Request, name: str) -> str | None:
        cookie_value = request.cookies.get(name)
        if not cookie_value:
            return None

        try:
            encoded_payload, provided_signature = cookie_value.rsplit(".", 1)
        except ValueError:
            return None

        expected_signature = cls._sign_cookie_payload(encoded_payload)
        if not hmac.compare_digest(provided_signature, expected_signature):
            return None

        try:
            payload = json.loads(cls._base64_url_decode(encoded_payload).decode())
            issued_at = int(payload["iat"])
            value = str(payload["value"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

        now = int(datetime.now(UTC).timestamp())
        if issued_at > now or now - issued_at > OAUTH_TEMP_COOKIE_TTL_SECONDS:
            return None
        return value

    @classmethod
    def _signed_cookie_value(cls, value: str) -> str:
        payload = {
            "iat": int(datetime.now(UTC).timestamp()),
            "value": value,
        }
        encoded_payload = cls._base64_url_encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        )
        signature = cls._sign_cookie_payload(encoded_payload)
        return f"{encoded_payload}.{signature}"

    @classmethod
    def _set_session_cookie(
        cls, response: RedirectResponse, token: str, expires_at: datetime
    ) -> None:
        settings = EngramConfigService.auth()
        max_age = max(0, int((expires_at - datetime.now(UTC)).total_seconds()))
        response.set_cookie(
            key=settings.session_cookie_name,
            value=token,
            max_age=max_age,
            expires=expires_at,
            httponly=settings.session_cookie_http_only,
            secure=settings.session_cookie_secure,
            samesite=settings.session_cookie_same_site,
            domain=settings.session_cookie_domain or None,
        )

    @classmethod
    def _set_csrf_cookie(cls, response: RedirectResponse, expires_at: datetime) -> None:
        settings = EngramConfigService.auth()
        if not settings.csrf_protection_enabled:
            return

        max_age = max(0, int((expires_at - datetime.now(UTC)).total_seconds()))
        response.set_cookie(
            key=settings.csrf_cookie_name,
            value=secrets.token_urlsafe(CSRF_TOKEN_BYTES),
            max_age=max_age,
            expires=expires_at,
            httponly=False,
            secure=settings.session_cookie_secure,
            samesite=settings.session_cookie_same_site,
            domain=settings.session_cookie_domain or None,
        )

    @classmethod
    def _clear_oauth_temp_cookies(cls, response: RedirectResponse) -> None:
        settings = EngramConfigService.auth()
        for cookie_name in (
            OAUTH_STATE_COOKIE,
            OAUTH_NONCE_COOKIE,
            OAUTH_RETURN_TO_COOKIE,
        ):
            response.delete_cookie(
                key=cookie_name,
                domain=settings.session_cookie_domain or None,
                httponly=True,
                secure=settings.session_cookie_secure,
                samesite=settings.session_cookie_same_site,
            )

    @classmethod
    def _failure_redirect(cls) -> RedirectResponse:
        return RedirectResponse(EngramConfigService.auth().dashboard_login_failure_url)

    @classmethod
    def _session_metadata(cls, request: Request) -> dict[str, str]:
        metadata: dict[str, str] = {}
        user_agent = request.headers.get("user-agent")
        forwarded_for = request.headers.get("x-forwarded-for")
        client_host = request.client.host if request.client else None
        ip_address = (
            forwarded_for.split(",", 1)[0].strip() if forwarded_for else client_host
        )

        if user_agent:
            metadata["user_agent"] = user_agent[:512]
        if ip_address:
            metadata["ip_hash"] = hashlib.sha256(ip_address.encode()).hexdigest()
        return metadata

    @classmethod
    def _sign_cookie_payload(cls, encoded_payload: str) -> str:
        return cls._base64_url_encode(
            hmac.new(
                cls._cookie_signing_key(), encoded_payload.encode(), hashlib.sha256
            ).digest()
        )

    @classmethod
    def _cookie_signing_key(cls) -> bytes:
        signing_key = EngramConfigService.auth().jwt_signing_key.strip()
        if not signing_key:
            raise service_unavailable("OAuth state signing key is not configured")
        return signing_key.encode()

    @classmethod
    def _base64_url_encode(cls, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

    @classmethod
    def _base64_url_decode(cls, value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(f"{value}{padding}".encode())
