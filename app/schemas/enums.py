"""Shared enums used by schemas, services, and ORM models."""

from enum import Enum


class ScopeType(str, Enum):
    USER = "user"
    REPO = "repo"
    ORG = "org"


class MemoryStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    DELETED = "deleted"
    SUPERSEDED = "superseded"


class MemoryListSection(str, Enum):
    MY = "my"
    ALL = "all"
    REPO = "repo"
    ORG = "org"


class ProposalType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"


class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    CANCELLED = "cancelled"


class MemorySource(str, Enum):
    MCP = "mcp"
    DASHBOARD = "dashboard"
    IMPORT = "import"
    SYSTEM = "system"
    HOOK = "hook"


class RetrievalMode(str, Enum):
    AUTO = "auto"
    LEXICAL = "lexical"
    ALL_SCOPED = "all_scoped"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class AuthMethod(str, Enum):
    PHASE1_HEADER = "phase1_header"
    OAUTH_WEB_COOKIE = "oauth_web_cookie"
    PERSONAL_ACCESS_TOKEN = "personal_access_token"


class AuthClientType(str, Enum):
    WEB = "web"
    MCP = "mcp"
    CLI = "cli"
    AUTOMATION = "automation"
