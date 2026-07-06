-- migrate:up

ALTER TABLE engram_memory_access_logs
    ADD COLUMN IF NOT EXISTS auth_method VARCHAR(64),
    ADD COLUMN IF NOT EXISTS client_type VARCHAR(32),
    ADD COLUMN IF NOT EXISTS session_id UUID,
    ADD COLUMN IF NOT EXISTS personal_access_token_id UUID;

CREATE INDEX IF NOT EXISTS engram_memory_access_logs_auth_method_idx
    ON engram_memory_access_logs (auth_method);

CREATE INDEX IF NOT EXISTS engram_memory_access_logs_client_type_idx
    ON engram_memory_access_logs (client_type);

CREATE INDEX IF NOT EXISTS engram_memory_access_logs_session_id_idx
    ON engram_memory_access_logs (session_id);

CREATE INDEX IF NOT EXISTS engram_memory_access_logs_pat_id_idx
    ON engram_memory_access_logs (personal_access_token_id);

-- migrate:down

DROP INDEX IF EXISTS engram_memory_access_logs_pat_id_idx;
DROP INDEX IF EXISTS engram_memory_access_logs_session_id_idx;
DROP INDEX IF EXISTS engram_memory_access_logs_client_type_idx;
DROP INDEX IF EXISTS engram_memory_access_logs_auth_method_idx;

ALTER TABLE engram_memory_access_logs
    DROP COLUMN IF EXISTS personal_access_token_id,
    DROP COLUMN IF EXISTS session_id,
    DROP COLUMN IF EXISTS client_type,
    DROP COLUMN IF EXISTS auth_method;