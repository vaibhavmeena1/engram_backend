-- migrate:up

ALTER TABLE engram_memory_facts
    ADD COLUMN IF NOT EXISTS rationale TEXT;

ALTER TABLE engram_memory_fact_versions
    ADD COLUMN IF NOT EXISTS rationale TEXT;

ALTER TABLE engram_memory_proposals
    ADD COLUMN IF NOT EXISTS proposed_rationale TEXT;

-- migrate:down

ALTER TABLE engram_memory_proposals
    DROP COLUMN IF EXISTS proposed_rationale;

ALTER TABLE engram_memory_fact_versions
    DROP COLUMN IF EXISTS rationale;

ALTER TABLE engram_memory_facts
    DROP COLUMN IF EXISTS rationale;