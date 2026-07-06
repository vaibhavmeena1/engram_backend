"""Phase 4 auth reliability, auditability, and hardening tests."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from starlette.requests import Request
from vortex.exceptions import VortexException

from app.models.audit import MemoryAccessLog
from app.models.identity import Organization, PersonalAccessToken, User
from app.routers.auth import _profile_response
from app.schemas.auth import PersonalAccessTokenCreateRequest
from app.schemas.context import ActorContext
from app.schemas.enums import AuthClientType, AuthMethod
from app.services.audit_query_service import AuditQueryService
from app.services.audit_service import AuditService
from app.services.auth_context_service import AuthContextService
from app.services.google_oauth_service import GoogleOAuthService
from app.services.mcp_context_service import McpContextService
from app.services.personal_access_token_service import PersonalAccessTokenService
from app.services.session_service import SessionService


pytestmark = pytest.mark.anyio


async def test_cookie_and_pat_auth_profile_contracts(test_db: None) -> None:
    user, organization = await _create_user_and_org()
    created_session = await SessionService.create_web_session(
        user=user, organization=organization
    )

    cookie_actor = await AuthContextService.resolve_actor_context(
        _request(cookies={"engram_session": created_session.token})
    )
    cookie_profile = await _profile_response(cookie_actor)

    assert cookie_profile.id == user.id
    assert cookie_profile.email == user.email
    assert cookie_profile.auth_method == AuthMethod.OAUTH_WEB_COOKIE
    assert cookie_profile.client_type == AuthClientType.WEB
    assert cookie_actor.session_id == created_session.session.id

    created_pat = await PersonalAccessTokenService.create_personal_access_token(
        cookie_actor,
        PersonalAccessTokenCreateRequest(
            name="Claude Code", client_type=AuthClientType.MCP, scopes=["mcp"]
        ),
    )
    listed_tokens = await PersonalAccessTokenService.list_personal_access_tokens(
        cookie_actor
    )

    assert created_pat.token.startswith("engpat_")
    assert len(listed_tokens) == 1
    assert listed_tokens[0].id == created_pat.id
    assert "token" not in listed_tokens[0].model_dump()

    pat_actor = await AuthContextService.resolve_actor_context(
        _request(headers={"Authorization": f"Bearer {created_pat.token}"})
    )
    pat_profile = await _profile_response(pat_actor)

    assert pat_profile.id == user.id
    assert pat_profile.auth_method == AuthMethod.PERSONAL_ACCESS_TOKEN
    assert pat_profile.client_type == AuthClientType.MCP
    assert pat_actor.personal_access_token_id == created_pat.id


async def test_get_me_accepts_active_pat_without_mcp_scope_but_mcp_rejects_it(
    test_db: None,
) -> None:
    user, organization = await _create_user_and_org()
    web_actor = await _web_actor(user, organization)
    created_pat = await PersonalAccessTokenService.create_personal_access_token(
        web_actor,
        PersonalAccessTokenCreateRequest(
            name="Automation Profile Reader",
            client_type=AuthClientType.AUTOMATION,
            scopes=["profile"],
        ),
    )

    profile_actor = await AuthContextService.resolve_actor_context(
        _request(headers={"Authorization": f"Bearer {created_pat.token}"})
    )

    assert profile_actor.auth_method == AuthMethod.PERSONAL_ACCESS_TOKEN
    assert profile_actor.client_type == AuthClientType.AUTOMATION

    with pytest.raises(VortexException) as exc_info:
        await AuthContextService.resolve_actor_context(
            _request(headers={"Authorization": f"Bearer {created_pat.token}"}),
            required_pat_scope="mcp",
        )

    assert exc_info.value.status_code == 403


async def test_mcp_pat_actor_guard_allows_mcp_pat_and_rejects_cookie_actor(
    test_db: None,
) -> None:
    user, organization = await _create_user_and_org()
    web_actor = await _web_actor(user, organization)
    created_pat = await PersonalAccessTokenService.create_personal_access_token(
        web_actor,
        PersonalAccessTokenCreateRequest(
            name="Claude Code", client_type=AuthClientType.MCP, scopes=["mcp"]
        ),
    )

    mcp_actor = await AuthContextService.resolve_actor_context(
        _request(headers={"Authorization": f"Bearer {created_pat.token}"}),
        required_pat_scope="mcp",
    )

    McpContextService.ensure_mcp_actor(mcp_actor)

    with pytest.raises(VortexException) as exc_info:
        McpContextService.ensure_mcp_actor(web_actor)

    assert exc_info.value.status_code == 403


async def test_revoked_and_expired_pat_fail_generically(test_db: None) -> None:
    user, organization = await _create_user_and_org()
    web_actor = await _web_actor(user, organization)
    revoked_pat = await PersonalAccessTokenService.create_personal_access_token(
        web_actor,
        PersonalAccessTokenCreateRequest(
            name="Revoked", client_type=AuthClientType.MCP, scopes=["mcp"]
        ),
    )

    await PersonalAccessTokenService.revoke_personal_access_token(
        web_actor, revoked_pat.id
    )

    with pytest.raises(VortexException) as revoked_exc:
        await PersonalAccessTokenService.verify_bearer_token(revoked_pat.token)

    assert revoked_exc.value.status_code == 401
    assert revoked_exc.value.error == "Invalid bearer token"

    expired_pat = await PersonalAccessTokenService.create_personal_access_token(
        web_actor,
        PersonalAccessTokenCreateRequest(
            name="Expired", client_type=AuthClientType.MCP, scopes=["mcp"]
        ),
    )
    token_row = await PersonalAccessToken.get(id=expired_pat.id)
    token_row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await token_row.save(update_fields=["expires_at", "updated_at"])

    with pytest.raises(VortexException) as expired_exc:
        await PersonalAccessTokenService.verify_bearer_token(expired_pat.token)

    assert expired_exc.value.status_code == 401
    assert expired_exc.value.error == "Invalid bearer token"


async def test_csrf_is_required_for_state_changing_cookie_auth_when_enabled(
    test_db: None, test_config: dict
) -> None:
    test_config["ENGRAM_AUTH"]["CSRF_PROTECTION_ENABLED"] = True
    user, organization = await _create_user_and_org()
    created_session = await SessionService.create_web_session(
        user=user, organization=organization
    )

    with pytest.raises(VortexException) as missing_csrf_exc:
        await AuthContextService.resolve_actor_context(
            _request(method="POST", cookies={"engram_session": created_session.token})
        )

    assert missing_csrf_exc.value.status_code == 403

    actor = await AuthContextService.resolve_actor_context(
        _request(
            method="POST",
            headers={"x-engram-csrf": "csrf-token"},
            cookies={
                "engram_session": created_session.token,
                "engram_csrf": "csrf-token",
            },
        )
    )

    assert actor.auth_method == AuthMethod.OAUTH_WEB_COOKIE


async def test_audit_logs_include_auth_actor_fields(test_db: None) -> None:
    user, organization = await _create_user_and_org(email="admin@1mg.com")
    web_actor = await _web_actor(user, organization)
    created_pat = await PersonalAccessTokenService.create_personal_access_token(
        web_actor,
        PersonalAccessTokenCreateRequest(
            name="Claude Code", client_type=AuthClientType.MCP, scopes=["mcp"]
        ),
    )
    pat_actor = await AuthContextService.resolve_actor_context(
        _request(
            headers={
                "Authorization": f"Bearer {created_pat.token}",
                "X-Engram-Client": "claude-code",
                "X-Request-Id": "request-123",
            }
        )
    )

    await AuditService.log_memory_event(
        actor=pat_actor, action="memory_search", query_text="audit me"
    )

    raw_log = await MemoryAccessLog.get(action="memory_search")
    assert raw_log.auth_method == AuthMethod.PERSONAL_ACCESS_TOKEN.value
    assert raw_log.client_type == AuthClientType.MCP.value
    assert raw_log.personal_access_token_id == created_pat.id
    assert raw_log.session_id is None
    assert raw_log.actor_user_id == user.id
    assert raw_log.request_id == "request-123"

    logs = await AuditQueryService.list_memory_access_logs(
        web_actor, action="memory_search"
    )
    assert len(logs) == 1
    assert logs[0].auth_method == AuthMethod.PERSONAL_ACCESS_TOKEN
    assert logs[0].client_type == AuthClientType.MCP
    assert logs[0].personal_access_token_id == created_pat.id
    assert logs[0].actor_user_id == user.id


def test_google_oauth_return_to_is_restricted_to_allowed_dashboard_origins(
    test_config: dict,
) -> None:
    assert (
        GoogleOAuthService._validated_return_to("http://localhost:5173/settings")
        == "http://localhost:5173/settings"
    )

    with pytest.raises(VortexException) as exc_info:
        GoogleOAuthService._validated_return_to("https://evil.example/settings")

    assert exc_info.value.status_code == 400


def test_auth_config_rejects_unsafe_cross_site_cookie_settings(
    test_config: dict,
) -> None:
    auth_config = test_config["ENGRAM_AUTH"]
    auth_config["SESSION_COOKIE_SAME_SITE"] = "none"
    auth_config["SESSION_COOKIE_SECURE"] = False
    auth_config["CSRF_PROTECTION_ENABLED"] = False

    with pytest.raises(ValueError):
        AuthContextService.resolve_default_roles("user@1mg.com")


async def _create_user_and_org(
    email: str = "user@1mg.com",
) -> tuple[User, Organization]:
    organization = await Organization.create(name="Tata 1mg", slug="tata1mg")
    user = await User.create(email=email, display_name="Test User")
    return user, organization


async def _web_actor(user: User, organization: Organization) -> ActorContext:
    created_session = await SessionService.create_web_session(
        user=user, organization=organization
    )
    return await AuthContextService.resolve_actor_context(
        _request(cookies={"engram_session": created_session.token})
    )


def _request(
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
) -> Request:
    raw_headers = [
        (key.lower().encode(), value.encode()) for key, value in (headers or {}).items()
    ]
    if cookies:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())
        raw_headers.append((b"cookie", cookie_header.encode()))

    scope: dict[str, Any] = {
        "type": "http",
        "method": method,
        "path": "/",
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)
