"""User and external identity provisioning helpers."""

from dataclasses import dataclass
from typing import Any

from app.models.identity import Organization, User, UserIdentity
from app.services.auth_context_service import AuthContextService
from app.services.config_service import EngramConfigService
from app.services.vortex_http import forbidden, unauthorized

GOOGLE_PROVIDER = "google"


@dataclass(frozen=True)
class GoogleIdentityClaims:
    provider_subject: str
    email: str
    email_verified: bool
    hosted_domain: str | None = None
    name: str | None = None
    picture: str | None = None
    locale: str | None = None


@dataclass(frozen=True)
class ResolvedGoogleIdentity:
    user: User
    organization: Organization
    identity: UserIdentity


class UserIdentityService:
    """Resolves Google Workspace claims into local users and identity rows."""

    @classmethod
    async def resolve_google_identity(
        cls, claims: GoogleIdentityClaims
    ) -> ResolvedGoogleIdentity:
        settings = EngramConfigService.auth()
        email = AuthContextService.normalize_email(claims.email)
        AuthContextService.validate_email_domain(email, settings.allowed_email_domains)
        cls._validate_google_claims(claims)

        organization = await AuthContextService.resolve_default_organization(
            settings.default_org_slug
        )
        identity = await UserIdentity.filter(
            provider=GOOGLE_PROVIDER, provider_subject=claims.provider_subject
        ).first()
        if identity:
            user = await User.get(id=identity.user_id)
        else:
            user = await AuthContextService.resolve_user(
                email, settings.auto_provision_users
            )

        cls._ensure_active_user(user)
        user.display_name = (
            user.display_name
            or claims.name
            or AuthContextService.display_name_from_email(email)
        )
        await user.save(update_fields=["display_name", "updated_at"])

        identity_profile = cls._safe_profile(claims)
        if identity:
            identity.user_id = user.id
            identity.email_at_login = email
            identity.email_verified = claims.email_verified
            identity.hosted_domain = claims.hosted_domain
            identity.profile = identity_profile
            await identity.save(
                update_fields=[
                    "user_id",
                    "email_at_login",
                    "email_verified",
                    "hosted_domain",
                    "profile",
                    "updated_at",
                ]
            )
        else:
            identity = await UserIdentity.create(
                user_id=user.id,
                provider=GOOGLE_PROVIDER,
                provider_subject=claims.provider_subject,
                email_at_login=email,
                email_verified=claims.email_verified,
                hosted_domain=claims.hosted_domain,
                profile=identity_profile,
            )

        return ResolvedGoogleIdentity(
            user=user, organization=organization, identity=identity
        )

    @classmethod
    def google_claims_from_id_token_payload(
        cls, payload: dict[str, Any]
    ) -> GoogleIdentityClaims:
        return GoogleIdentityClaims(
            provider_subject=str(payload.get("sub") or ""),
            email=str(payload.get("email") or ""),
            email_verified=cls._bool_claim(payload.get("email_verified")),
            hosted_domain=payload.get("hd"),
            name=payload.get("name"),
            picture=payload.get("picture"),
            locale=payload.get("locale"),
        )

    @classmethod
    def _bool_claim(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() == "true"
        return False

    @classmethod
    def _validate_google_claims(cls, claims: GoogleIdentityClaims) -> None:
        settings = EngramConfigService.auth()
        if not claims.provider_subject.strip():
            raise unauthorized("Google identity is invalid")
        if not claims.email_verified:
            raise forbidden("Google email is not verified")
        hosted_domain = (claims.hosted_domain or "").strip().lower()
        expected_hosted_domain = settings.google_hosted_domain.strip().lower()
        if (
            hosted_domain
            and expected_hosted_domain
            and hosted_domain != expected_hosted_domain
        ):
            raise forbidden("Google hosted domain is not allowed")

    @classmethod
    def _ensure_active_user(cls, user: User) -> None:
        if not user.is_active:
            raise forbidden("User is not active")

    @classmethod
    def _safe_profile(cls, claims: GoogleIdentityClaims) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "name": claims.name,
                "picture": claims.picture,
                "locale": claims.locale,
            }.items()
            if value
        }
