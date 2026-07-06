"""Shared test fixtures for Engram backend tests."""

from collections.abc import AsyncIterator, Iterator
from copy import deepcopy

import pytest
from tortoise import Tortoise
from vortex import CONFIG


TEST_CONFIG = {
    "DEV_MODE": True,
    "CORS": {
        "ALLOWED_ORIGINS": ["http://localhost:5173"],
        "ALLOW_CREDENTIALS": True,
        "ALLOW_METHODS": ["*"],
        "ALLOW_HEADERS": ["*"],
    },
    "ENGRAM": {
        "MCP_SERVER_NAME": "engram-mcp-test",
        "DEFAULT_RETRIEVAL_MODE": "lexical",
        "MAX_SEARCH_RESULTS": 20,
        "REQUIRE_REVIEW_FOR_REPO_MEMORY": True,
        "REQUIRE_REVIEW_FOR_ORG_MEMORY": True,
        "ALLOW_USER_MEMORY_AUTO_APPROVE": True,
    },
    "ENGRAM_AUTH": {
        "MODE": "google_workspace_oidc",
        "PHASE1_HEADER_ENABLED": False,
        "ALLOWED_EMAIL_DOMAINS": ["1mg.com"],
        "GOOGLE_HOSTED_DOMAIN": "1mg.com",
        "DEFAULT_ORG_SLUG": "tata1mg",
        "ADMIN_EMAILS": ["admin@1mg.com"],
        "AUTO_PROVISION_USERS": True,
        "GOOGLE_CLIENT_ID": "test-google-client-id",
        "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
        "GOOGLE_AUTHORIZATION_ENDPOINT": "https://accounts.google.com/o/oauth2/v2/auth",
        "GOOGLE_TOKEN_ENDPOINT": "https://oauth2.googleapis.com/token",
        "GOOGLE_JWKS_URI": "https://www.googleapis.com/oauth2/v3/certs",
        "GOOGLE_REDIRECT_URI": "http://localhost:8000/auth/google/callback",
        "JWT_ISSUER": "engram-backend-test",
        "JWT_AUDIENCE": "engram-clients-test",
        "JWT_SIGNING_ALGORITHM": "HS256",
        "JWT_SIGNING_KEY": "test-jwt-signing-key-with-enough-entropy",
        "ACCESS_TOKEN_TTL_SECONDS": 86400,
        "WEB_SESSION_TTL_SECONDS": 86400,
        "SESSION_COOKIE_NAME": "engram_session",
        "SESSION_COOKIE_DOMAIN": "",
        "SESSION_COOKIE_SECURE": False,
        "SESSION_COOKIE_HTTP_ONLY": True,
        "SESSION_COOKIE_SAME_SITE": "lax",
        "CSRF_PROTECTION_ENABLED": False,
        "CSRF_COOKIE_NAME": "engram_csrf",
        "CSRF_HEADER_NAME": "x-engram-csrf",
        "DASHBOARD_LOGIN_SUCCESS_URL": "http://localhost:5173/",
        "DASHBOARD_LOGIN_FAILURE_URL": "http://localhost:5173/login?error=auth_failed",
        "DASHBOARD_ALLOWED_RETURN_TO_ORIGINS": ["http://localhost:5173"],
        "PERSONAL_ACCESS_TOKENS_ENABLED": True,
        "PERSONAL_ACCESS_TOKEN_PREFIX": "engpat",
        "PERSONAL_ACCESS_TOKEN_DEFAULT_TTL_SECONDS": 7776000,
        "PERSONAL_ACCESS_TOKEN_MAX_TTL_SECONDS": 15552000,
        "PERSONAL_ACCESS_TOKEN_HASH_SECRET": "test-pat-hash-secret-with-enough-entropy",
    },
    "MEMORY_PROCESSING": {
        "ENABLED": False,
        "EXTRACTION_MODEL": "",
        "AUTO_TAGGING_ENABLED": False,
        "SECRET_DETECTION_ENABLED": True,
    },
    "EMBEDDINGS": {
        "ENABLED": False,
        "MODEL": "",
        "FALLBACK_MODEL": "",
        "DIMENSIONS": None,
        "BATCH_SIZE": 64,
        "INSTRUMENT": True,
    },
    "QDRANT": {
        "ENABLED": False,
        "URL": "",
        "API_KEY": "",
        "COLLECTION_STRATEGY": "per_environment",
        "COLLECTION_PREFIX": "engram_memories",
        "COLLECTION": "engram_memories_test",
    },
    "OPENAI": {"API_KEY": ""},
}


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def test_config() -> Iterator[dict]:
    original_config = deepcopy(CONFIG.config)
    CONFIG.config.clear()
    CONFIG.config.update(deepcopy(TEST_CONFIG))
    try:
        yield CONFIG.config
    finally:
        CONFIG.config.clear()
        CONFIG.config.update(original_config)


@pytest.fixture()
async def test_db() -> AsyncIterator[None]:
    await Tortoise.init(
        config={
            "connections": {"default": "sqlite://:memory:"},
            "apps": {
                "dao": {
                    "models": [
                        "app.models.identity",
                        "app.models.repository",
                        "app.models.memory",
                        "app.models.review",
                        "app.models.audit",
                    ],
                    "default_connection": "default",
                }
            },
        }
    )
    await Tortoise.generate_schemas(safe=True)
    try:
        yield
    finally:
        await Tortoise.close_connections()
