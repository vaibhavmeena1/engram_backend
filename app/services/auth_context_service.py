"""ActorContext authentication dispatcher.

The previous shared config API key/secret path is intentionally retired. Dashboard
requests should resolve through backend-owned Google OAuth web sessions, and MCP
requests should resolve through web-generated Personal Access Tokens.
"""

import hmac
import re
from uuid import UUID

from fastapi import Request

from app.models.identity import Organization, User
from app.schemas.context import ActorContext
from app.schemas.enums import AuthClientType, AuthMethod
from app.services.actor_context import ActorContextService
from app.services.config_service import EngramConfigService
from app.services.personal_access_token_service import PersonalAccessTokenService
from app.services.session_service import SessionService
from app.services.vortex_http import (
    bad_request,
    forbidden,
    internal_server_error,
    unauthorized,
)

AUTHORIZATION_HEADER = "authorization"
CLIENT_HEADER = "x-engram-client"
REQUEST_ID_HEADER = "x-request-id"
SAFE_CSRF_METHODS = {"GET", "HEAD", "OPTIONS"}

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthContextService:
    """Builds trusted internal actor context from configured credential transports.

    Keep transport-specific auth code modular:
    - Google OAuth web cookie/session verification belongs in a focused OAuth/session service.
    - MCP Personal Access Token verification belongs in a focused token service.
    - This service should stay as the small dispatcher that converts verified credentials into ActorContext.
    """

    @classmethod
    async def resolve_actor_context(
        cls, request: Request, required_pat_scope: str | None = None
    ) -> ActorContext:
        settings = EngramConfigService.auth()

        if settings.phase1_header_enabled or settings.mode == "phase1_header":
            raise internal_server_error(
                "Phase-1 shared API key authentication has been retired; use Google OAuth web sessions "
                "or web-generated Personal Access Tokens instead."
            )

        authorization_header = cls.normalize_optional_header(
            request.headers.get(AUTHORIZATION_HEADER)
        )
        if authorization_header:
            raw_token = cls.bearer_token_from_authorization_header(authorization_header)
            verified_token = await PersonalAccessTokenService.verify_bearer_token(
                raw_token,
                required_scope=required_pat_scope,
            )
            return cls.build_actor_context(
                request=request,
                user=verified_token.user,
                organization=verified_token.organization,
                auth_method=AuthMethod.PERSONAL_ACCESS_TOKEN,
                personal_access_token_id=verified_token.token.id,
                client_type=AuthClientType(verified_token.token.client_type),
            )

        session_cookie = request.cookies.get(settings.session_cookie_name)
        if session_cookie:
            verified_session = await SessionService.verify_session_token(session_cookie)
            cls.validate_csrf_token(request)
            return cls.build_actor_context(
                request=request,
                user=verified_session.user,
                organization=verified_session.organization,
                auth_method=AuthMethod.OAUTH_WEB_COOKIE,
                session_id=verified_session.session.id,
                client_type=AuthClientType(verified_session.session.client_type),
            )

        raise unauthorized("Missing authentication credentials")

    @classmethod
    def build_actor_context(
        cls,
        *,
        request: Request,
        user: User,
        organization: Organization,
        auth_method: AuthMethod,
        permissions: list[str] | None = None,
        session_id: UUID | None = None,
        personal_access_token_id: UUID | None = None,
        client_type: AuthClientType | None = None,
    ) -> ActorContext:
        if not user.is_active:
            raise forbidden("User is not active")
        if not organization.is_active:
            raise forbidden("Organization is not active")

        actor_context = ActorContext(
            actor_user_id=user.id,
            email=user.email,
            org_id=organization.id,
            org_slug=organization.slug,
            client_name=cls.normalize_optional_header(
                request.headers.get(CLIENT_HEADER)
            ),
            request_id=cls.normalize_optional_header(
                request.headers.get(REQUEST_ID_HEADER)
            ),
            auth_method=auth_method,
            session_id=session_id,
            personal_access_token_id=personal_access_token_id,
            client_type=client_type,
            roles=cls.resolve_default_roles(user.email),
            permissions=permissions or [],
        )
        ActorContextService.set_actor_context(actor_context)
        return actor_context

    @classmethod
    def bearer_token_from_authorization_header(cls, authorization_header: str) -> str:
        scheme, _, token = authorization_header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise unauthorized("Invalid Authorization header")
        return token.strip()

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        normalized_email = (email or "").strip().lower()
        if not normalized_email:
            raise unauthorized("Missing user email")
        if not _EMAIL_PATTERN.match(normalized_email):
            raise bad_request("Malformed user email")
        return normalized_email

    @classmethod
    def validate_email_domain(cls, email: str, allowed_domains: list[str]) -> None:
        allowed_domain_set = {
            domain.strip().lower().removeprefix("@")
            for domain in allowed_domains
            if domain.strip()
        }
        email_domain = email.rsplit("@", 1)[-1]
        if email_domain not in allowed_domain_set:
            raise forbidden("Email domain is not allowed")

    @classmethod
    async def resolve_default_organization(cls, default_org_slug: str) -> Organization:
        org_slug = default_org_slug.strip().lower()
        if not org_slug:
            raise internal_server_error("Default organization slug is not configured")

        organization, _ = await Organization.get_or_create(
            slug=org_slug,
            defaults={
                "name": cls.display_name_from_slug(org_slug),
                "metadata": {"source": "auth_context"},
            },
        )
        if not organization.is_active:
            raise forbidden("Organization is not active")
        return organization

    @classmethod
    async def resolve_user(cls, email: str, auto_provision_users: bool) -> User:
        user = await User.get_or_none(email=email)
        if user:
            return user

        if not auto_provision_users:
            raise forbidden("User is not provisioned")

        return await User.create(
            email=email,
            display_name=cls.display_name_from_email(email),
            metadata={"source": "auth_context"},
        )

    @classmethod
    def resolve_default_roles(cls, email: str) -> list[str]:
        settings = EngramConfigService.auth()
        admin_emails = {
            admin_email.strip().lower() for admin_email in settings.admin_emails
        }
        if email in admin_emails:
            return ["admin", "user"]
        return ["user"]

    @classmethod
    def validate_csrf_token(cls, request: Request) -> None:
        settings = EngramConfigService.auth()
        if (
            not settings.csrf_protection_enabled
            or request.method.upper() in SAFE_CSRF_METHODS
        ):
            return

        csrf_cookie = cls.normalize_optional_header(
            request.cookies.get(settings.csrf_cookie_name)
        )
        csrf_header = cls.normalize_optional_header(
            request.headers.get(settings.csrf_header_name)
        )
        if (
            not csrf_cookie
            or not csrf_header
            or not hmac.compare_digest(csrf_cookie, csrf_header)
        ):
            raise forbidden("CSRF token is missing or invalid")

    @classmethod
    def normalize_optional_header(cls, value: str | None) -> str | None:
        normalized_value = (value or "").strip()
        return normalized_value or None

    @classmethod
    def display_name_from_email(cls, email: str) -> str:
        local_part = email.split("@", 1)[0]
        readable_name = (
            local_part.replace(".", " ").replace("_", " ").replace("-", " ").strip()
        )
        return readable_name.title() or email

    @classmethod
    def display_name_from_slug(cls, slug: str) -> str:
        readable_name = slug.replace("-", " ").replace("_", " ").strip()
        return readable_name.title() or slug

    @classmethod
    def parse_uuid(cls, value: str | None) -> UUID | None:
        if not value:
            return None
        try:
            return UUID(value)
        except ValueError:
            return None
