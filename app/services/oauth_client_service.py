"""OAuth dynamic client registration and validation."""

import secrets
from datetime import UTC, datetime
from urllib.parse import urlparse

from app.models.oauth import OAuthClient
from app.schemas.auth import (
    OAuthClientRegistrationRequest,
    OAuthClientRegistrationResponse,
)
from app.services.config_service import EngramConfigService
from app.services.vortex_http import (
    bad_request,
    forbidden,
    not_found,
    service_unavailable,
)


class OAuthClientService:
    """Stores and validates public OAuth clients for MCP connector flows."""

    DEFAULT_GRANT_TYPES = ["authorization_code"]
    DEFAULT_RESPONSE_TYPES = ["code"]
    DEFAULT_TOKEN_ENDPOINT_AUTH_METHOD = "none"

    @classmethod
    async def register_client(
        cls, request: OAuthClientRegistrationRequest
    ) -> OAuthClientRegistrationResponse:
        settings = EngramConfigService.oauth()
        if not settings.enabled:
            raise service_unavailable("OAuth connector flow is disabled")
        if not settings.allow_dynamic_client_registration:
            raise forbidden("Dynamic client registration is disabled")

        redirect_uris = cls.validate_redirect_uris(request.redirect_uris)
        grant_types = cls.validate_grant_types(request.grant_types)
        response_types = cls.validate_response_types(request.response_types)
        token_auth_method = cls.validate_token_auth_method(
            request.token_endpoint_auth_method
        )
        client_name = cls.normalize_client_name(request.client_name)
        metadata = dict(request.metadata or {})
        if request.scope:
            metadata["scope"] = request.scope
        if request.model_extra:
            metadata["registration_extra"] = dict(request.model_extra)

        existing_client = await cls._find_existing_client(redirect_uris, client_name)
        if existing_client:
            existing_client.client_name = client_name or existing_client.client_name
            existing_client.redirect_uris = redirect_uris
            existing_client.grant_types = grant_types
            existing_client.response_types = response_types
            existing_client.token_endpoint_auth_method = token_auth_method
            existing_client.metadata = metadata
            existing_client.last_seen_at = datetime.now(UTC)
            await existing_client.save(
                update_fields=[
                    "client_name",
                    "redirect_uris",
                    "grant_types",
                    "response_types",
                    "token_endpoint_auth_method",
                    "metadata",
                    "last_seen_at",
                    "updated_at",
                ]
            )
            return cls.response(existing_client)

        client = await OAuthClient.create(
            client_id=cls.generate_client_id(),
            client_name=client_name,
            redirect_uris=redirect_uris,
            grant_types=grant_types,
            response_types=response_types,
            token_endpoint_auth_method=token_auth_method,
            metadata=metadata,
            last_seen_at=datetime.now(UTC),
        )
        return cls.response(client)

    @classmethod
    async def get_validated_client(
        cls, client_id: str, redirect_uri: str | None = None
    ) -> OAuthClient:
        normalized_client_id = (client_id or "").strip()
        if not normalized_client_id:
            raise bad_request("client_id is required")

        client = await OAuthClient.get_or_none(client_id=normalized_client_id)
        if not client:
            raise not_found("OAuth client not found")

        if redirect_uri is not None:
            cls.validate_registered_redirect_uri(client, redirect_uri)

        client.last_seen_at = datetime.now(UTC)
        await client.save(update_fields=["last_seen_at", "updated_at"])
        return client

    @classmethod
    def validate_registered_redirect_uri(
        cls, client: OAuthClient, redirect_uri: str
    ) -> str:
        normalized_redirect_uri = cls.validate_redirect_uris([redirect_uri])[0]
        registered_redirect_uris = [str(uri) for uri in client.redirect_uris or []]
        if normalized_redirect_uri not in registered_redirect_uris:
            raise bad_request("redirect_uri is not registered for this client")
        return normalized_redirect_uri

    @classmethod
    def validate_redirect_uris(cls, redirect_uris: list[str]) -> list[str]:
        settings = EngramConfigService.oauth()
        allowed_origins = {
            origin.rstrip("/")
            for origin in settings.allowed_redirect_uri_origins
            if origin.strip()
        }
        normalized_redirect_uris = []

        for redirect_uri in redirect_uris:
            normalized_redirect_uri = str(redirect_uri or "").strip()
            if not normalized_redirect_uri:
                continue
            parsed_redirect_uri = urlparse(normalized_redirect_uri)
            redirect_origin = (
                f"{parsed_redirect_uri.scheme}://{parsed_redirect_uri.netloc}"
            )
            is_https_allowed_origin = (
                parsed_redirect_uri.scheme == "https"
                and parsed_redirect_uri.netloc
                and redirect_origin.rstrip("/") in allowed_origins
            )

            is_loopback_redirect = (
                parsed_redirect_uri.scheme == "http"
                and parsed_redirect_uri.hostname in {"localhost", "127.0.0.1", "::1"}
            )

            if not is_https_allowed_origin and not is_loopback_redirect:
                raise bad_request("redirect_uri origin is not allowed")
            if normalized_redirect_uri not in normalized_redirect_uris:
                normalized_redirect_uris.append(normalized_redirect_uri)

        if not normalized_redirect_uris:
            raise bad_request("At least one redirect_uri is required")
        return normalized_redirect_uris

    @classmethod
    def validate_grant_types(cls, grant_types: list[str]) -> list[str]:
        normalized_grant_types = cls._normalize_string_list(grant_types)
        if normalized_grant_types and "authorization_code" not in normalized_grant_types:
            raise bad_request("authorization_code grant is required")
        return cls.DEFAULT_GRANT_TYPES

    @classmethod
    def validate_response_types(cls, response_types: list[str]) -> list[str]:
        normalized_response_types = cls._normalize_string_list(response_types)
        if normalized_response_types and "code" not in normalized_response_types:
            raise bad_request("code response type is required")
        return cls.DEFAULT_RESPONSE_TYPES

    @classmethod
    def validate_token_auth_method(cls, token_auth_method: str) -> str:
        normalized_token_auth_method = (token_auth_method or "").strip() or "none"
        if normalized_token_auth_method != cls.DEFAULT_TOKEN_ENDPOINT_AUTH_METHOD:
            raise bad_request("Only public clients without client secret are supported")
        return normalized_token_auth_method

    @classmethod
    def normalize_client_name(cls, client_name: str | None) -> str | None:
        normalized_client_name = (client_name or "").strip()
        return normalized_client_name[:255] or None

    @classmethod
    def response(cls, client: OAuthClient) -> OAuthClientRegistrationResponse:
        return OAuthClientRegistrationResponse(
            client_id=client.client_id,
            client_name=client.client_name,
            redirect_uris=list(client.redirect_uris or []),
            grant_types=list(client.grant_types or cls.DEFAULT_GRANT_TYPES),
            response_types=list(client.response_types or cls.DEFAULT_RESPONSE_TYPES),
            token_endpoint_auth_method=client.token_endpoint_auth_method,
        )

    @classmethod
    async def _find_existing_client(
        cls, redirect_uris: list[str], client_name: str | None
    ) -> OAuthClient | None:
        _ = client_name
        clients = await OAuthClient.all()
        requested_redirect_uri_set = set(redirect_uris)
        for client in clients:
            if set(client.redirect_uris or []) == requested_redirect_uri_set:
                return client
        return None

    @classmethod
    def generate_client_id(cls) -> str:
        return f"engram_oauth_{secrets.token_urlsafe(24)}"

    @classmethod
    def _normalize_string_list(cls, values: list[str]) -> list[str]:
        normalized_values = []
        for value in values or []:
            normalized_value = str(value or "").strip()
            if normalized_value and normalized_value not in normalized_values:
                normalized_values.append(normalized_value)
        return normalized_values
