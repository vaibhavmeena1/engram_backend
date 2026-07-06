\restrict dbmate

-- Dumped from database version 18.4 (Postgres.app)
-- Dumped by pg_dump version 18.3 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: engram_memory_access_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_memory_access_logs (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    action character varying(64) NOT NULL,
    client_name character varying(120),
    request_id character varying(120),
    query_hash character varying(128),
    returned_memory_ids jsonb NOT NULL,
    scope_filters jsonb NOT NULL,
    scores jsonb NOT NULL,
    metadata jsonb NOT NULL,
    actor_user_id uuid,
    memory_fact_id uuid,
    org_id uuid,
    proposal_id uuid,
    repository_id uuid,
    auth_method character varying(64),
    client_type character varying(32),
    session_id uuid,
    personal_access_token_id uuid
);


--
-- Name: engram_memory_fact_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_memory_fact_tags (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    metadata jsonb NOT NULL,
    fact_id uuid NOT NULL,
    org_id uuid NOT NULL,
    tag_id uuid NOT NULL
);


--
-- Name: engram_memory_fact_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_memory_fact_versions (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    version_number integer NOT NULL,
    status character varying(32) NOT NULL,
    content text NOT NULL,
    summary text,
    content_hash character varying(128) NOT NULL,
    change_reason text,
    metadata jsonb NOT NULL,
    changed_by_id uuid,
    fact_id uuid NOT NULL,
    proposal_id uuid
);


--
-- Name: COLUMN engram_memory_fact_versions.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.engram_memory_fact_versions.status IS 'PENDING_REVIEW: pending_review\nAPPROVED: approved\nREJECTED: rejected\nARCHIVED: archived\nDELETED: deleted\nSUPERSEDED: superseded';


--
-- Name: engram_memory_facts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_memory_facts (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    scope_type character varying(16) NOT NULL,
    scope_id uuid NOT NULL,
    status character varying(32) DEFAULT 'pending_review'::character varying NOT NULL,
    content text NOT NULL,
    summary text,
    content_hash character varying(128) NOT NULL,
    source character varying(32) DEFAULT 'system'::character varying NOT NULL,
    source_ref character varying(255),
    metadata jsonb NOT NULL,
    approved_at timestamp with time zone,
    approved_by_id uuid,
    created_by_id uuid,
    org_id uuid NOT NULL,
    owner_user_id uuid,
    repository_id uuid,
    updated_by_id uuid
);


--
-- Name: COLUMN engram_memory_facts.scope_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.engram_memory_facts.scope_type IS 'USER: user\nREPO: repo\nORG: org';


--
-- Name: COLUMN engram_memory_facts.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.engram_memory_facts.status IS 'PENDING_REVIEW: pending_review\nAPPROVED: approved\nREJECTED: rejected\nARCHIVED: archived\nDELETED: deleted\nSUPERSEDED: superseded';


--
-- Name: COLUMN engram_memory_facts.source; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.engram_memory_facts.source IS 'MCP: mcp\nDASHBOARD: dashboard\nIMPORT: import\nSYSTEM: system\nHOOK: hook';


--
-- Name: engram_memory_observations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_memory_observations (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    scope_type character varying(16) NOT NULL,
    scope_id uuid NOT NULL,
    raw_content text NOT NULL,
    source character varying(32) DEFAULT 'mcp'::character varying NOT NULL,
    source_metadata jsonb NOT NULL,
    contains_possible_secret boolean DEFAULT false CONSTRAINT engram_memory_observat_contains_possible_secret_not_null NOT NULL,
    metadata jsonb NOT NULL,
    actor_user_id uuid,
    org_id uuid NOT NULL,
    repository_id uuid
);


--
-- Name: COLUMN engram_memory_observations.scope_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.engram_memory_observations.scope_type IS 'USER: user\nREPO: repo\nORG: org';


--
-- Name: COLUMN engram_memory_observations.source; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.engram_memory_observations.source IS 'MCP: mcp\nDASHBOARD: dashboard\nIMPORT: import\nSYSTEM: system\nHOOK: hook';


--
-- Name: engram_memory_proposals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_memory_proposals (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    scope_type character varying(16) NOT NULL,
    scope_id uuid NOT NULL,
    proposal_type character varying(16) NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    proposed_content text,
    proposed_summary text,
    proposed_metadata jsonb NOT NULL,
    content_hash character varying(128),
    contains_possible_secret boolean DEFAULT false CONSTRAINT engram_memory_proposal_contains_possible_secret_not_null NOT NULL,
    source character varying(32) DEFAULT 'mcp'::character varying NOT NULL,
    idempotency_key character varying(255),
    review_notes text,
    reviewed_at timestamp with time zone,
    applied_at timestamp with time zone,
    metadata jsonb NOT NULL,
    created_by_id uuid,
    fact_id uuid,
    observation_id uuid,
    org_id uuid NOT NULL,
    repository_id uuid,
    reviewed_by_id uuid
);


--
-- Name: COLUMN engram_memory_proposals.scope_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.engram_memory_proposals.scope_type IS 'USER: user\nREPO: repo\nORG: org';


--
-- Name: COLUMN engram_memory_proposals.proposal_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.engram_memory_proposals.proposal_type IS 'CREATE: create\nUPDATE: update\nDELETE: delete\nMERGE: merge';


--
-- Name: COLUMN engram_memory_proposals.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.engram_memory_proposals.status IS 'PENDING: pending\nAPPROVED: approved\nREJECTED: rejected\nAPPLIED: applied\nCANCELLED: cancelled';


--
-- Name: COLUMN engram_memory_proposals.source; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.engram_memory_proposals.source IS 'MCP: mcp\nDASHBOARD: dashboard\nIMPORT: import\nSYSTEM: system\nHOOK: hook';


--
-- Name: engram_organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_organizations (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(120) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb NOT NULL
);


--
-- Name: engram_personal_access_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_personal_access_tokens (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    name character varying(255) NOT NULL,
    key_prefix character varying(64) NOT NULL,
    token_hash character varying(128) NOT NULL,
    client_type character varying(32) DEFAULT 'mcp'::character varying NOT NULL,
    scopes jsonb NOT NULL,
    last_used_at timestamp with time zone,
    expires_at timestamp with time zone,
    revoked_at timestamp with time zone,
    revoked_reason text,
    metadata jsonb NOT NULL,
    org_id uuid NOT NULL,
    user_id uuid NOT NULL
);


--
-- Name: engram_repositories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_repositories (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    provider character varying(64) NOT NULL,
    host character varying(255) NOT NULL,
    workspace character varying(255) NOT NULL,
    repo_slug character varying(255) NOT NULL,
    repository_key character varying(512) NOT NULL,
    display_name character varying(255),
    canonical_remote_url character varying(1024),
    resolver_source character varying(64) NOT NULL,
    resolver_confidence double precision DEFAULT 1 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb NOT NULL,
    org_id uuid NOT NULL
);


--
-- Name: engram_repository_aliases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_repository_aliases (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    alias_key character varying(512) NOT NULL,
    alias_remote_url character varying(1024),
    source character varying(64) NOT NULL,
    metadata jsonb NOT NULL,
    org_id uuid NOT NULL,
    repository_id uuid NOT NULL
);


--
-- Name: engram_role_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_role_assignments (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    scope_type character varying(32),
    scope_id uuid,
    metadata jsonb NOT NULL,
    assigned_by_id uuid,
    org_id uuid NOT NULL,
    role_id uuid NOT NULL,
    user_id uuid NOT NULL
);


--
-- Name: engram_roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_roles (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    slug character varying(120) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    permissions jsonb NOT NULL,
    is_system boolean DEFAULT false NOT NULL,
    metadata jsonb NOT NULL,
    org_id uuid NOT NULL
);


--
-- Name: engram_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_sessions (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    client_type character varying(32) DEFAULT 'web'::character varying NOT NULL,
    jwt_id_hash character varying(128) NOT NULL,
    last_seen_at timestamp with time zone,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    revoked_reason text,
    metadata jsonb NOT NULL,
    org_id uuid NOT NULL,
    user_id uuid NOT NULL
);


--
-- Name: engram_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_tags (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    slug character varying(120) NOT NULL,
    label character varying(255) NOT NULL,
    description text,
    color character varying(32),
    metadata jsonb NOT NULL,
    org_id uuid NOT NULL
);


--
-- Name: engram_user_identities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_user_identities (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    provider character varying(64) NOT NULL,
    provider_subject character varying(255) NOT NULL,
    email_at_login character varying(320) NOT NULL,
    email_verified boolean DEFAULT false NOT NULL,
    hosted_domain character varying(255),
    profile jsonb NOT NULL,
    user_id uuid NOT NULL
);


--
-- Name: engram_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.engram_users (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    email character varying(320) NOT NULL,
    display_name character varying(255),
    is_active boolean DEFAULT true NOT NULL,
    metadata jsonb NOT NULL
);


--
-- Name: animus_agent_instances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.animus_agent_instances (
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    agent_instance_id uuid NOT NULL,
    session_id character varying(255) NOT NULL,
    agent_id uuid,
    agent_slug character varying(255),
    status character varying(9) DEFAULT 'active'::character varying NOT NULL,
    user_visible boolean DEFAULT true NOT NULL,
    visibility_scope character varying(12) DEFAULT 'full'::character varying NOT NULL,
    result jsonb,
    error text,
    metadata jsonb
);


--
-- Name: TABLE animus_agent_instances; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.animus_agent_instances IS 'Agent instance model representing a runtime execution of an agent.';


--
-- Name: COLUMN animus_agent_instances.agent_instance_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_instances.agent_instance_id IS 'Unique agent instance identifier';


--
-- Name: COLUMN animus_agent_instances.session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_instances.session_id IS 'Session this agent instance belongs to';


--
-- Name: COLUMN animus_agent_instances.agent_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_instances.agent_id IS 'Agent template this instance is based on';


--
-- Name: COLUMN animus_agent_instances.agent_slug; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_instances.agent_slug IS 'Agent slug for quick lookup (denormalized)';


--
-- Name: COLUMN animus_agent_instances.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_instances.status IS 'Current agent status';


--
-- Name: COLUMN animus_agent_instances.user_visible; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_instances.user_visible IS 'Whether this agent''s activities are visible to the user';


--
-- Name: COLUMN animus_agent_instances.visibility_scope; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_instances.visibility_scope IS 'Scope of visibility for agent activities';


--
-- Name: COLUMN animus_agent_instances.result; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_instances.result IS 'Final result/output from the agent instance';


--
-- Name: COLUMN animus_agent_instances.error; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_instances.error IS 'Error message if agent failed';


--
-- Name: COLUMN animus_agent_instances.metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_instances.metadata IS 'Additional metadata for the agent instance';


--
-- Name: animus_agent_message_map; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.animus_agent_message_map (
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    id uuid NOT NULL,
    message_history_thread_id uuid NOT NULL,
    agent_instance_id uuid NOT NULL,
    message_id uuid NOT NULL
);


--
-- Name: TABLE animus_agent_message_map; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.animus_agent_message_map IS 'Agent message mapping model for linking messages to threads and agents.';


--
-- Name: COLUMN animus_agent_message_map.id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_message_map.id IS 'Unique mapping identifier';


--
-- Name: COLUMN animus_agent_message_map.message_history_thread_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_message_map.message_history_thread_id IS 'Thread this message belongs to';


--
-- Name: COLUMN animus_agent_message_map.agent_instance_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_message_map.agent_instance_id IS 'Agent instance that has access to this message';


--
-- Name: COLUMN animus_agent_message_map.message_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_message_map.message_id IS 'Message that is shared with the agent';


--
-- Name: animus_agent_models; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.animus_agent_models (
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    agent_model_id uuid NOT NULL,
    agent_id uuid NOT NULL,
    model_provider character varying(100) NOT NULL,
    model_name character varying(255) NOT NULL,
    model_variant character varying(100) DEFAULT 'default'::character varying NOT NULL,
    priority integer DEFAULT 0 NOT NULL,
    instructions_override text,
    temperature double precision,
    max_tokens integer,
    config jsonb,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: TABLE animus_agent_models; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.animus_agent_models IS 'Agent model configuration for specific LLM providers and model variants.';


--
-- Name: COLUMN animus_agent_models.agent_model_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_models.agent_model_id IS 'Unique agent model config identifier';


--
-- Name: COLUMN animus_agent_models.agent_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_models.agent_id IS 'Agent this model config belongs to';


--
-- Name: COLUMN animus_agent_models.model_provider; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_models.model_provider IS 'Model provider (openai, anthropic, google, etc.)';


--
-- Name: COLUMN animus_agent_models.model_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_models.model_name IS 'Model name (gpt-4, claude-3-opus, etc.)';


--
-- Name: COLUMN animus_agent_models.model_variant; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_models.model_variant IS 'Variant identifier (fast, accurate, default)';


--
-- Name: COLUMN animus_agent_models.priority; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_models.priority IS 'Priority for fallback chain (0=highest priority, use first)';


--
-- Name: COLUMN animus_agent_models.instructions_override; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_models.instructions_override IS 'Model-specific instructions override (if different from agent default)';


--
-- Name: COLUMN animus_agent_models.temperature; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_models.temperature IS 'Model-specific temperature override';


--
-- Name: COLUMN animus_agent_models.max_tokens; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_models.max_tokens IS 'Model-specific max tokens override';


--
-- Name: COLUMN animus_agent_models.config; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_models.config IS 'Provider-specific configuration (API keys, endpoints, advanced params)';


--
-- Name: COLUMN animus_agent_models.is_active; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agent_models.is_active IS 'Whether this model config is currently active';


--
-- Name: animus_agents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.animus_agents (
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    agent_id uuid NOT NULL,
    agent_name character varying(255) NOT NULL,
    description text,
    instructions text,
    tools jsonb,
    temperature double precision DEFAULT 0.7 NOT NULL,
    max_tokens integer,
    config jsonb
);


--
-- Name: TABLE animus_agents; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.animus_agents IS 'Agent model representing an agent template/definition.';


--
-- Name: COLUMN animus_agents.agent_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agents.agent_id IS 'Unique agent identifier';


--
-- Name: COLUMN animus_agents.agent_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agents.agent_name IS 'Unique agent name';


--
-- Name: COLUMN animus_agents.description; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agents.description IS 'Description of the agent''s purpose and capabilities';


--
-- Name: COLUMN animus_agents.instructions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agents.instructions IS 'Default instructions for the agent';


--
-- Name: COLUMN animus_agents.tools; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agents.tools IS 'List of tool definitions available to this agent (tool names, configs)';


--
-- Name: COLUMN animus_agents.temperature; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agents.temperature IS 'Default temperature for model inference';


--
-- Name: COLUMN animus_agents.max_tokens; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agents.max_tokens IS 'Default max tokens for model responses';


--
-- Name: COLUMN animus_agents.config; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_agents.config IS 'Additional agent configuration (retries, timeouts, custom params)';


--
-- Name: animus_handoffs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.animus_handoffs (
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    handoff_id uuid NOT NULL,
    session_id character varying(255) NOT NULL,
    from_agent_instance_id uuid NOT NULL,
    to_agent_instance_id uuid NOT NULL,
    handoff_strategy character varying(20) NOT NULL,
    handoff_reason text,
    strategy_metadata jsonb,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE animus_handoffs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.animus_handoffs IS 'Handoff model for tracking agent-to-agent transitions.';


--
-- Name: COLUMN animus_handoffs.handoff_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_handoffs.handoff_id IS 'Unique handoff identifier';


--
-- Name: COLUMN animus_handoffs.session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_handoffs.session_id IS 'Session this handoff belongs to';


--
-- Name: COLUMN animus_handoffs.from_agent_instance_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_handoffs.from_agent_instance_id IS 'Agent instance initiating the handoff';


--
-- Name: COLUMN animus_handoffs.to_agent_instance_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_handoffs.to_agent_instance_id IS 'Agent instance receiving the handoff';


--
-- Name: COLUMN animus_handoffs.handoff_strategy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_handoffs.handoff_strategy IS 'Strategy used for the handoff';


--
-- Name: COLUMN animus_handoffs.handoff_reason; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_handoffs.handoff_reason IS 'Reason or context for the handoff';


--
-- Name: COLUMN animus_handoffs.strategy_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_handoffs.strategy_metadata IS 'Strategy-specific metadata (tool name, routing logic, conditions)';


--
-- Name: COLUMN animus_handoffs."timestamp"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_handoffs."timestamp" IS 'Handoff timestamp';


--
-- Name: animus_history_compactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.animus_history_compactions (
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    compaction_id uuid NOT NULL,
    thread_id uuid NOT NULL,
    last_compacted_message_id uuid NOT NULL,
    summary text NOT NULL,
    original_token_count integer NOT NULL,
    compacted_token_count integer NOT NULL,
    compaction_model character varying(255) NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL
);


--
-- Name: TABLE animus_history_compactions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.animus_history_compactions IS 'History compaction model representing summarized message history.';


--
-- Name: COLUMN animus_history_compactions.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_history_compactions.created_at IS 'Compaction creation timestamp';


--
-- Name: COLUMN animus_history_compactions.updated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_history_compactions.updated_at IS 'Last update timestamp';


--
-- Name: COLUMN animus_history_compactions.compaction_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_history_compactions.compaction_id IS 'Unique compaction identifier';


--
-- Name: COLUMN animus_history_compactions.thread_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_history_compactions.thread_id IS 'Message history thread this compaction belongs to';


--
-- Name: COLUMN animus_history_compactions.last_compacted_message_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_history_compactions.last_compacted_message_id IS 'Last message ID included in this compaction';


--
-- Name: COLUMN animus_history_compactions.summary; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_history_compactions.summary IS 'Summarized content of compacted messages';


--
-- Name: COLUMN animus_history_compactions.original_token_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_history_compactions.original_token_count IS 'Approximate token count before compaction';


--
-- Name: COLUMN animus_history_compactions.compacted_token_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_history_compactions.compacted_token_count IS 'Approximate token count after compaction';


--
-- Name: COLUMN animus_history_compactions.compaction_model; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_history_compactions.compaction_model IS 'Model used for compaction (e.g., ''openai:gpt-4o-mini'')';


--
-- Name: COLUMN animus_history_compactions.is_deleted; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_history_compactions.is_deleted IS 'Soft deletion flag - marks compaction as superseded by a newer one';


--
-- Name: animus_llm_calls; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.animus_llm_calls (
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    llm_call_id uuid NOT NULL,
    message_id uuid,
    session_id character varying(255) NOT NULL,
    agent_instance_id uuid NOT NULL,
    run_id character varying(255),
    model_name character varying(255),
    provider_name character varying(100),
    provider_url character varying(500),
    provider_response_id character varying(255),
    finish_reason character varying(50),
    usage jsonb,
    provider_details jsonb,
    metadata jsonb,
    messages_sent jsonb,
    "timestamp" timestamp without time zone NOT NULL,
    is_cancelled boolean DEFAULT false NOT NULL,
    cancellation_reason character varying(255),
    cancelled_at timestamp with time zone
);


--
-- Name: TABLE animus_llm_calls; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.animus_llm_calls IS 'LLM call model for tracking API calls and responses.';


--
-- Name: COLUMN animus_llm_calls.llm_call_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.llm_call_id IS 'Unique LLM call identifier';


--
-- Name: COLUMN animus_llm_calls.message_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.message_id IS 'Associated message (response) for this LLM call';


--
-- Name: COLUMN animus_llm_calls.session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.session_id IS 'Session this LLM call belongs to';


--
-- Name: COLUMN animus_llm_calls.agent_instance_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.agent_instance_id IS 'Agent instance that made this LLM call';


--
-- Name: COLUMN animus_llm_calls.run_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.run_id IS 'Pydantic AI run ID';


--
-- Name: COLUMN animus_llm_calls.model_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.model_name IS 'Model name (e.g., gpt-4o-mini-2024-07-18)';


--
-- Name: COLUMN animus_llm_calls.provider_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.provider_name IS 'Provider name (e.g., openai, litellm)';


--
-- Name: COLUMN animus_llm_calls.provider_url; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.provider_url IS 'Provider API URL';


--
-- Name: COLUMN animus_llm_calls.provider_response_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.provider_response_id IS 'Provider''s response ID (e.g., chatcmpl-xxx)';


--
-- Name: COLUMN animus_llm_calls.finish_reason; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.finish_reason IS 'Completion finish reason (stop, length, etc.)';


--
-- Name: COLUMN animus_llm_calls.usage; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.usage IS 'Complete usage data with token counts and details';


--
-- Name: COLUMN animus_llm_calls.provider_details; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.provider_details IS 'Provider-specific response details';


--
-- Name: COLUMN animus_llm_calls.metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.metadata IS 'Additional metadata from the response';


--
-- Name: COLUMN animus_llm_calls.messages_sent; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.messages_sent IS 'ALL messages that were sent to LLM (including history after processing)';


--
-- Name: COLUMN animus_llm_calls."timestamp"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls."timestamp" IS 'Response timestamp from Pydantic AI';


--
-- Name: COLUMN animus_llm_calls.is_cancelled; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.is_cancelled IS 'Whether this LLM call was cancelled';


--
-- Name: COLUMN animus_llm_calls.cancellation_reason; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.cancellation_reason IS 'Reason for cancellation if cancelled';


--
-- Name: COLUMN animus_llm_calls.cancelled_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_llm_calls.cancelled_at IS 'When this LLM call was cancelled';


--
-- Name: animus_message_history_threads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.animus_message_history_threads (
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    thread_id uuid NOT NULL,
    session_id uuid NOT NULL,
    thread_slug character varying(255) NOT NULL,
    name character varying(255),
    metadata jsonb
);


--
-- Name: TABLE animus_message_history_threads; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.animus_message_history_threads IS 'Message history thread model for grouping messages within a session.';


--
-- Name: COLUMN animus_message_history_threads.thread_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_message_history_threads.thread_id IS 'Unique thread identifier';


--
-- Name: COLUMN animus_message_history_threads.session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_message_history_threads.session_id IS 'Session this thread belongs to';


--
-- Name: COLUMN animus_message_history_threads.thread_slug; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_message_history_threads.thread_slug IS 'Unique slug for thread identification';


--
-- Name: COLUMN animus_message_history_threads.name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_message_history_threads.name IS 'Optional thread name for identification';


--
-- Name: COLUMN animus_message_history_threads.metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_message_history_threads.metadata IS 'Additional metadata for the thread (context, branch info, etc.)';


--
-- Name: animus_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.animus_messages (
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    message_id uuid NOT NULL,
    created_by_agent_instance_id uuid,
    agent_slug character varying(255),
    role character varying(6) NOT NULL,
    message jsonb NOT NULL,
    message_vars_meta jsonb,
    last_stream_event_id character varying(36),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE animus_messages; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.animus_messages IS 'Message model representing messages in a session.';


--
-- Name: COLUMN animus_messages.message_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_messages.message_id IS 'Unique message identifier';


--
-- Name: COLUMN animus_messages.created_by_agent_instance_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_messages.created_by_agent_instance_id IS 'Agent instance that created this message';


--
-- Name: COLUMN animus_messages.agent_slug; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_messages.agent_slug IS 'Agent slug for quick lookup (denormalized)';


--
-- Name: COLUMN animus_messages.role; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_messages.role IS 'Message role (user, agent, system, tool)';


--
-- Name: COLUMN animus_messages.message; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_messages.message IS 'Full Pydantic AI message object (ModelRequest or ModelResponse) as JSONB';


--
-- Name: COLUMN animus_messages.message_vars_meta; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_messages.message_vars_meta IS 'Additional metadata about message parts/variables (multi-modal content, etc.)';


--
-- Name: COLUMN animus_messages.last_stream_event_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_messages.last_stream_event_id IS 'UUID of the last AnimusStreamEvent in this message turn (only set on response messages)';


--
-- Name: COLUMN animus_messages."timestamp"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_messages."timestamp" IS 'Message creation timestamp';


--
-- Name: animus_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.animus_sessions (
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    session_id uuid NOT NULL,
    user_id character varying(255),
    status character varying(9) DEFAULT 'active'::character varying NOT NULL,
    metadata jsonb
);


--
-- Name: TABLE animus_sessions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.animus_sessions IS 'Session model representing a conversation or workflow execution.';


--
-- Name: COLUMN animus_sessions.session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_sessions.session_id IS 'Unique session identifier';


--
-- Name: COLUMN animus_sessions.user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_sessions.user_id IS 'User ID associated with the session';


--
-- Name: COLUMN animus_sessions.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_sessions.status IS 'Current session status';


--
-- Name: COLUMN animus_sessions.metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.animus_sessions.metadata IS 'Additional metadata for the session (context, user info, etc.)';


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying NOT NULL
);


--
-- Name: engram_memory_access_logs engram_memory_access_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_access_logs
    ADD CONSTRAINT engram_memory_access_logs_pkey PRIMARY KEY (id);


--
-- Name: engram_memory_fact_tags engram_memory_fact_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_fact_tags
    ADD CONSTRAINT engram_memory_fact_tags_pkey PRIMARY KEY (id);


--
-- Name: engram_memory_fact_versions engram_memory_fact_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_fact_versions
    ADD CONSTRAINT engram_memory_fact_versions_pkey PRIMARY KEY (id);


--
-- Name: engram_memory_facts engram_memory_facts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_facts
    ADD CONSTRAINT engram_memory_facts_pkey PRIMARY KEY (id);


--
-- Name: engram_memory_observations engram_memory_observations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_observations
    ADD CONSTRAINT engram_memory_observations_pkey PRIMARY KEY (id);


--
-- Name: engram_memory_proposals engram_memory_proposals_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_proposals
    ADD CONSTRAINT engram_memory_proposals_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: engram_memory_proposals engram_memory_proposals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_proposals
    ADD CONSTRAINT engram_memory_proposals_pkey PRIMARY KEY (id);


--
-- Name: engram_organizations engram_organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_organizations
    ADD CONSTRAINT engram_organizations_pkey PRIMARY KEY (id);


--
-- Name: engram_organizations engram_organizations_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_organizations
    ADD CONSTRAINT engram_organizations_slug_key UNIQUE (slug);


--
-- Name: engram_personal_access_tokens engram_personal_access_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_personal_access_tokens
    ADD CONSTRAINT engram_personal_access_tokens_pkey PRIMARY KEY (id);


--
-- Name: engram_personal_access_tokens engram_personal_access_tokens_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_personal_access_tokens
    ADD CONSTRAINT engram_personal_access_tokens_token_hash_key UNIQUE (token_hash);


--
-- Name: engram_repositories engram_repositories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_repositories
    ADD CONSTRAINT engram_repositories_pkey PRIMARY KEY (id);


--
-- Name: engram_repository_aliases engram_repository_aliases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_repository_aliases
    ADD CONSTRAINT engram_repository_aliases_pkey PRIMARY KEY (id);


--
-- Name: engram_role_assignments engram_role_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_role_assignments
    ADD CONSTRAINT engram_role_assignments_pkey PRIMARY KEY (id);


--
-- Name: engram_roles engram_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_roles
    ADD CONSTRAINT engram_roles_pkey PRIMARY KEY (id);


--
-- Name: engram_sessions engram_sessions_jwt_id_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_sessions
    ADD CONSTRAINT engram_sessions_jwt_id_hash_key UNIQUE (jwt_id_hash);


--
-- Name: engram_sessions engram_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_sessions
    ADD CONSTRAINT engram_sessions_pkey PRIMARY KEY (id);


--
-- Name: engram_tags engram_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_tags
    ADD CONSTRAINT engram_tags_pkey PRIMARY KEY (id);


--
-- Name: engram_user_identities engram_user_identities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_user_identities
    ADD CONSTRAINT engram_user_identities_pkey PRIMARY KEY (id);


--
-- Name: engram_users engram_users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_users
    ADD CONSTRAINT engram_users_email_key UNIQUE (email);


--
-- Name: engram_users engram_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_users
    ADD CONSTRAINT engram_users_pkey PRIMARY KEY (id);


--
-- Name: animus_agent_instances animus_agent_instances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_agent_instances
    ADD CONSTRAINT animus_agent_instances_pkey PRIMARY KEY (agent_instance_id);


--
-- Name: animus_agent_message_map animus_agent_message_map_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_agent_message_map
    ADD CONSTRAINT animus_agent_message_map_pkey PRIMARY KEY (id);


--
-- Name: animus_agent_models animus_agent_models_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_agent_models
    ADD CONSTRAINT animus_agent_models_pkey PRIMARY KEY (agent_model_id);


--
-- Name: animus_agents animus_agents_agent_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_agents
    ADD CONSTRAINT animus_agents_agent_name_key UNIQUE (agent_name);


--
-- Name: animus_agents animus_agents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_agents
    ADD CONSTRAINT animus_agents_pkey PRIMARY KEY (agent_id);


--
-- Name: animus_handoffs animus_handoffs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_handoffs
    ADD CONSTRAINT animus_handoffs_pkey PRIMARY KEY (handoff_id);


--
-- Name: animus_history_compactions animus_history_compactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_history_compactions
    ADD CONSTRAINT animus_history_compactions_pkey PRIMARY KEY (compaction_id);


--
-- Name: animus_llm_calls animus_llm_calls_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_llm_calls
    ADD CONSTRAINT animus_llm_calls_pkey PRIMARY KEY (llm_call_id);


--
-- Name: animus_message_history_threads animus_message_history_threads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_message_history_threads
    ADD CONSTRAINT animus_message_history_threads_pkey PRIMARY KEY (thread_id);


--
-- Name: animus_message_history_threads animus_message_history_threads_thread_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_message_history_threads
    ADD CONSTRAINT animus_message_history_threads_thread_slug_key UNIQUE (thread_slug);


--
-- Name: animus_messages animus_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_messages
    ADD CONSTRAINT animus_messages_pkey PRIMARY KEY (message_id);


--
-- Name: animus_sessions animus_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_sessions
    ADD CONSTRAINT animus_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: engram_memory_fact_versions uid_agent_conte_fact_id_2d5b3e; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_fact_versions
    ADD CONSTRAINT uid_agent_conte_fact_id_2d5b3e UNIQUE (fact_id, version_number);


--
-- Name: engram_memory_fact_tags uid_agent_conte_fact_id_9cf82f; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_fact_tags
    ADD CONSTRAINT uid_agent_conte_fact_id_9cf82f UNIQUE (fact_id, tag_id);


--
-- Name: engram_roles uid_agent_conte_org_id_1bafb2; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_roles
    ADD CONSTRAINT uid_agent_conte_org_id_1bafb2 UNIQUE (org_id, slug);


--
-- Name: engram_repositories uid_agent_conte_org_id_8c0f13; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_repositories
    ADD CONSTRAINT uid_agent_conte_org_id_8c0f13 UNIQUE (org_id, repository_key);


--
-- Name: engram_repository_aliases uid_agent_conte_org_id_9c2746; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_repository_aliases
    ADD CONSTRAINT uid_agent_conte_org_id_9c2746 UNIQUE (org_id, alias_key);


--
-- Name: engram_role_assignments uid_agent_conte_org_id_9d8548; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_role_assignments
    ADD CONSTRAINT uid_agent_conte_org_id_9d8548 UNIQUE (org_id, user_id, role_id, scope_type, scope_id);


--
-- Name: engram_tags uid_agent_conte_org_id_fad6f3; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_tags
    ADD CONSTRAINT uid_agent_conte_org_id_fad6f3 UNIQUE (org_id, slug);


--
-- Name: engram_user_identities uid_agent_conte_provide_ca5e2d; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_user_identities
    ADD CONSTRAINT uid_agent_conte_provide_ca5e2d UNIQUE (provider, provider_subject);


--
-- Name: animus_agent_models uid_animus_agen_agent_i_959512; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_agent_models
    ADD CONSTRAINT uid_animus_agen_agent_i_959512 UNIQUE (agent_id, model_provider, model_name, model_variant);


--
-- Name: animus_agent_message_map uid_animus_agen_message_0883e6; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.animus_agent_message_map
    ADD CONSTRAINT uid_animus_agen_message_0883e6 UNIQUE (message_history_thread_id, agent_instance_id, message_id);


--
-- Name: engram_memory_access_logs_auth_method_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX engram_memory_access_logs_auth_method_idx ON public.engram_memory_access_logs USING btree (auth_method);


--
-- Name: engram_memory_access_logs_client_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX engram_memory_access_logs_client_type_idx ON public.engram_memory_access_logs USING btree (client_type);


--
-- Name: engram_memory_access_logs_pat_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX engram_memory_access_logs_pat_id_idx ON public.engram_memory_access_logs USING btree (personal_access_token_id);


--
-- Name: engram_memory_access_logs_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX engram_memory_access_logs_session_id_idx ON public.engram_memory_access_logs USING btree (session_id);


--
-- Name: engram_personal_access_tokens_expires_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX engram_personal_access_tokens_expires_at_idx ON public.engram_personal_access_tokens USING btree (expires_at);


--
-- Name: engram_personal_access_tokens_key_prefix_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX engram_personal_access_tokens_key_prefix_idx ON public.engram_personal_access_tokens USING btree (key_prefix);


--
-- Name: engram_personal_access_tokens_user_org_revoked_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX engram_personal_access_tokens_user_org_revoked_idx ON public.engram_personal_access_tokens USING btree (user_id, org_id, revoked_at);


--
-- Name: engram_sessions_expires_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX engram_sessions_expires_at_idx ON public.engram_sessions USING btree (expires_at);


--
-- Name: engram_sessions_user_org_revoked_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX engram_sessions_user_org_revoked_idx ON public.engram_sessions USING btree (user_id, org_id, revoked_at);


--
-- Name: idx_agent_conte_content_04a427; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_content_04a427 ON public.engram_memory_facts USING btree (content_hash);


--
-- Name: idx_agent_conte_content_3cc133; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_content_3cc133 ON public.engram_memory_proposals USING btree (content_hash);


--
-- Name: idx_agent_conte_expires_630b6d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_expires_630b6d ON public.engram_sessions USING btree (expires_at);


--
-- Name: idx_agent_conte_expires_f98183; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_expires_f98183 ON public.engram_personal_access_tokens USING btree (expires_at);


--
-- Name: idx_agent_conte_key_pre_0983d0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_key_pre_0983d0 ON public.engram_personal_access_tokens USING btree (key_prefix);


--
-- Name: idx_agent_conte_org_id_08624d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_org_id_08624d ON public.engram_memory_access_logs USING btree (org_id, action, created_at);


--
-- Name: idx_agent_conte_org_id_2e0c02; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_org_id_2e0c02 ON public.engram_memory_proposals USING btree (org_id, scope_type, scope_id, status);


--
-- Name: idx_agent_conte_org_id_8e04ed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_org_id_8e04ed ON public.engram_memory_facts USING btree (org_id, scope_type, scope_id, status);


--
-- Name: idx_agent_conte_org_id_d081ba; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_org_id_d081ba ON public.engram_memory_observations USING btree (org_id, scope_type, scope_id);


--
-- Name: idx_agent_conte_request_09bda5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_request_09bda5 ON public.engram_memory_access_logs USING btree (request_id);


--
-- Name: idx_agent_conte_user_id_5fd66e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_user_id_5fd66e ON public.engram_personal_access_tokens USING btree (user_id, org_id, revoked_at);


--
-- Name: idx_agent_conte_user_id_dfd2da; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_conte_user_id_dfd2da ON public.engram_sessions USING btree (user_id, org_id, revoked_at);


--
-- Name: idx_animus_agen_agent_i_9d8675; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_agent_i_9d8675 ON public.animus_agent_models USING btree (agent_id);


--
-- Name: idx_animus_agen_agent_i_c90b69; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_agent_i_c90b69 ON public.animus_agent_message_map USING btree (agent_instance_id);


--
-- Name: idx_animus_agen_agent_i_cffa7c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_agent_i_cffa7c ON public.animus_agent_instances USING btree (agent_id);


--
-- Name: idx_animus_agen_agent_n_4161d2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_agent_n_4161d2 ON public.animus_agents USING btree (agent_name);


--
-- Name: idx_animus_agen_agent_s_81f9e3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_agent_s_81f9e3 ON public.animus_agent_instances USING btree (agent_slug);


--
-- Name: idx_animus_agen_is_acti_e8af40; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_is_acti_e8af40 ON public.animus_agent_models USING btree (is_active);


--
-- Name: idx_animus_agen_message_89f322; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_message_89f322 ON public.animus_agent_message_map USING btree (message_history_thread_id);


--
-- Name: idx_animus_agen_message_ae1f44; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_message_ae1f44 ON public.animus_agent_message_map USING btree (message_id);


--
-- Name: idx_animus_agen_model_p_be0a7c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_model_p_be0a7c ON public.animus_agent_models USING btree (model_provider);


--
-- Name: idx_animus_agen_priorit_a09edc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_priorit_a09edc ON public.animus_agent_models USING btree (priority);


--
-- Name: idx_animus_agen_session_68a50c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_session_68a50c ON public.animus_agent_instances USING btree (session_id);


--
-- Name: idx_animus_agen_status_4b4bd7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_agen_status_4b4bd7 ON public.animus_agent_instances USING btree (status);


--
-- Name: idx_animus_hand_from_ag_5532c1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_hand_from_ag_5532c1 ON public.animus_handoffs USING btree (from_agent_instance_id);


--
-- Name: idx_animus_hand_handoff_8cec51; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_hand_handoff_8cec51 ON public.animus_handoffs USING btree (handoff_strategy);


--
-- Name: idx_animus_hand_session_d10796; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_hand_session_d10796 ON public.animus_handoffs USING btree (session_id);


--
-- Name: idx_animus_hand_timesta_0dcbaa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_hand_timesta_0dcbaa ON public.animus_handoffs USING btree ("timestamp");


--
-- Name: idx_animus_hand_to_agen_33cbcd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_hand_to_agen_33cbcd ON public.animus_handoffs USING btree (to_agent_instance_id);


--
-- Name: idx_animus_hist_thread__492b68; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_hist_thread__492b68 ON public.animus_history_compactions USING btree (thread_id, created_at);


--
-- Name: idx_animus_llm__agent_i_53e67f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_llm__agent_i_53e67f ON public.animus_llm_calls USING btree (agent_instance_id);


--
-- Name: idx_animus_llm__model_n_7b3814; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_llm__model_n_7b3814 ON public.animus_llm_calls USING btree (model_name);


--
-- Name: idx_animus_llm__provide_77a2fe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_llm__provide_77a2fe ON public.animus_llm_calls USING btree (provider_name);


--
-- Name: idx_animus_llm__run_id_35c6ca; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_llm__run_id_35c6ca ON public.animus_llm_calls USING btree (run_id);


--
-- Name: idx_animus_llm__session_f4152b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_llm__session_f4152b ON public.animus_llm_calls USING btree (session_id);


--
-- Name: idx_animus_llm__timesta_6984b2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_llm__timesta_6984b2 ON public.animus_llm_calls USING btree ("timestamp");


--
-- Name: idx_animus_mess_agent_s_cb3db1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_mess_agent_s_cb3db1 ON public.animus_messages USING btree (agent_slug);


--
-- Name: idx_animus_mess_created_4c167a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_mess_created_4c167a ON public.animus_messages USING btree (created_by_agent_instance_id);


--
-- Name: idx_animus_mess_created_95fcfe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_mess_created_95fcfe ON public.animus_message_history_threads USING btree (created_at);


--
-- Name: idx_animus_mess_role_b96777; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_mess_role_b96777 ON public.animus_messages USING btree (role);


--
-- Name: idx_animus_mess_session_52531d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_mess_session_52531d ON public.animus_message_history_threads USING btree (session_id);


--
-- Name: idx_animus_mess_thread__6589b8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_mess_thread__6589b8 ON public.animus_message_history_threads USING btree (thread_slug);


--
-- Name: idx_animus_mess_timesta_0c3882; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_mess_timesta_0c3882 ON public.animus_messages USING btree ("timestamp");


--
-- Name: idx_animus_sess_created_14734b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_sess_created_14734b ON public.animus_sessions USING btree (created_at);


--
-- Name: idx_animus_sess_status_5f5855; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_sess_status_5f5855 ON public.animus_sessions USING btree (status);


--
-- Name: idx_animus_sess_user_id_47a5ba; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_animus_sess_user_id_47a5ba ON public.animus_sessions USING btree (user_id);


--
-- Name: engram_memory_access_logs engram_memory_access_logs_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_access_logs
    ADD CONSTRAINT engram_memory_access_logs_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.engram_users(id) ON DELETE SET NULL;


--
-- Name: engram_memory_access_logs engram_memory_access_logs_memory_fact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_access_logs
    ADD CONSTRAINT engram_memory_access_logs_memory_fact_id_fkey FOREIGN KEY (memory_fact_id) REFERENCES public.engram_memory_facts(id) ON DELETE SET NULL;


--
-- Name: engram_memory_access_logs engram_memory_access_logs_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_access_logs
    ADD CONSTRAINT engram_memory_access_logs_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE SET NULL;


--
-- Name: engram_memory_access_logs engram_memory_access_logs_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_access_logs
    ADD CONSTRAINT engram_memory_access_logs_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.engram_memory_proposals(id) ON DELETE SET NULL;


--
-- Name: engram_memory_access_logs engram_memory_access_logs_repository_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_access_logs
    ADD CONSTRAINT engram_memory_access_logs_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES public.engram_repositories(id) ON DELETE SET NULL;


--
-- Name: engram_memory_fact_tags engram_memory_fact_tags_fact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_fact_tags
    ADD CONSTRAINT engram_memory_fact_tags_fact_id_fkey FOREIGN KEY (fact_id) REFERENCES public.engram_memory_facts(id) ON DELETE CASCADE;


--
-- Name: engram_memory_fact_tags engram_memory_fact_tags_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_fact_tags
    ADD CONSTRAINT engram_memory_fact_tags_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE CASCADE;


--
-- Name: engram_memory_fact_tags engram_memory_fact_tags_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_fact_tags
    ADD CONSTRAINT engram_memory_fact_tags_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.engram_tags(id) ON DELETE CASCADE;


--
-- Name: engram_memory_fact_versions engram_memory_fact_versions_changed_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_fact_versions
    ADD CONSTRAINT engram_memory_fact_versions_changed_by_id_fkey FOREIGN KEY (changed_by_id) REFERENCES public.engram_users(id) ON DELETE SET NULL;


--
-- Name: engram_memory_fact_versions engram_memory_fact_versions_fact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_fact_versions
    ADD CONSTRAINT engram_memory_fact_versions_fact_id_fkey FOREIGN KEY (fact_id) REFERENCES public.engram_memory_facts(id) ON DELETE CASCADE;


--
-- Name: engram_memory_fact_versions engram_memory_fact_versions_proposal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_fact_versions
    ADD CONSTRAINT engram_memory_fact_versions_proposal_id_fkey FOREIGN KEY (proposal_id) REFERENCES public.engram_memory_proposals(id) ON DELETE SET NULL;


--
-- Name: engram_memory_facts engram_memory_facts_approved_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_facts
    ADD CONSTRAINT engram_memory_facts_approved_by_id_fkey FOREIGN KEY (approved_by_id) REFERENCES public.engram_users(id) ON DELETE SET NULL;


--
-- Name: engram_memory_facts engram_memory_facts_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_facts
    ADD CONSTRAINT engram_memory_facts_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.engram_users(id) ON DELETE SET NULL;


--
-- Name: engram_memory_facts engram_memory_facts_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_facts
    ADD CONSTRAINT engram_memory_facts_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE CASCADE;


--
-- Name: engram_memory_facts engram_memory_facts_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_facts
    ADD CONSTRAINT engram_memory_facts_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.engram_users(id) ON DELETE SET NULL;


--
-- Name: engram_memory_facts engram_memory_facts_repository_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_facts
    ADD CONSTRAINT engram_memory_facts_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES public.engram_repositories(id) ON DELETE SET NULL;


--
-- Name: engram_memory_facts engram_memory_facts_updated_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_facts
    ADD CONSTRAINT engram_memory_facts_updated_by_id_fkey FOREIGN KEY (updated_by_id) REFERENCES public.engram_users(id) ON DELETE SET NULL;


--
-- Name: engram_memory_observations engram_memory_observations_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_observations
    ADD CONSTRAINT engram_memory_observations_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.engram_users(id) ON DELETE SET NULL;


--
-- Name: engram_memory_observations engram_memory_observations_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_observations
    ADD CONSTRAINT engram_memory_observations_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE CASCADE;


--
-- Name: engram_memory_observations engram_memory_observations_repository_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_observations
    ADD CONSTRAINT engram_memory_observations_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES public.engram_repositories(id) ON DELETE SET NULL;


--
-- Name: engram_memory_proposals engram_memory_proposals_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_proposals
    ADD CONSTRAINT engram_memory_proposals_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.engram_users(id) ON DELETE SET NULL;


--
-- Name: engram_memory_proposals engram_memory_proposals_fact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_proposals
    ADD CONSTRAINT engram_memory_proposals_fact_id_fkey FOREIGN KEY (fact_id) REFERENCES public.engram_memory_facts(id) ON DELETE SET NULL;


--
-- Name: engram_memory_proposals engram_memory_proposals_observation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_proposals
    ADD CONSTRAINT engram_memory_proposals_observation_id_fkey FOREIGN KEY (observation_id) REFERENCES public.engram_memory_observations(id) ON DELETE SET NULL;


--
-- Name: engram_memory_proposals engram_memory_proposals_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_proposals
    ADD CONSTRAINT engram_memory_proposals_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE CASCADE;


--
-- Name: engram_memory_proposals engram_memory_proposals_repository_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_proposals
    ADD CONSTRAINT engram_memory_proposals_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES public.engram_repositories(id) ON DELETE SET NULL;


--
-- Name: engram_memory_proposals engram_memory_proposals_reviewed_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_memory_proposals
    ADD CONSTRAINT engram_memory_proposals_reviewed_by_id_fkey FOREIGN KEY (reviewed_by_id) REFERENCES public.engram_users(id) ON DELETE SET NULL;


--
-- Name: engram_personal_access_tokens engram_personal_access_tokens_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_personal_access_tokens
    ADD CONSTRAINT engram_personal_access_tokens_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE CASCADE;


--
-- Name: engram_personal_access_tokens engram_personal_access_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_personal_access_tokens
    ADD CONSTRAINT engram_personal_access_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.engram_users(id) ON DELETE CASCADE;


--
-- Name: engram_repositories engram_repositories_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_repositories
    ADD CONSTRAINT engram_repositories_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE CASCADE;


--
-- Name: engram_repository_aliases engram_repository_aliases_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_repository_aliases
    ADD CONSTRAINT engram_repository_aliases_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE CASCADE;


--
-- Name: engram_repository_aliases engram_repository_aliases_repository_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_repository_aliases
    ADD CONSTRAINT engram_repository_aliases_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES public.engram_repositories(id) ON DELETE CASCADE;


--
-- Name: engram_role_assignments engram_role_assignments_assigned_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_role_assignments
    ADD CONSTRAINT engram_role_assignments_assigned_by_id_fkey FOREIGN KEY (assigned_by_id) REFERENCES public.engram_users(id) ON DELETE SET NULL;


--
-- Name: engram_role_assignments engram_role_assignments_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_role_assignments
    ADD CONSTRAINT engram_role_assignments_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE CASCADE;


--
-- Name: engram_role_assignments engram_role_assignments_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_role_assignments
    ADD CONSTRAINT engram_role_assignments_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.engram_roles(id) ON DELETE CASCADE;


--
-- Name: engram_role_assignments engram_role_assignments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_role_assignments
    ADD CONSTRAINT engram_role_assignments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.engram_users(id) ON DELETE CASCADE;


--
-- Name: engram_roles engram_roles_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_roles
    ADD CONSTRAINT engram_roles_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE CASCADE;


--
-- Name: engram_sessions engram_sessions_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_sessions
    ADD CONSTRAINT engram_sessions_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE CASCADE;


--
-- Name: engram_sessions engram_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_sessions
    ADD CONSTRAINT engram_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.engram_users(id) ON DELETE CASCADE;


--
-- Name: engram_tags engram_tags_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_tags
    ADD CONSTRAINT engram_tags_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.engram_organizations(id) ON DELETE CASCADE;


--
-- Name: engram_user_identities engram_user_identities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.engram_user_identities
    ADD CONSTRAINT engram_user_identities_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.engram_users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict dbmate


--
-- Dbmate schema migrations
--

INSERT INTO public.schema_migrations (version) VALUES
    ('20260704152000'),
    ('20260704161000');
