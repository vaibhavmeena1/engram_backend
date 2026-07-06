-- migrate:up

CREATE TABLE IF NOT EXISTS engram_user_identities (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id UUID NOT NULL REFERENCES engram_users (id) ON DELETE CASCADE,
    provider VARCHAR(64) NOT NULL,
    provider_subject VARCHAR(255) NOT NULL,
    email_at_login VARCHAR(320) NOT NULL,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    hosted_domain VARCHAR(255),
    profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT engram_user_identities_provider_subject_unique UNIQUE (provider, provider_subject)
);

CREATE TABLE IF NOT EXISTS engram_sessions (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id UUID NOT NULL REFERENCES engram_users (id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES engram_organizations (id) ON DELETE CASCADE,
    client_type VARCHAR(32) NOT NULL DEFAULT 'web',
    jwt_id_hash VARCHAR(128) NOT NULL UNIQUE,
    last_seen_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    revoked_reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS engram_sessions_user_org_revoked_idx
    ON engram_sessions (user_id, org_id, revoked_at);

CREATE INDEX IF NOT EXISTS engram_sessions_expires_at_idx
    ON engram_sessions (expires_at);

CREATE TABLE IF NOT EXISTS engram_personal_access_tokens (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id UUID NOT NULL REFERENCES engram_users (id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES engram_organizations (id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(64) NOT NULL,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    client_type VARCHAR(32) NOT NULL DEFAULT 'mcp',
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revoked_reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS engram_personal_access_tokens_key_prefix_idx
    ON engram_personal_access_tokens (key_prefix);

CREATE INDEX IF NOT EXISTS engram_personal_access_tokens_user_org_revoked_idx
    ON engram_personal_access_tokens (user_id, org_id, revoked_at);

CREATE INDEX IF NOT EXISTS engram_personal_access_tokens_expires_at_idx
    ON engram_personal_access_tokens (expires_at);

-- migrate:down

DROP TABLE IF EXISTS engram_personal_access_tokens;
DROP TABLE IF EXISTS engram_sessions;
DROP TABLE IF EXISTS engram_user_identities;