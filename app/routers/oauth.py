"""OAuth facade endpoints for Claude Desktop MCP connector flows."""

from typing import Annotated
from urllib.parse import parse_qs

from fastapi import APIRouter, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse

from app.schemas.auth import OAuthClientRegistrationRequest
from app.services.oauth_authorization_service import OAuthAuthorizationService
from app.services.oauth_client_service import OAuthClientService
from app.services.oauth_metadata_service import OAuthMetadataService
from app.services.vortex_http import bad_request

router = APIRouter(tags=["engram-oauth"])


@router.get("/.well-known/oauth-protected-resource")
async def protected_resource_metadata() -> JSONResponse:
    return JSONResponse(
        jsonable_encoder(OAuthMetadataService.protected_resource_metadata())
    )


@router.get("/.well-known/oauth-authorization-server")
async def authorization_server_metadata() -> JSONResponse:
    return JSONResponse(
        jsonable_encoder(OAuthMetadataService.authorization_server_metadata())
    )


@router.post("/oauth/register")
async def register_client(
    registration_request: OAuthClientRegistrationRequest,
) -> JSONResponse:
    registered_client = await OAuthClientService.register_client(registration_request)
    return JSONResponse(jsonable_encoder(registered_client), status_code=201)


@router.get("/oauth/authorize")
async def authorize(
    request: Request,
    response_type: Annotated[str | None, Query()] = None,
    client_id: Annotated[str | None, Query()] = None,
    redirect_uri: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    scope: Annotated[str | None, Query()] = None,
    code_challenge: Annotated[str | None, Query()] = None,
    code_challenge_method: Annotated[str | None, Query()] = None,
    resource: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    return await OAuthAuthorizationService.authorize(
        request=request,
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resource,
    )


@router.post("/oauth/token")
async def token(request: Request) -> JSONResponse:
    form_data = await _read_oauth_form_data(request)
    token_response = await OAuthAuthorizationService.redeem_token(
        grant_type=form_data.get("grant_type"),
        code=form_data.get("code"),
        client_id=form_data.get("client_id"),
        redirect_uri=form_data.get("redirect_uri"),
        code_verifier=form_data.get("code_verifier"),
    )
    return JSONResponse(jsonable_encoder(token_response))


async def _read_oauth_form_data(request: Request) -> dict[str, str]:
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise bad_request("OAuth token request body must be an object")
        return {
            str(key): str(value) for key, value in payload.items() if value is not None
        }

    body = (await request.body()).decode()
    parsed_form = parse_qs(body, keep_blank_values=True)
    return {
        key: values[-1]
        for key, values in parsed_form.items()
        if values and values[-1] is not None
    }
