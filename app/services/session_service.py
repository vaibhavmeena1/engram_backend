"""Dashboard web-session persistence and verification."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.models.identity import Organization, Session, User
from app.schemas.context import ActorContext
from app.schemas.enums import AuthClientType
from app.services.token_service import TokenService
from app.services.vortex_http import forbidden, unauthorized


@dataclass(frozen=True)
class CreatedWebSession:
    session: Session
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class VerifiedWebSession:
    session: Session
    user: User
    organization: Organization


class SessionService:
    """Creates, verifies, and revokes backend-owned dashboard sessions."""

    @classmethod
    async def create_web_session(
        cls,
        *,
        user: User,
        organization: Organization,
        metadata: dict | None = None,
    ) -> CreatedWebSession:
        issued_token = TokenService.issue_web_session_token(
            user_id=user.id,
            org_id=organization.id,
            client_type=AuthClientType.WEB,
        )
        session = await Session.create(
            user_id=user.id,
            org_id=organization.id,
            client_type=AuthClientType.WEB.value,
            jwt_id_hash=TokenService.hash_jwt_id(issued_token.jwt_id),
            expires_at=issued_token.expires_at,
            metadata=metadata or {},
        )
        return CreatedWebSession(
            session=session,
            token=issued_token.token,
            expires_at=issued_token.expires_at,
        )

    @classmethod
    async def verify_session_token(cls, raw_token: str) -> VerifiedWebSession:
        verified_token = TokenService.verify_web_session_token(raw_token)
        session = await (
            Session.filter(
                jwt_id_hash=TokenService.hash_jwt_id(verified_token.jwt_id),
                user_id=verified_token.user_id,
                org_id=verified_token.org_id,
            )
            .select_related("user", "org")
            .first()
        )
        if not session:
            raise unauthorized("Invalid session")
        if session.revoked_at is not None:
            raise unauthorized("Session has been revoked")
        if session.expires_at <= datetime.now(UTC):
            raise unauthorized("Session has expired")

        user = session.user
        organization = session.org
        if not user.is_active:
            raise forbidden("User is not active")
        if not organization.is_active:
            raise forbidden("Organization is not active")

        session.last_seen_at = datetime.now(UTC)
        await session.save(update_fields=["last_seen_at", "updated_at"])
        return VerifiedWebSession(session=session, user=user, organization=organization)

    @classmethod
    async def revoke_actor_session(
        cls, actor: ActorContext, revoked_reason: str = "logout"
    ) -> bool:
        if not actor.session_id:
            return False

        session = await Session.get_or_none(
            id=actor.session_id, user_id=actor.actor_user_id, org_id=actor.org_id
        )
        if not session or session.revoked_at is not None:
            return False

        session.revoked_at = datetime.now(UTC)
        session.revoked_reason = revoked_reason
        await session.save(update_fields=["revoked_at", "revoked_reason", "updated_at"])
        return True
