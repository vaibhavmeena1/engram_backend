-- migrate:up

CREATE TABLE IF NOT EXISTS engram_oauth_clients (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    client_id VARCHAR(255) NOT NULL UNIQUE,
    client_name VARCHAR(255),
    redirect_uris JSONB NOT NULL DEFAULT '[]'::jsonb,
    grant_types JSONB NOT NULL DEFAULT '["authorization_code"]'::jsonb,
    response_types JSONB NOT NULL DEFAULT '["code"]'::jsonb,
    token_endpoint_auth_method VARCHAR(64) NOT NULL DEFAULT 'none',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_seen_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS engram_oauth_clients_client_id_idx
    ON engram_oauth_clients (client_id);

CREATE TABLE IF NOT EXISTS engram_oauth_authorization_codes (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    code_hash VARCHAR(128) NOT NULL UNIQUE,
    client_id VARCHAR(255) NOT NULL,
    redirect_uri TEXT NOT NULL,
    scope VARCHAR(255) NOT NULL DEFAULT 'mcp',
    code_challenge VARCHAR(255) NOT NULL,
    code_challenge_method VARCHAR(16) NOT NULL DEFAULT 'S256',
    resource TEXT,
    user_id UUID NOT NULL REFERENCES engram_users (id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES engram_organizations (id) ON DELETE CASCADE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS engram_oauth_authorization_codes_code_hash_idx
    ON engram_oauth_authorization_codes (code_hash);

CREATE INDEX IF NOT EXISTS engram_oauth_authorization_codes_expires_at_idx
    ON engram_oauth_authorization_codes (expires_at);

CREATE INDEX IF NOT EXISTS engram_oauth_authorization_codes_used_at_idx
    ON engram_oauth_authorization_codes (used_at);

CREATE INDEX IF NOT EXISTS engram_oauth_authorization_codes_user_org_idx
    ON engram_oauth_authorization_codes (user_id, org_id);

-- migrate:down

DROP TABLE IF EXISTS engram_oauth_authorization_codes;
DROP TABLE IF EXISTS engram_oauth_clients;