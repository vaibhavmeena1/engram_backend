"""OAuth discovery metadata for the MCP connector facade."""

from app.schemas.auth import (
    OAuthAuthorizationServerMetadataResponse,
    OAuthProtectedResourceMetadataResponse,
)
from app.services.config_service import EngramConfigService


class OAuthMetadataService:
    """Centralizes OAuth facade URL construction from runtime config."""

    @classmethod
    def protected_resource_metadata(cls) -> OAuthProtectedResourceMetadataResponse:
        settings = EngramConfigService.oauth()
        return OAuthProtectedResourceMetadataResponse(
            resource=settings.mcp_resource_url,
            authorization_servers=[settings.issuer],
            scopes_supported=["mcp"],
            bearer_methods_supported=["header"],
        )

    @classmethod
    def authorization_server_metadata(cls) -> OAuthAuthorizationServerMetadataResponse:
        settings = EngramConfigService.oauth()
        return OAuthAuthorizationServerMetadataResponse(
            issuer=settings.issuer,
            authorization_endpoint=cls.public_url(settings.authorization_endpoint_path),
            token_endpoint=cls.public_url(settings.token_endpoint_path),
            registration_endpoint=cls.public_url(settings.registration_endpoint_path),
            response_types_supported=["code"],
            grant_types_supported=["authorization_code"],
            code_challenge_methods_supported=["S256"],
            token_endpoint_auth_methods_supported=["none"],
            scopes_supported=["mcp"],
        )

    @classmethod
    def protected_resource_metadata_url(cls) -> str:
        return cls.public_url(
            EngramConfigService.oauth().protected_resource_metadata_path
        )

    @classmethod
    def public_url(cls, path: str) -> str:
        settings = EngramConfigService.oauth()
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{settings.public_base_url}{normalized_path}"

    @classmethod
    def www_authenticate_challenge(cls) -> str:
        return (
            "Bearer "
            f'resource_metadata="{cls.protected_resource_metadata_url()}", '
            'error="invalid_token", '
            'error_description="Missing or invalid access token"'
        )
