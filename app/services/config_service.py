"""Typed accessors for Engram runtime configuration."""

from typing import Any, Self

from pydantic import Field, field_validator, model_validator
from vortex import CONFIG

from app.schemas.base import EngramBaseSchema
from app.schemas.enums import RetrievalMode


class EngramSettings(EngramBaseSchema):
    mcp_server_name: str = Field(default="engram-mcp", alias="MCP_SERVER_NAME")
    default_retrieval_mode: RetrievalMode = Field(
        default=RetrievalMode.LEXICAL, alias="DEFAULT_RETRIEVAL_MODE"
    )
    max_search_results: int = Field(default=20, alias="MAX_SEARCH_RESULTS", ge=1)
    per_scope_search_results: int | None = Field(
        default=None, alias="PER_SCOPE_SEARCH_RESULTS", ge=1
    )
    require_review_for_repo_memory: bool = Field(
        default=True, alias="REQUIRE_REVIEW_FOR_REPO_MEMORY"
    )
    require_review_for_org_memory: bool = Field(
        default=True, alias="REQUIRE_REVIEW_FOR_ORG_MEMORY"
    )
    allow_user_memory_auto_approve: bool = Field(
        default=True, alias="ALLOW_USER_MEMORY_AUTO_APPROVE"
    )


class EngramAuthSettings(EngramBaseSchema):
    mode: str = Field(default="google_workspace_oidc", alias="MODE")
    phase1_header_enabled: bool = Field(default=False, alias="PHASE1_HEADER_ENABLED")
    allowed_email_domains: list[str] = Field(
        default_factory=lambda: ["1mg.com"], alias="ALLOWED_EMAIL_DOMAINS"
    )
    google_hosted_domain: str = Field(default="1mg.com", alias="GOOGLE_HOSTED_DOMAIN")
    default_org_slug: str = Field(default="tata1mg", alias="DEFAULT_ORG_SLUG")
    admin_emails: list[str] = Field(default_factory=list, alias="ADMIN_EMAILS")
    auto_provision_users: bool = Field(default=True, alias="AUTO_PROVISION_USERS")
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_authorization_endpoint: str = Field(
        default="https://accounts.google.com/o/oauth2/v2/auth",
        alias="GOOGLE_AUTHORIZATION_ENDPOINT",
    )
    google_token_endpoint: str = Field(
        default="https://oauth2.googleapis.com/token", alias="GOOGLE_TOKEN_ENDPOINT"
    )
    google_jwks_uri: str = Field(
        default="https://www.googleapis.com/oauth2/v3/certs", alias="GOOGLE_JWKS_URI"
    )
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback",
        alias="GOOGLE_REDIRECT_URI",
    )
    jwt_issuer: str = Field(default="engram-backend", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="engram-clients", alias="JWT_AUDIENCE")
    jwt_signing_algorithm: str = Field(default="HS256", alias="JWT_SIGNING_ALGORITHM")
    jwt_signing_key: str = Field(default="", alias="JWT_SIGNING_KEY")
    access_token_ttl_seconds: int = Field(
        default=86400, alias="ACCESS_TOKEN_TTL_SECONDS", ge=1
    )
    web_session_ttl_seconds: int = Field(
        default=86400, alias="WEB_SESSION_TTL_SECONDS", ge=1
    )
    session_cookie_name: str = Field(
        default="engram_session", alias="SESSION_COOKIE_NAME"
    )
    session_cookie_domain: str = Field(default="", alias="SESSION_COOKIE_DOMAIN")
    session_cookie_secure: bool = Field(default=True, alias="SESSION_COOKIE_SECURE")
    session_cookie_http_only: bool = Field(
        default=True, alias="SESSION_COOKIE_HTTP_ONLY"
    )
    session_cookie_same_site: str = Field(
        default="lax", alias="SESSION_COOKIE_SAME_SITE"
    )
    csrf_protection_enabled: bool = Field(
        default=False, alias="CSRF_PROTECTION_ENABLED"
    )
    csrf_cookie_name: str = Field(default="engram_csrf", alias="CSRF_COOKIE_NAME")
    csrf_header_name: str = Field(default="x-engram-csrf", alias="CSRF_HEADER_NAME")
    dashboard_login_success_url: str = Field(
        default="http://localhost:5173/", alias="DASHBOARD_LOGIN_SUCCESS_URL"
    )
    dashboard_login_failure_url: str = Field(
        default="http://localhost:5173/login?error=auth_failed",
        alias="DASHBOARD_LOGIN_FAILURE_URL",
    )
    dashboard_allowed_return_to_origins: list[str] = Field(
        default_factory=list,
        alias="DASHBOARD_ALLOWED_RETURN_TO_ORIGINS",
    )
    personal_access_tokens_enabled: bool = Field(
        default=True, alias="PERSONAL_ACCESS_TOKENS_ENABLED"
    )
    personal_access_token_prefix: str = Field(
        default="engpat", alias="PERSONAL_ACCESS_TOKEN_PREFIX"
    )
    personal_access_token_default_ttl_seconds: int = Field(
        default=7776000,
        alias="PERSONAL_ACCESS_TOKEN_DEFAULT_TTL_SECONDS",
        ge=1,
    )
    personal_access_token_max_ttl_seconds: int = Field(
        default=15552000,
        alias="PERSONAL_ACCESS_TOKEN_MAX_TTL_SECONDS",
        ge=1,
    )
    personal_access_token_hash_secret: str = Field(
        default="", alias="PERSONAL_ACCESS_TOKEN_HASH_SECRET"
    )

    @field_validator("session_cookie_same_site")
    @classmethod
    def normalize_cookie_same_site(cls, value: str) -> str:
        normalized_value = (value or "").strip().lower()
        if normalized_value not in {"lax", "strict", "none"}:
            raise ValueError("SESSION_COOKIE_SAME_SITE must be lax, strict, or none")
        return normalized_value

    @field_validator("csrf_header_name")
    @classmethod
    def normalize_csrf_header_name(cls, value: str) -> str:
        normalized_value = (value or "").strip().lower()
        if not normalized_value:
            raise ValueError("CSRF_HEADER_NAME must not be empty")
        return normalized_value

    @model_validator(mode="after")
    def validate_auth_hardening(self) -> Self:
        if self.mode == "phase1_header" or self.phase1_header_enabled:
            raise ValueError(
                "Phase-1 shared header authentication is retired and cannot be enabled"
            )
        if not self.session_cookie_http_only:
            raise ValueError(
                "SESSION_COOKIE_HTTP_ONLY must stay enabled for dashboard sessions"
            )
        if self.session_cookie_same_site == "none" and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be enabled when SameSite=None")
        if self.session_cookie_same_site == "none" and not self.csrf_protection_enabled:
            raise ValueError(
                "CSRF_PROTECTION_ENABLED must be enabled when SameSite=None"
            )
        return self


class EngramOAuthSettings(EngramBaseSchema):
    enabled: bool = Field(default=True, alias="ENABLED")
    issuer: str = Field(default="http://localhost:8000", alias="ISSUER")
    public_base_url: str = Field(
        default="http://localhost:8000", alias="PUBLIC_BASE_URL"
    )
    mcp_resource_url: str = Field(
        default="http://localhost:8000/mcp/http", alias="MCP_RESOURCE_URL"
    )
    authorization_endpoint_path: str = Field(
        default="/oauth/authorize", alias="AUTHORIZATION_ENDPOINT_PATH"
    )
    token_endpoint_path: str = Field(
        default="/oauth/token", alias="TOKEN_ENDPOINT_PATH"
    )
    registration_endpoint_path: str = Field(
        default="/oauth/register", alias="REGISTRATION_ENDPOINT_PATH"
    )
    protected_resource_metadata_path: str = Field(
        default="/.well-known/oauth-protected-resource",
        alias="PROTECTED_RESOURCE_METADATA_PATH",
    )
    authorization_server_metadata_path: str = Field(
        default="/.well-known/oauth-authorization-server",
        alias="AUTHORIZATION_SERVER_METADATA_PATH",
    )
    authorization_code_ttl_seconds: int = Field(
        default=300, alias="AUTHORIZATION_CODE_TTL_SECONDS", ge=1
    )
    default_mcp_access_token_ttl_seconds: int = Field(
        default=7776000, alias="DEFAULT_MCP_ACCESS_TOKEN_TTL_SECONDS", ge=1
    )
    allowed_redirect_uri_origins: list[str] = Field(
        default_factory=lambda: ["https://claude.ai"],
        alias="ALLOWED_REDIRECT_URI_ORIGINS",
    )
    allow_dynamic_client_registration: bool = Field(
        default=True, alias="ALLOW_DYNAMIC_CLIENT_REGISTRATION"
    )
    auto_approve_trusted_clients: bool = Field(
        default=True, alias="AUTO_APPROVE_TRUSTED_CLIENTS"
    )
    trusted_client_names: list[str] = Field(
        default_factory=lambda: ["Claude Desktop", "Claude Code"],
        alias="TRUSTED_CLIENT_NAMES",
    )
    authorization_code_hash_secret: str = Field(
        default="", alias="AUTHORIZATION_CODE_HASH_SECRET"
    )

    @field_validator(
        "authorization_endpoint_path",
        "token_endpoint_path",
        "registration_endpoint_path",
        "protected_resource_metadata_path",
        "authorization_server_metadata_path",
    )
    @classmethod
    def normalize_path(cls, value: str) -> str:
        normalized_value = (value or "").strip()
        if not normalized_value:
            raise ValueError("OAuth endpoint paths must not be empty")
        return (
            normalized_value
            if normalized_value.startswith("/")
            else f"/{normalized_value}"
        )

    @field_validator("issuer", "public_base_url", "mcp_resource_url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        normalized_value = (value or "").strip().rstrip("/")
        if not normalized_value:
            raise ValueError("OAuth URLs must not be empty")
        return normalized_value

    @field_validator("allowed_redirect_uri_origins")
    @classmethod
    def normalize_redirect_origins(cls, values: list[str]) -> list[str]:
        normalized_values = []
        for value in values:
            normalized_value = str(value or "").strip().rstrip("/")
            if normalized_value and normalized_value not in normalized_values:
                normalized_values.append(normalized_value)
        return normalized_values


class MemoryProcessingSettings(EngramBaseSchema):
    enabled: bool = Field(default=False, alias="ENABLED")
    extraction_model: str = Field(default="", alias="EXTRACTION_MODEL")
    auto_tagging_enabled: bool = Field(default=False, alias="AUTO_TAGGING_ENABLED")
    secret_detection_enabled: bool = Field(
        default=True, alias="SECRET_DETECTION_ENABLED"
    )


class EmbeddingSettings(EngramBaseSchema):
    enabled: bool = Field(default=False, alias="ENABLED")
    model: str = Field(default="", alias="MODEL")
    fallback_model: str = Field(default="", alias="FALLBACK_MODEL")
    dimensions: int | None = Field(default=None, alias="DIMENSIONS")
    batch_size: int = Field(default=64, alias="BATCH_SIZE", ge=1)
    instrument: bool = Field(default=True, alias="INSTRUMENT")


class QdrantSettings(EngramBaseSchema):
    enabled: bool = Field(default=False, alias="ENABLED")
    url: str = Field(default="http://localhost:6333", alias="URL")
    api_key: str = Field(default="", alias="API_KEY")
    collection_strategy: str = Field(
        default="per_environment", alias="COLLECTION_STRATEGY"
    )
    collection_prefix: str = Field(default="engram_memories", alias="COLLECTION_PREFIX")
    collection: str = Field(default="engram_memories_dev", alias="COLLECTION")


class CorsSettings(EngramBaseSchema):
    allowed_origins: list[str] = Field(default_factory=list, alias="ALLOWED_ORIGINS")
    allow_credentials: bool = Field(default=True, alias="ALLOW_CREDENTIALS")
    allow_methods: list[str] = Field(
        default_factory=lambda: ["*"], alias="ALLOW_METHODS"
    )
    allow_headers: list[str] = Field(
        default_factory=lambda: ["*"], alias="ALLOW_HEADERS"
    )


class EngramConfigService:
    """Small boundary around raw Vortex config access."""

    @classmethod
    def raw_config(cls) -> dict[str, Any]:
        return CONFIG.config

    @classmethod
    def section(cls, section_name: str) -> dict[str, Any]:
        section = cls.raw_config().get(section_name, {})
        if isinstance(section, dict):
            return section
        return {}

    @classmethod
    def engram(cls) -> EngramSettings:
        return EngramSettings.model_validate(cls.section("ENGRAM"))

    @classmethod
    def auth(cls) -> EngramAuthSettings:
        return EngramAuthSettings.model_validate(cls.section("ENGRAM_AUTH"))

    @classmethod
    def oauth(cls) -> EngramOAuthSettings:
        return EngramOAuthSettings.model_validate(cls.section("ENGRAM_OAUTH"))

    @classmethod
    def memory_processing(cls) -> MemoryProcessingSettings:
        return MemoryProcessingSettings.model_validate(cls.section("MEMORY_PROCESSING"))

    @classmethod
    def embeddings(cls) -> EmbeddingSettings:
        return EmbeddingSettings.model_validate(cls.section("EMBEDDINGS"))

    @classmethod
    def qdrant(cls) -> QdrantSettings:
        return QdrantSettings.model_validate(cls.section("QDRANT"))

    @classmethod
    def cors(cls) -> CorsSettings:
        return CorsSettings.model_validate(cls.section("CORS"))
