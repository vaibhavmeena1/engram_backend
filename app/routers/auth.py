"""Authentication endpoints for dashboard sessions and current actor profile."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.models.identity import User
from app.routers.dependencies import resolve_actor
from app.schemas.auth import AuthProfileResponse
from app.schemas.context import ActorContext
from app.schemas.enums import AuthMethod
from app.services.config_service import EngramConfigService
from app.services.google_oauth_service import GoogleOAuthService
from app.services.session_service import SessionService
from app.services.vortex_http import forbidden, send_success_response

router = APIRouter(tags=["engram-auth"])


@router.get("/auth/google/login")
async def google_login(
    return_to: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    return GoogleOAuthService.build_login_redirect(return_to=return_to)


@router.get("/auth/google/callback")
async def google_callback(
    request: Request,
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    return await GoogleOAuthService.handle_callback(
        request=request, code=code, state=state
    )


@router.post("/auth/logout")
async def logout(
    request: Request, actor: Annotated[ActorContext, Depends(resolve_actor)]
) -> JSONResponse:
    await SessionService.revoke_actor_session(actor)
    response = send_success_response({"logged_out": True})
    settings = EngramConfigService.auth()
    response.delete_cookie(
        key=settings.session_cookie_name,
        domain=settings.session_cookie_domain or None,
        httponly=settings.session_cookie_http_only,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_same_site,
    )
    if settings.csrf_protection_enabled:
        response.delete_cookie(
            key=settings.csrf_cookie_name,
            domain=settings.session_cookie_domain or None,
            httponly=False,
            secure=settings.session_cookie_secure,
            samesite=settings.session_cookie_same_site,
        )
    return response


@router.get("/me")
async def me(actor: Annotated[ActorContext, Depends(resolve_actor)]) -> JSONResponse:
    return send_success_response(await _profile_response(actor))


async def _profile_response(actor: ActorContext) -> AuthProfileResponse:
    if actor.auth_method not in {
        AuthMethod.OAUTH_WEB_COOKIE,
        AuthMethod.PERSONAL_ACCESS_TOKEN,
    }:
        raise forbidden("Unsupported authentication method")

    user = await User.get_or_none(id=actor.actor_user_id)

    return AuthProfileResponse(
        id=actor.actor_user_id,
        email=actor.email,
        display_name=user.display_name if user else None,
        org_id=actor.org_id,
        org_slug=actor.org_slug,
        client_type=actor.client_type,
        auth_method=actor.auth_method,
        roles=actor.roles,
    )
