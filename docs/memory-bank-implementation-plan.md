# Engram Memory Bank Implementation Plan

## Goal

Build an organization-grade memory bank for coding agents and internal AI tools. The backend will power:

- MCP tools for Claude Code first.
- User-level, organization-level, and repository-level memories.
- Optional category/tag filtering on top of memory scope.
- LLM-assisted memory processing through Animus.
- Review and governance workflows for dashboard users.
- RBAC for regular users, team admins, org admins, and service/admin users.
- Future semantic or hybrid retrieval through Qdrant embeddings.

The backend is expected to live in `engram-backend`, using:

- Vortex as the FastAPI wrapper.
- Tortoise ORM for PostgreSQL persistence.
- FastMCP for MCP server/tool exposure.
- Qdrant for optional vector retrieval.
- Animus for LLM calls, structured memory processing, and embedding model access.
- A project-owned `MemoryEmbeddingService` for embedding generation when semantic retrieval is enabled.

The dashboard UI is out of scope for this repo, but this backend should expose APIs that make the dashboard straightforward to build in React/Next.js.

---

## Related Design Docs

- [Repository scope resolution](./repository-scope-resolution.md)
- [MCP and dashboard authentication](./mcp-phase-1-auth.md)
- [Animus reference and project usage](./animus.md)
- [Embedding and retrieval design](./embedding-retrieval-design.md)

---

## Current Repository State

After reviewing the repository, the backend is still at scaffold/POC bootstrap:

- `main.py` creates the Vortex app, but no domain routers are registered yet.
- `models/`, `schemas/`, `services/`, and `routers/` currently contain package markers only.
- `tests/` contains the default `/ping` health-check test.
- `config_template.json` has core Vortex, Sentry, Redis, database, Langfuse, and OpenTelemetry sections, but it does not yet include the planned `ENGRAM`, `ENGRAM_AUTH`, `MEMORY_PROCESSING`, `EMBEDDINGS`, or `QDRANT` sections. Runtime `config.json` remains the intended config source; production should generate it from Vault-managed JSON.
- `pyproject.toml` already includes Vortex, Animus, FastMCP, SQLAlchemy, Tortoise ORM, Qdrant client, Redis, and asyncpg dependencies.

Implication: the memory-bank sections below describe the target architecture, not implemented behavior. The implementation should align on Tortoise ORM for persistence because it is simpler for this POC and is already used by Animus internally. The existing SQLAlchemy dependency should be treated as removable unless another Vortex/project requirement needs it.

---

## Reference Patterns From Mem0

The Mem0/OpenMemory implementation in `openmemory/api/app/mcp_server.py` provides useful patterns to reuse conceptually:

1. **FastMCP tool registration**
   - Uses `FastMCP("mem0-mcp-server")`.
   - Registers tools with `@mcp.tool(...)`.

2. **Per-request context variables**
   - Stores `user_id` and `client_name` in `contextvars`.
   - Tool functions read from the context instead of requiring every parameter explicitly.

3. **Lazy client initialization**
   - Memory client initialization is deferred until a tool actually needs it.
   - If dependencies are unavailable, the MCP server still starts and returns safe errors.

4. **MCP transport support**
   - Supports SSE and Streamable HTTP.
   - Streamable HTTP is the newer transport and should be the primary target for new clients.

5. **Permission filtering before returning memories**
   - Search/list results are filtered by access-control checks before being returned to the agent.

6. **Audit/history models**
   - Keeps memory state history and memory access logs.
   - This is important for dashboard review, debugging, and compliance.

For this org memory bank, we should keep those patterns but extend the model for org/repo scoping, review workflows, RBAC, semantic retrieval readiness, and richer lifecycle states.

---

## High-Level Architecture

```text
Claude Code / MCP Client
        |
        | MCP over Streamable HTTP initially
        v
Vortex/FastAPI Backend
        |
        |-- MCP router/tools
        |-- Dashboard REST APIs
        |-- RBAC + audit services
        |-- Memory ingestion/retrieval services
        |-- Animus processing service
        |
        |------------------ PostgreSQL
        |                   - users/orgs/repos
        |                   - memories/facts
        |                   - tags/categories
        |                   - proposals/reviews
        |                   - permissions/audit logs
        |
        |------------------ Qdrant
                            - optional memory vectors
                            - collection per environment or tenant strategy
```

Recommended split:

```text
engram-backend/
├── main.py
├── models/
│   ├── base.py
│   ├── identity.py
│   ├── memory.py
│   ├── review.py
│   └── audit.py
├── schemas/
│   ├── memory.py
│   ├── review.py
│   └── mcp.py
├── services/
│   ├── memory_service.py
│   ├── memory_processing_service.py
│   ├── memory_retrieval_service.py
│   ├── rbac_service.py
│   ├── qdrant_service.py
│   └── audit_service.py
├── routers/
│   ├── mcp_router.py
│   ├── memories.py
│   ├── reviews.py
│   ├── tags.py
│   └── admin.py
└── docs/
    └── memory-bank-implementation-plan.md
```

---

## Memory Scope Model

Each memory must belong to exactly one primary scope.

### Scope Types

| Scope | Meaning | Examples |
|---|---|---|
| `user` | Personal memory for one user | User preferences, personal coding style, recurring tasks |
| `org` | Shared memory for the whole organization | Engineering standards, incident policies, approved tools |
| `repo` | Memory specific to one repository | Architecture decisions, module ownership, test commands |

Optional future scopes can include:

- `team`
- `project`
- `service`
- `environment`

For the current rollout, keep the enum narrow: `user`, `org`, `repo`.

### Scope Resolution

Every MCP request should resolve a context object like:

```text
ActorContext
- actor_user_id
- org_id
- repo_id, optional
- repo_slug, optional
- client_name, e.g. claude-code
- session_id, optional
- request_id
- roles/permissions
```

For Claude Code/Codex-style agent runtimes, repository context should come from local environment and Git metadata collected by the client/hook:

1. Bitbucket `origin_url`, if available.
2. Git root, branch, and commit metadata from the active workspace.
3. Optional tool arguments like `repo_slug` as a fallback/hint.
4. Fallback: no repo scope if the current repo cannot be identified.

Recommended first version: resolve `org_id` and `actor_user_id` from MCP auth headers, resolve repo identity from Bitbucket origin URL/local Git metadata, and accept optional `repo_slug` only as a fallback hint. See [MCP phase-1 header authentication](./mcp-phase-1-auth.md) and [Repository scope resolution](./repository-scope-resolution.md).

---

## Database Design

Use PostgreSQL as the source of truth. Qdrant should be treated as a derived index that can be rebuilt from PostgreSQL.

### Core Identity Tables

#### `users`

Stores dashboard/MCP users.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Internal ID |
| `external_user_id` | String unique | SSO/HR/auth identity |
| `email` | String unique nullable | User email |
| `name` | String nullable | Display name |
| `status` | Enum | `active`, `disabled` |
| `metadata` | JSONB | Extra attributes |
| `created_at` | timestamptz |  |
| `updated_at` | timestamptz |  |

#### `organizations`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK |  |
| `slug` | String unique | Stable org identifier |
| `name` | String |  |
| `metadata` | JSONB |  |
| `created_at` | timestamptz |  |
| `updated_at` | timestamptz |  |

#### `repositories`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK |  |
| `org_id` | UUID FK | Owning org |
| `slug` | String | Example: `engram-backend` |
| `provider` | String nullable | Phase-1 default: `bitbucket`; keep extensible for future providers |
| `host` | String nullable | Example: `bitbucket.org` |
| `workspace` | String nullable | Bitbucket workspace/project owner, e.g. `tata1mg` |
| `repo_slug` | String nullable | Bitbucket repository slug |
| `repository_key` | String nullable | Canonical key, e.g. `bitbucket.org/tata1mg/engram-backend` |
| `bitbucket_origin_url` | String nullable | Original or canonical Bitbucket origin URL used for linking/resolution |
| `remote_url` | String nullable | Canonical remote; phase-1 same as Bitbucket canonical URL |
| `default_branch` | String nullable |  |
| `metadata` | JSONB | Codex/Claude local git metadata, aliases, resolver confidence |
| `created_at` | timestamptz |  |
| `updated_at` | timestamptz |  |

Indexes:

- Unique `(org_id, slug)`.
- Unique `(org_id, repository_key)` where `repository_key` is not null.
- Index `(org_id, provider)`.
- Index `(org_id, host, workspace, repo_slug)`.

---

## RBAC Model

RBAC must apply to both dashboard APIs and MCP tools.

### Suggested Roles

| Role | Scope | Capabilities |
|---|---|---|
| `user` | user/org | Read own user memories, propose repo/org memories if permitted |
| `repo_member` | repo | Read approved repo memories |
| `repo_admin` | repo | Approve/reject/edit repo memories |
| `team_admin` | team/org subset | Future role for mapped repos/teams; team-level memories are deferred beyond phase 1 |
| `org_admin` | org | Full org/repo review and management |
| `memory_admin` | global/org | Maintenance, audits, re-indexing |
| `service_account` | org/repo | MCP/plugin access with delegated actor context |

### Tables

#### `roles`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK |  |
| `name` | String unique | `org_admin`, `repo_admin`, etc. |
| `description` | String nullable |  |

#### `role_assignments`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK |  |
| `user_id` | UUID FK | User receiving the role |
| `role_id` | UUID FK | Role |
| `scope_type` | Enum | `org`, `repo`, `user` |
| `scope_id` | UUID | The org/repo/user ID |
| `created_by` | UUID nullable | Actor who granted it |
| `created_at` | timestamptz |  |

Indexes:

- `(user_id, scope_type, scope_id)`.
- `(scope_type, scope_id, role_id)`.

### Permission Rules

Access should be centralized in `rbac_service.py`.

Example checks:

```text
can_read_memory(actor, memory)
can_create_memory(actor, scope_type, scope_id)
can_propose_memory(actor, scope_type, scope_id)
can_approve_memory(actor, memory)
can_edit_memory(actor, memory)
can_delete_memory(actor, memory)
can_manage_tags(actor, org_id)
```

MCP tools should never query memories directly without passing through these checks.

### Approval Defaults

Phase-1 approval policy:

1. **User-level memories:** no review required by default. The resolved owner can create/edit their own user memories directly.
2. **Repo-level memories:** review required by default before becoming visible to agents.
3. **Org-level memories:** review required by default before becoming visible to agents.
4. **Admins/reviewers:** repo/org admins can approve proposals for their scope; direct approval can be allowed later behind explicit policy, but the safer phase-1 default is proposal first.
5. **Team-level facts:** deferred. Team roles can exist for RBAC planning, but team-scoped memories should not be introduced in phase 1 because classification is ambiguous.


---

## Memory Data Model

The system should separate:

1. **Raw observations**: Things seen in prompts, tool outputs, repository files, terminal results, etc.
2. **Canonical facts**: Reviewed or LLM-extracted memories that agents should consume.
3. **Proposals**: Pending new facts or updates that need approval.

This avoids letting every agent interaction directly mutate approved knowledge.

### `memory_facts`

This is the canonical memory table.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Memory/fact ID |
| `org_id` | UUID FK | Always present |
| `scope_type` | Enum | `user`, `org`, `repo` |
| `scope_id` | UUID | User/org/repo ID depending on scope |
| `repo_id` | UUID nullable | Denormalized for repo memories and easier filtering |
| `owner_user_id` | UUID nullable | For user-level memories |
| `content` | Text | Canonical fact text |
| `summary` | Text nullable | Short version for dashboard/listing |
| `source` | Enum | `mcp`, `dashboard`, `import`, `system`, `hook` |
| `source_client` | String nullable | `claude-code`, `cursor`, etc. |
| `confidence` | Float nullable | LLM extraction confidence |
| `status` | Enum | See below |
| `visibility` | Enum | `private`, `repo`, `org` |
| `created_by` | UUID nullable | User/service actor |
| `updated_by` | UUID nullable |  |
| `approved_by` | UUID nullable |  |
| `approved_at` | timestamptz nullable |  |
| `rejected_by` | UUID nullable |  |
| `rejected_at` | timestamptz nullable |  |
| `metadata` | JSONB | Tool/session/model info |
| `created_at` | timestamptz |  |
| `updated_at` | timestamptz |  |
| `archived_at` | timestamptz nullable |  |
| `deleted_at` | timestamptz nullable |  |

Recommended statuses:

```text
pending_review
approved
rejected
archived
deleted
superseded
```

Indexes:

- `(org_id, scope_type, scope_id, status)`.
- `(org_id, repo_id, status)`.
- `(org_id, owner_user_id, status)`.
- Full-text index on `content` if PostgreSQL lexical search is needed.
- Partial index for approved memories: `(org_id, scope_type, scope_id) WHERE status = 'approved'`.

### `memory_observations`

Stores raw inputs that may produce one or more facts.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK |  |
| `org_id` | UUID FK |  |
| `actor_user_id` | UUID nullable |  |
| `repo_id` | UUID nullable |  |
| `source_client` | String | `claude-code` |
| `source_type` | Enum | `prompt`, `tool_output`, `file_context`, `manual`, `import` |
| `raw_text` | Text | Original input |
| `metadata` | JSONB | Session/tool/file info |
| `processed_status` | Enum | `pending`, `processed`, `failed`, `ignored` |
| `created_at` | timestamptz |  |

This table is optional for the very first MVP, but strongly recommended because it gives auditability and enables reprocessing when prompts/models change.

### `memory_proposals`

Used for LLM-extracted new facts or updates that require review.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK |  |
| `org_id` | UUID FK |  |
| `observation_id` | UUID nullable FK | Source observation |
| `target_memory_id` | UUID nullable FK | Present for updates/deletes |
| `proposal_type` | Enum | `create`, `update`, `delete`, `merge` |
| `scope_type` | Enum | `user`, `org`, `repo` |
| `scope_id` | UUID |  |
| `proposed_content` | Text | Suggested canonical fact |
| `current_content_snapshot` | Text nullable | Existing fact at proposal time |
| `reasoning` | Text nullable | LLM/user explanation |
| `confidence` | Float nullable |  |
| `status` | Enum | `pending`, `approved`, `rejected`, `applied`, `cancelled` |
| `created_by` | UUID nullable |  |
| `reviewed_by` | UUID nullable |  |
| `reviewed_at` | timestamptz nullable |  |
| `metadata` | JSONB | Model/prompt/category info |
| `created_at` | timestamptz |  |
| `updated_at` | timestamptz |  |

### `memory_fact_versions`

Keep every approved/manual edit version.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK |  |
| `memory_fact_id` | UUID FK |  |
| `version` | Integer | Incrementing version number |
| `content` | Text | Content at this version |
| `change_type` | Enum | `create`, `update`, `manual_edit`, `approve`, `archive`, `delete` |
| `changed_by` | UUID nullable |  |
| `change_reason` | Text nullable |  |
| `metadata` | JSONB |  |
| `created_at` | timestamptz |  |

### `tags`

Category/tag system for further filtering.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK |  |
| `org_id` | UUID FK | Tags should usually be org-local |
| `name` | String | Human-readable tag |
| `slug` | String | Stable normalized tag |
| `description` | Text nullable |  |
| `created_by` | UUID nullable |  |
| `created_at` | timestamptz |  |
| `updated_at` | timestamptz |  |

Unique `(org_id, slug)`.

### `memory_fact_tags`

| Column | Type | Notes |
|---|---|---|
| `memory_fact_id` | UUID FK |  |
| `tag_id` | UUID FK |  |
| `created_by` | UUID nullable |  |
| `created_at` | timestamptz |  |

### `memory_access_logs`

Audit reads/writes from MCP and dashboard.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK |  |
| `org_id` | UUID FK |  |
| `memory_fact_id` | UUID nullable FK | Null for searches with no result |
| `actor_user_id` | UUID nullable |  |
| `client_name` | String nullable |  |
| `access_type` | Enum | `search`, `list`, `read`, `create`, `update`, `delete`, `approve`, `reject` |
| `request_id` | String nullable |  |
| `metadata` | JSONB | query, scores, filters, etc. |
| `created_at` | timestamptz |  |

---

## Qdrant / Embedding Readiness

Even if semantic search is not enabled in v1, design for it now.

### Source of Truth

PostgreSQL remains the source of truth. Qdrant is an index/cache.

Never rely on Qdrant alone for authorization or memory lifecycle state. Always apply PostgreSQL/RBAC filters before returning results.

### Qdrant Collection Strategy

Use one shared Qdrant deployment with multiple collections.

Recommended v1 collection strategy:

```text
collection: engram_memories_<environment>
```

Examples:

```text
engram_memories_dev
engram_memories_stage
engram_memories_prod
```

If isolation requirements grow later, add collections per org or per embedding model/dimension migration. Do not mix vectors with different dimensions in the same unnamed-vector collection.

Payload for each vector:

```json
{
  "memory_fact_id": "uuid",
  "org_id": "uuid",
  "scope_type": "repo",
  "scope_id": "uuid",
  "repo_id": "uuid-or-null",
  "owner_user_id": "uuid-or-null",
  "status": "approved",
  "visibility": "repo",
  "tag_slugs": ["testing", "architecture"],
  "updated_at": "2026-07-03T00:00:00Z"
}
```

### Embedding Model Choice

Supported options:

- `openai:text-embedding-3-large` — selected default; 3072 dimensions by default, 8192-token max input.
- `google:gemini-embedding-2` — fallback if OpenAI embeddings are unavailable or unsuitable.
- `google:gemini-embedding-001` — older Gemini option if required by provider availability.
- `openai:text-embedding-3-small` — cost-saving fallback only, not the preferred default.

Local/private embeddings are out of scope for this rollout.

Use Animus-compatible embedding helpers/classes behind an internal `MemoryEmbeddingService`. Animus remains the model access layer for extraction/classification/summarization and embeddings; memory CRUD, retrieval, and MCP tool code should not import or call Pydantic AI directly. See [Embedding and retrieval design](./embedding-retrieval-design.md).

OpenAI v3 embeddings support dimension reduction through the `dimensions` setting. If dimensions are changed, create or migrate to a matching Qdrant collection and re-embed existing facts.

### Retrieval Modes

Add a config flag:

```json
{
  "MEMORY_RETRIEVAL": {
    "MODE": "lexical",
    "ENABLE_QDRANT": false,
    "DEFAULT_LIMIT": 20,
    "MAX_LIMIT": 100,
    "EMBEDDING_MODEL": "openai:text-embedding-3-large",
    "FALLBACK_EMBEDDING_MODEL": "google:gemini-embedding-2"
  }
}
```

Possible modes:

| Mode | Behavior |
|---|---|
| `all_scoped` | Return all approved memories in the requested scopes, bounded by limit |
| `lexical` | PostgreSQL search over content/tags/scope |
| `semantic` | Qdrant vector search, then PostgreSQL authorization filter |
| `hybrid` | Combine lexical + semantic, then rerank |

Recommended first production behavior for Claude Code:

1. If query is provided and Qdrant is enabled: semantic or hybrid search.
2. If Qdrant is disabled: lexical search.
3. Never pass everything unbounded.
4. Always enforce a max limit.

### Why Not Pass Everything?

Passing all memories can work for very small memory sets, but it has problems:

- Token cost grows quickly.
- Irrelevant memories can distract the coding agent.
- Privacy/RBAC mistakes become more dangerous.
- Latency increases.
- It prevents good dashboard curation incentives.

Use `all_scoped` only as a fallback/debug mode, with strict limits and explicit scopes.

---

## LLM Processing With Animus

Animus should be used for post-processing raw observations into structured memory proposals. See [Animus reference and project usage](./animus.md).

### Processing Pipeline

```text
Raw input from MCP/hook/manual API
        |
        v
memory_observations row
        |
        v
Animus extraction/classification
        |
        |-- no useful fact -> mark observation ignored
        |-- new fact -> memory_proposals(create)
        |-- update existing fact -> memory_proposals(update)
        |-- duplicate -> link or ignore
        v
Review workflow
        |
        |-- approved -> memory_facts + versions + optional Qdrant upsert
        |-- rejected -> proposal rejected
```

### Extracted Fact Schema

The LLM should return a structured object, not free-form prose.

```text
ExtractedMemoryFact
- action: create | update | ignore
- scope_type: user | org | repo
- scope_hint: optional string
- content: canonical fact text
- summary: optional short summary
- tags: list[string]
- confidence: float
- reason: string
- sensitivity: low | medium | high
- requires_review: bool
```

### Processing Rules

1. User-level memories can be auto-approved for low-risk personal preferences if product policy allows it.
2. Org-level and repo-level memories should default to `pending_review`.
3. High-sensitivity facts should always require review.
4. LLM output must be validated with Pydantic schemas before storage.
5. LLM-generated tags should be normalized and checked against allowed org tags, or inserted as pending tag suggestions.
6. Every LLM call should store model metadata and prompt version in `metadata`.

### Prompt Versioning

Create a stable prompt registry in code:

```text
MEMORY_EXTRACTION_PROMPT_V1
MEMORY_DEDUP_PROMPT_V1
MEMORY_RERANK_PROMPT_V1
```

Store prompt version in proposal metadata:

```json
{
  "prompt_version": "MEMORY_EXTRACTION_PROMPT_V1",
  "model": "...",
  "provider": "animus",
  "source": "claude-code"
}
```

---

## MCP Tool Design

Target Claude Code first. Keep tools explicit and safe.

### Recommended Tool Names

Use names that make scope clear and avoid accidental broad access.

#### 1. `save_memory`

Creates an observation and either directly creates a fact or creates a proposal depending on policy.

Inputs:

```json
{
  "content": "Repo uses uv for Python commands.",
  "scope_type": "repo",
  "repo_slug": "engram-backend",
  "tags": ["tooling", "python"],
  "confidence": 0.9,
  "source_type": "manual",
  "requires_review": true
}
```

Behavior:

- Resolve actor/org/repo context.
- Check `can_create_memory` or `can_propose_memory`.
- Store raw observation if content came from untrusted context.
- Run Animus extraction if `process=true` or source is raw.
- For user scope, create/update the user's memory directly unless policy flags it for review later.
- For repo/org scope, default to proposal/review before the fact becomes visible to agents.
- Return proposal/fact ID and status.

#### 2. `search_memories`

Retrieves relevant memories for the agent.

Inputs:

```json
{
  "query": "How do I run tests in this repo?",
  "scopes": ["user", "repo", "org"],
  "repo_slug": "engram-backend",
  "tags": ["testing"],
  "limit": 10,
  "retrieval_mode": "auto"
}
```

Behavior:

- Resolve candidate scopes.
- Apply RBAC filters.
- Retrieve approved memories only by default.
- Use configured retrieval mode.
- Log returned memory IDs and scores.
- Return compact, citation-friendly results.

Output shape:

```json
{
  "results": [
    {
      "id": "uuid",
      "scope_type": "repo",
      "content": "Use `uv run pytest` for tests.",
      "tags": ["testing", "python"],
      "score": 0.82,
      "updated_at": "2026-07-03T00:00:00Z"
    }
  ]
}
```

#### 3. `list_memories`

Lists approved memories in a scope. This should be bounded and mostly for explicit user requests.

Inputs:

```json
{
  "scope_type": "repo",
  "repo_slug": "engram-backend",
  "tags": [],
  "limit": 50,
  "offset": 0
}
```

#### 4. `propose_memory_update`

Lets the agent suggest an update to an existing fact.

Inputs:

```json
{
  "memory_id": "uuid",
  "proposed_content": "Use `uv run pytest tests/` for test execution.",
  "reason": "README and pyproject indicate uv-based workflow."
}
```

Behavior:

- Check read access to existing memory.
- Check update/propose permission.
- Create `memory_proposals(update)`.
- Do not overwrite approved memory until review.

#### 5. `delete_memory` or `propose_memory_deletion`

Prefer proposal-first deletion for org/repo memories.

Inputs:

```json
{
  "memory_id": "uuid",
  "reason": "Fact is outdated."
}
```

Behavior:

- User-level memory: allow delete if owner.
- Repo/org memory: create deletion proposal unless actor is admin.

#### 6. `get_memory_review_status`

Useful when Claude Code saves something and wants to report what happened.

Inputs:

```json
{
  "proposal_id": "uuid"
}
```

---

## MCP Endpoint Design

### Preferred Transport

Use Streamable HTTP first.

Suggested endpoint:

```text
POST /mcp/http
GET  /mcp/http
DELETE /mcp/http
```

Example:

```text
/mcp/http
```

However, passing actor IDs in URLs can be sensitive and spoofable if not authenticated. A safer production version is:

```text
/mcp/http
```

with authentication headers resolving:

- actor user
- org
- service/client
- allowed repos

For the MCP rollout, use dashboard-generated Personal Access Tokens instead of shared config API keys or asserted user email headers. URL params for actor identity should be avoided except for local experiments. See [MCP and dashboard authentication](./mcp-phase-1-auth.md).

### Claude Code MCP Config

Target config can look like:

```json
{
  "mcpServers": {
    "engram": {
      "type": "http",
      "url": "http://localhost:8000/mcp/http",
      "headers": {
        "Authorization": "Bearer ${ENGRAM_PERSONAL_ACCESS_TOKEN}",
        "X-Engram-Client": "claude-code",
        "X-Engram-Repo": "${ENGRAM_REPO}"
      }
    }
  }
}
```

If Claude Code header interpolation is limited in your target environment, use a local wrapper or installer script that writes a concrete config.

### Context Extraction

Implement a request context builder:

```text
build_mcp_context(request)
- validate Authorization bearer Personal Access Token
- resolve actor user and org from the token owner
- resolve optional repo
- load roles/permissions
- assign request_id
- set contextvars
```

Context variables can mirror Mem0's approach:

```text
actor_context_var
org_context_var
repo_context_var
client_name_var
request_id_var
```

---

## Dashboard API Design

The UI is separate, but the backend should expose these routes.

### Memory Review APIs

```text
GET    /api/memories
GET    /api/memories/{memory_id}
POST   /api/memories
PATCH  /api/memories/{memory_id}
DELETE /api/memories/{memory_id}

GET    /api/memory-proposals
GET    /api/memory-proposals/{proposal_id}
POST   /api/memory-proposals/{proposal_id}/approve
POST   /api/memory-proposals/{proposal_id}/reject
POST   /api/memory-proposals/{proposal_id}/apply-edited
```

### Filters for Dashboard

`GET /api/memories` should support:

```text
scope_type
org_id
repo_id
owner_user_id
status
tag
created_by
approved_by
created_from
created_to
updated_from
updated_to
query
limit
offset
```

### Tags APIs

```text
GET    /api/tags
POST   /api/tags
PATCH  /api/tags/{tag_id}
DELETE /api/tags/{tag_id}
POST   /api/memories/{memory_id}/tags/{tag_id}
DELETE /api/memories/{memory_id}/tags/{tag_id}
```

### Admin/RBAC APIs

```text
GET    /api/admin/users
GET    /api/admin/roles
GET    /api/admin/role-assignments
POST   /api/admin/role-assignments
DELETE /api/admin/role-assignments/{assignment_id}
```

### Audit APIs

```text
GET /api/audit/memory-access-logs
GET /api/audit/memory-fact-versions
```

---

## Review and Approval Workflow

### New Fact Flow

```text
MCP save_memory / raw observation
        |
        v
Optional LLM extraction/canonicalization
        |
        |-- user scope -> memory_facts(approved) directly for the owner
        |
        |-- repo/org scope -> memory_proposals(create, pending)
                              |
                              v
                              Dashboard reviewer approves/rejects/edits
                              |
                              |-- approve -> memory_facts(approved) + version + Qdrant upsert
                              |-- reject -> proposal rejected
                              |-- edit + approve -> memory_facts(approved with edited content)
```

### Update Flow

```text
Existing memory
        |
        v
MCP proposes update or dashboard user edits
        |
        |-- user scope owner edit -> memory_facts updated directly
        |
        |-- repo/org scope -> memory_proposals(update, pending)
                            |
                            v
                            Reviewer approves
                            |
                            v
                            memory_facts updated
                            memory_fact_versions inserted
                            Qdrant vector refreshed
```

### Manual Edits

Manual dashboard edits are not required for phase 1, but the policy should be clear for later dashboard support.

Policy:

1. **User memory edits:** the owner can edit directly without approval.
2. **Repo/org memory edits by regular users:** create an update proposal and require review.
3. **Repo/org memory edits by users with the required admin/reviewer role:** can be applied directly later if product policy allows, but still record a version and audit event.
4. **Repo/org memory edits by users without the required role:** approval is required.
5. **Org-level facts:** prefer review unless the actor is an org admin or memory admin.

Always record:

- old content
- new content
- editor
- reason
- version
- Qdrant reindex event

---

## Retrieval Policy For Claude Code

When Claude Code asks for context, default search should combine:

1. User memories for the actor.
2. Repo memories for the current repo.
3. Org memories for the org.

Priority order:

```text
repo > user > org
```

But final ranking should consider relevance.

Suggested default limits:

```text
repo memories: up to 8
user memories: up to 5
org memories: up to 5
total: max 15
```

Return compact results, not full audit metadata.

Example result to Claude Code:

```json
{
  "results": [
    {
      "id": "...",
      "scope_type": "repo",
      "content": "This repo uses Vortex as a FastAPI wrapper and uv for dependency commands.",
      "tags": ["architecture", "tooling"],
      "source": "approved_memory",
      "score": 0.91
    }
  ]
}
```

---

## Security and Safety Requirements

1. **MCP tools must never expose pending/rejected/deleted memories by default.**
2. **Qdrant results must always be rechecked against PostgreSQL RBAC.**
3. **Org/repo memories should require review before becoming approved.**
4. **Phase 1 may skip dedicated audit-log storage**, but the model should keep audit tables in the design for later rollout. Once audit logging is enabled, every MCP search/list/read that returns memory content should be recorded.
5. **Do not store secrets as memories.** Add a secret detector before proposal creation.
6. **Add max result limits.** Avoid unbounded `list all` tools.
7. **Keep service tokens separate from actor identity.** A Claude Code token should identify the client, but requests should also resolve the human actor.
8. **Use soft delete for memory facts.** Keep history for compliance.
9. **Make review actions idempotent.** Approving an already-applied proposal should not double-apply changes.
10. **Version all prompt templates and LLM outputs.**

---

## Suggested Implementation Phases

### Phase 1: Core Database + Manual APIs

- Add Tortoise ORM models and migration/bootstrap workflow.
- Create identity, memory, tag, proposal, version, and audit models.
- Implement RBAC checks.
- Add dashboard-ready REST APIs for memories/proposals/tags.
- Skip Qdrant initially or keep it behind a disabled config flag.

### Phase 2: MCP for Claude Code

- Add FastMCP server router.
- Implement context extraction from token/headers.
- Add tools:
  - `save_memory`
  - `search_memories`
  - `list_memories`
  - `propose_memory_update`
  - `propose_memory_deletion`
  - `get_memory_review_status`
- Add access logs for all MCP operations.
- Provide Claude Code config/install instructions.

### Phase 3: Animus Processing

- Add `memory_processing_service.py`.
- Create prompt templates and Pydantic output schemas.
- Convert raw observations to proposals.
- Add duplicate detection using lexical matching first.
- Store raw observations in phase 1 for audit/reprocessing. Add secret/sensitive-data detection as a follow-up guardrail before broader rollout, and avoid promoting obvious secrets into approved facts.

### Phase 4: Qdrant Retrieval

- Add Qdrant collection management.
- Add embedding generation through Animus-compatible helpers/classes behind `MemoryEmbeddingService`.
- Upsert approved facts to Qdrant.
- Refresh vectors on approved edits.
- Implement semantic/hybrid search.
- Add reindex command/job.

### Phase 5: Review UX Support

- Add proposal assignment/queue filters.
- Add reviewer comments.
- Add bulk approve/reject for trusted imports.
- Add memory quality scores and stale-memory detection.

---

## Initial Config Additions

Extend `config_template.json` with sections like:

```json
{
  "ENGRAM": {
    "MCP_SERVER_NAME": "engram-mcp",
    "DEFAULT_RETRIEVAL_MODE": "lexical",
    "MAX_SEARCH_RESULTS": 20,
    "REQUIRE_REVIEW_FOR_REPO_MEMORY": true,
    "REQUIRE_REVIEW_FOR_ORG_MEMORY": true,
    "ALLOW_USER_MEMORY_AUTO_APPROVE": true
  },
  "QDRANT": {
    "ENABLED": false,
    "URL": "http://localhost:6333",
    "API_KEY": "",
    "COLLECTION_STRATEGY": "per_environment",
    "COLLECTION_PREFIX": "engram_memories",
    "COLLECTION": "engram_memories_dev"
  },
  "EMBEDDINGS": {
    "ENABLED": false,
    "MODEL": "openai:text-embedding-3-large",
    "FALLBACK_MODEL": "google:gemini-embedding-2",
    "DIMENSIONS": null,
    "BATCH_SIZE": 64,
    "INSTRUMENT": true
  },
  "MEMORY_PROCESSING": {
    "ENABLED": true,
    "EXTRACTION_MODEL": "",
    "AUTO_TAGGING_ENABLED": true,
    "SECRET_DETECTION_ENABLED": false
  },
  "ENGRAM_AUTH": {
    "MODE": "google_workspace_oidc",
    "PHASE1_HEADER_ENABLED": false,
    "ALLOWED_EMAIL_DOMAINS": ["1mg.com"],
    "DEFAULT_ORG_SLUG": "tata1mg",
    "ADMIN_EMAILS": [],
    "AUTO_PROVISION_USERS": true,
    "PERSONAL_ACCESS_TOKENS_ENABLED": true,
    "PERSONAL_ACCESS_TOKEN_PREFIX": "engpat"
  }
}
```

---

## MVP Decisions Recommended Now

1. **Use PostgreSQL as the source of truth.**
2. **Store all memory facts with a strict scope.** No global unscoped memories.
3. **Default repo/org memories to pending review.**
4. **Allow user memories to be created/edited without approval by default.**
5. **Implement lexical search first, but design every interface with `retrieval_mode`.**
6. **Add Qdrant only after the first MCP loop works.** Use one Qdrant deployment with multiple collections.
7. **Return only approved memories to Claude Code.**
8. **Keep audit logging designed but optional in phase 1.** Dedicated memory-return audit logs can be deferred until after the first MCP loop works.
9. **Keep tool count small for Claude Code rollout.** Start with save/search/list/propose-update/propose-delete/status.
10. **Make dashboard APIs first-class even before UI exists.** This prevents MCP-only shortcuts that are hard to govern later.

---

## Resolved Implementation Decisions

1. **Persistence:** Use Tortoise ORM for memory-bank persistence. Remove or ignore SQLAlchemy unless a separate framework requirement appears.
2. **Auth domain:** Google Workspace OAuth accepts only verified `@1mg.com` users; MCP uses web-generated Personal Access Tokens owned by those users.
3. **User provisioning:** Auto-provision unknown valid-domain users from email. Use the email local part as the fallback display name; admins assign roles later through dashboard/API flows.
4. **Repository metadata:** Send as much Git metadata as the Claude Code/plugin setup can reliably collect (`origin_url`, `git_root`, `branch`, `commit_sha`, `repo_dir_name`). Treat `X-Engram-Repo` as a fallback hint.
5. **Embedding default:** Use `openai:text-embedding-3-large` first. If that fails or is unavailable, use Gemini embeddings, preferably `google:gemini-embedding-2`. Do not plan for local embeddings in this rollout.
6. **Raw observations:** Store raw observations in phase 1. Add secret detection/redaction later before wider or more sensitive rollout.

## Implementation Follow-ups

1. **Claude Code plugin validation:** Use the plugin distribution plan in [MCP and dashboard authentication](./mcp-phase-1-auth.md) as the preferred rollout path, then validate it against the installed Claude Code CLI version.
2. **Internal plugin hosting:** Decide where the internal Claude Code plugin repository or marketplace will live.
3. **Installer fallback:** If plugin `userConfig` interpolation does not work in the target CLI version, provide a generated `.mcp.json` installer or wrapper script.