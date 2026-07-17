# Engram Implementation Checklist

## Purpose

This document turns the current Engram design into an implementation sequence that another agent or developer can follow task-by-task.

It is intentionally focused on **what to build and in what order**, not low-level implementation details. For deeper design, refer to:

- `docs/memory-bank-implementation-plan.md`
- `docs/repository-scope-resolution.md`
- `docs/mcp-phase-1-auth.md`
- `docs/embedding-retrieval-design.md`
- `docs/animus.md`

---

## Product Direction

Build an internal, organization-grade memory bank for coding agents, starting with Claude Code over MCP.

The app should support:

- User-level memories.
- Repository-level memories.
- Organization-level memories.
- Review workflow for repo/org memories.
- Repository-aware retrieval.
- Safe MCP tools.
- Dashboard-ready APIs.
- Future semantic retrieval through Qdrant.
- Future LLM processing through Animus.

Use Mem0/OpenMemory as a reference for:

- MCP tool registration.
- Lazy dependency initialization.
- Graceful degraded mode.
- Compact memory search responses.
- Access logs and status history.
- Vector search patterns.

Do **not** directly copy Mem0’s user/app-only memory model. Engram needs stricter organization/repository scoping, RBAC, and approval workflows.

---

## Core Architecture Rules

Before implementation starts, keep these rules fixed:

- [ ] PostgreSQL is the source of truth.
- [ ] Qdrant is a derived/rebuildable index only.
- [ ] Memory facts must always have exactly one primary scope: `user`, `repo`, or `org`.
- [ ] Repository identity must use canonical Git remote resolution, not local folder path.
- [ ] MCP tools must resolve an internal `ActorContext` before doing work.
- [ ] MCP tools must not directly bypass RBAC or review policy.
- [ ] Repo/org memories should default to pending review.
- [ ] User memories may auto-approve only when policy allows.
- [ ] Pending/rejected/deleted memories must not be returned to agents by default.
- [ ] Qdrant results must always be rechecked against PostgreSQL status and RBAC.
- [ ] Animus should assist with extraction/classification, but application DB owns memory persistence.

---

## Recommended MVP Goal

The first complete MVP should prove this loop:

```text
Claude Code connects over MCP
        |
        v
Backend resolves actor + organization + repository
        |
        v
Agent saves a repository memory
        |
        v
Memory becomes a pending proposal
        |
        v
Reviewer approves proposal through API
        |
        v
Memory becomes approved fact
        |
        v
Agent searches and receives approved repo/user/org memories
```

Everything else should support this loop.

---

# Current Implementation Snapshot

Last updated after the Phase 12 MCP/audit slice, UI milestone 3 memory browser, and config alignment.

## Completed in Code

- Added modular ORM model files under `models/`:
  - `models/base.py`
  - `models/identity.py`
  - `models/repository.py`
  - `models/memory.py`
  - `models/review.py`
  - `models/audit.py`
- Added modular Pydantic/schema files under `schemas/`:
  - `schemas/base.py`
  - `schemas/enums.py`
  - `schemas/context.py`
  - `schemas/repository.py`
  - `schemas/memory.py`
  - `schemas/review.py`
  - `schemas/mcp.py`
- Added service-layer foundations under `services/`:
  - `services/config_service.py`
  - `services/actor_context.py`
  - `services/auth_context_service.py`
  - `services/repository_resolver.py`
  - `services/rbac_service.py`
  - `services/memory_service.py`
  - `services/safety_service.py`
  - `services/memory_retrieval_service.py`
  - `services/dashboard_memory_service.py`
  - `services/tag_service.py`
  - `services/admin_service.py`
  - `services/audit_query_service.py`
- Added dashboard REST routers under `routers/`:
  - `routers/dependencies.py`
  - `routers/memories.py`
  - `routers/memory_proposals.py`
  - `routers/tags.py`
  - `routers/admin.py`
  - `routers/audit.py`
- Added UI service-layer alignment plan in `engram-ui/docs/frontend-feature-build-plan.md`.
  - Frontend will target both regular developers and admin/reviewer users.
  - Frontend can add shadcn components, Sonner, TanStack Query, and Zustand where useful.
  - Backend follow-up APIs are needed for repository/organization/scope discovery.
- Completed initial UI milestones 1–2 in `engram-ui`.
  - Dedicated routes now exist for overview, memories, proposals, tags, audit, admin, and settings.
  - Overview continues to reuse existing dashboard REST APIs through the frontend service layer.
  - TanStack Query is mounted through a small query provider for server-state caching/refetching.
  - Sonner remains root-mounted and a reusable mutation toast helper is available for future writes.
  - Zustand was not added because no shared client-only state is needed yet.
- Completed UI milestone 3 memory list/detail browser in `engram-ui`.
  - `/memories` lists memory facts through `listMemories(params)` only.
  - URL-friendly filters cover query, status, scope type, tag, limit, and offset.
  - Selected memory detail opens in a sheet and loads through `getMemory(memoryId)` only.
  - Shared frontend components now include `DataState`, `JsonPreview`, `PaginationControls`, and `StatusBadge`.
  - Feature code is modular under `src/pages/memories/` with `components/`, `hooks/`, `constants.ts`, and `types.ts`.
- Aligned UI config usage in `engram-ui`.
  - Added typed `src/lib/appConfig.ts` adapter over `config.json`.
  - Added `ENGRAM_UI` keys to `config.json` and `config_template.json` for query and memory-browser defaults.
  - Settings now displays safe config values while hiding secrets.
  - HTTP timeout, router base path, query defaults, and memory page-size options are config-backed.
- Sanitized disabled local backend secrets in `config.json`.
  - Qdrant remains disabled and now has empty local `URL`/`API_KEY` placeholders.
  - OpenAI remains unused for the current loop and now has an empty local `API_KEY` placeholder.
- Registered app model modules directly in Tortoise config instead of importing through `models/__init__.py`.
- Added missing Engram config sections to local `config.json`.
- Kept Qdrant disabled and memory processing disabled for the first manual DB/review loop.
- Verified Python compile/imports and non-DB Tortoise model initialization.
- Verified `services/memory_service.py`, `services/memory_retrieval_service.py`, `services/safety_service.py`, and `schemas/memory.py` with compile, import, hash-generation/safety/retrieval smoke, and Ruff checks.
- Verified Phase 10 REST router/service/schema import, compile, Ruff, app route registration smoke, and read-only configured-DB service query smoke.
- Verified configured Tortoise DB init/close, DB listener setup/teardown, FastAPI lifespan startup/shutdown, and read access to generated core tables.
- Added no new dependencies for the Phase 7 service-complete and Phase 8 safety slices; existing stdlib/Tortoise/Starlette stack was enough.

## Not Done Yet / Requires Verification

- Memory update/delete/archive flows are implemented at service level, but mutation DB smoke through a disposable dataset is still pending.
- No migration strategy has been added yet; schemas are currently generated out-of-band and the DB listener does not call `Tortoise.generate_schemas`.
- UI proposal/tag/admin/audit feature pages are still placeholder surfaces after milestone 3; proposal review queue is the next frontend milestone.
- UI feature build needs backend repository/organization/scope discovery APIs so users do not paste raw scope UUIDs.
- UI proposal review can build a simple diff by fetching `fact_id`, but proposal detail response expansion may be useful later.
- Delete-vs-archive product behavior/copy remains TBD and should be clarified before final UI mutation copy.
- Audit APIs currently return IDs; optional display-field enrichment can improve UI readability later.

## New Cleanup / Alignment Items

- [ ] Decide whether to remove `sqlalchemy` from `pyproject.toml`; current plan uses Tortoise only.
- [ ] Decide whether `animus` should remain an installed dependency while disabled, or be made optional/later.
- [x] Do not add a new dependency for Phase 7 create/propose/approve/reject flows.
- [x] Replace committed local secrets in `config.json` with safe local placeholders or env-driven config before wider sharing.
  - Sanitized disabled Qdrant and OpenAI local values; keep all future secrets out of committed config files.
- [x] Add DB smoke command/process once PostgreSQL credentials/environment are confirmed.
  - Verified configured Tortoise init/close, DB listener setup/teardown, FastAPI lifespan startup/shutdown, and read access to generated core tables.
- [ ] Keep package `__init__.py` files minimal; import concrete modules directly from services/routers.
- [ ] Add backend repository discovery APIs for UI scope selectors.
- [ ] Add organization/scope discovery APIs or a consolidated `/api/scopes` endpoint.
- [ ] Decide delete-vs-archive behavior/copy for dashboard memory removal flows.
- [ ] Consider proposal detail response expansion for current-vs-proposed diff rendering.
- [ ] Consider audit response enrichment with actor email/repository display fields.

## Immediate Next Step

Continue with UI proposal review work while keeping dashboard support APIs stable:

1. Build the UI proposal review queue over existing proposal APIs and fetch current memory facts through `getMemory(factId)` for MVP diff support.
2. Add repository/organization/scope discovery REST APIs before normal users need scope selectors for create/filter flows.
3. Keep existing memory/proposal/tag/admin/audit APIs stable for UI feature pages.
4. Clarify delete-vs-archive behavior before final dashboard removal copy.
5. Keep Qdrant/semantic retrieval as a later derived-index path; Phase 9 remains PostgreSQL lexical retrieval.

---

# Phase 0: Project Alignment and Scope Lock

## Goal

Prepare the repository for implementation and avoid premature Qdrant/LLM complexity.

## Checklist

- [x] Confirm `engram-backend` remains the backend service repo.
- [x] Confirm Vortex remains the FastAPI wrapper.
- [x] Confirm Tortoise ORM is the persistence layer.
- [x] Treat SQLAlchemy as unnecessary unless a separate requirement appears.
  - Follow-up: remove the dependency if no existing Vortex/Animus path needs it.
- [x] Confirm PostgreSQL is required for real app behavior.
- [x] Confirm Qdrant is disabled for the first working loop.
- [x] Confirm Animus is not required for the first manual memory loop.
- [x] Confirm target auth is Google OAuth for dashboard and web-generated Personal Access Tokens for MCP.
- [x] Confirm allowed Google Workspace email domain is `1mg.com`.
- [x] Confirm only `user`, `repo`, and `org` scopes are part of phase 1.

## Definition of Done

- [x] The next agent understands that Phase 1 is DB/manual/lexical-first.
- [x] No work starts with Qdrant, embeddings, or Animus unless the core loop is complete.

---

# Phase 1: Configuration and App Bootstrap

## Goal

Make runtime configuration and application startup ready for Engram components.

## Checklist

- [x] Review `config_template.json` and ensure required sections exist:
  - [x] `ENGRAM`
  - [x] `ENGRAM_AUTH`
  - [x] `MEMORY_PROCESSING`
  - [x] `EMBEDDINGS`
  - [x] `QDRANT`
- [x] Ensure local `config.json` follows the template shape.
- [x] Add backend config helpers if existing Vortex `CONFIG.config` access is too raw.
  - Implemented in `services/config_service.py`.
- [x] Confirm DB connection config includes this project’s app models, not only Animus models.
- [x] Confirm startup/shutdown listeners initialize and close Tortoise cleanly against an actual configured DB.
  - Verified with configured DB listener setup/teardown smoke.
- [x] Keep Qdrant and Animus initialization lazy or disabled by config.
- [ ] Add a simple internal health/readiness distinction later if needed:
  - [ ] app alive
  - [ ] database ready
  - [ ] optional services ready

## Definition of Done

- [x] App starts with current config.
  - Verified with in-process FastAPI lifespan startup/shutdown smoke.
- [x] Database models can be registered by Tortoise.
  - Verified with non-DB Tortoise model initialization.
- [x] Optional systems being disabled does not block import/config validation.

---

# Phase 2: Core Database Models

## Goal

Create the canonical data model before MCP tools or retrieval logic.

## Recommended Files

- `models/base.py`
- `models/identity.py`
- `models/repository.py`
- `models/memory.py`
- `models/review.py`
- `models/audit.py`

## Checklist

### Identity Models

- [x] Add `User` model.
- [x] Add `Organization` model.
- [x] Add `Role` model.
- [x] Add `RoleAssignment` model.

### Repository Models

- [x] Add `Repository` model.
- [x] Add `RepositoryAlias` model or reserve for Phase 2.5 if you want MVP smaller.
- [x] Include repository fields needed for canonical Git remote identity:
  - [x] `org_id`
  - [x] `provider`
  - [x] `host`
  - [x] `workspace`
  - [x] `repo_slug`
  - [x] `repository_key`
  - [x] `canonical_remote_url`
  - [x] `resolver_source`
  - [x] `resolver_confidence`
  - [x] `metadata`
- [x] Add uniqueness rule for `(org_id, repository_key)`.

### Memory Models

- [x] Add `MemoryFact` model.
- [x] Add `MemoryObservation` model.
- [x] Add `MemoryProposal` model.
- [x] Add `MemoryFactVersion` model.
- [x] Add `Tag` model.
- [x] Add `MemoryFactTag` mapping.

### Audit Models

- [x] Add `MemoryAccessLog` model.
- [x] Add enough fields to audit search/list/read/write/review actions.
- [x] Keep audit logging optional in first pass, but model should exist.

## Definition of Done

- [x] Models load without import cycles.
- [x] Generated tables are present and readable in local/dev DB.
  - Verified read access to core identity/repository/memory/review tables after schema generation.
- [x] Core constraints exist for users, orgs, repos, facts, proposals, and tags.
- [x] Every memory fact has `org_id`, `scope_type`, `scope_id`, and `status`.

---

# Phase 3: Schemas and Enums

## Goal

Define stable request/response contracts before services and routers grow.

## Recommended Files

- `schemas/context.py`
- `schemas/repository.py`
- `schemas/memory.py`
- `schemas/review.py`
- `schemas/mcp.py`

## Checklist

- [x] Define enums:
  - [x] `ScopeType`: `user`, `repo`, `org`
  - [x] `MemoryStatus`: `pending_review`, `approved`, `rejected`, `archived`, `deleted`, `superseded`
  - [x] `ProposalType`: `create`, `update`, `delete`, `merge`
  - [x] `ProposalStatus`: `pending`, `approved`, `rejected`, `applied`, `cancelled`
  - [x] `MemorySource`: `mcp`, `dashboard`, `import`, `system`, `hook`
  - [x] `RetrievalMode`: `auto`, `lexical`, `all_scoped`, `semantic`, `hybrid`
- [x] Define `ActorContext` schema/dataclass.
- [x] Define `RepositoryContext` schema/dataclass.
- [x] Define memory create/proposal/search/list request schemas.
- [x] Define compact MCP response schemas.
- [x] Define dashboard response schemas with enough metadata for review UI.
  - Initial response contracts exist; router-specific refinements can happen when APIs are implemented.

## Definition of Done

- [x] Service and router code can rely on typed schemas.
- [x] MCP response shapes are compact and agent-friendly.
- [x] Dashboard response shapes preserve enough review/audit information for first APIs.

---

# Phase 4: Google OAuth, Personal Access Tokens, and Actor Context

## Goal

Resolve every MCP/dashboard request into a trusted internal context object without shared config API keys or asserted user email headers.

## Recommended Files

- `services/auth_context_service.py`
- `services/google_oauth_service.py`
- `services/session_service.py`
- `services/token_service.py`
- `services/personal_access_token_service.py`
- `services/user_identity_service.py`
- `services/actor_context.py`
- `routers/auth.py`
- `routers/personal_access_tokens.py`
- `schemas/auth.py`
- `schemas/context.py`

## Current Status

- `schemas/context.py` exists with `ActorContext` and `RequestContext`.
- `services/actor_context.py` exists for request-safe context variables.
- `services/auth_context_service.py` is now the intended dispatcher boundary for web-cookie and Personal Access Token credentials.
- Shared config API key/secret auth is no longer the target path.
- Pending implementation: Google OAuth callback/session services and Personal Access Token create/list/revoke/verify services.

## Checklist

- [ ] Implement Google OAuth login/callback for dashboard.
- [ ] Verify Google ID token and enforce verified `@1mg.com` users.
- [ ] Store Google `sub` in a `UserIdentity` record.
- [ ] Create backend web sessions/JWTs after Google login.
- [ ] Resolve dashboard requests from HttpOnly web cookie into `ActorContext(auth_method=oauth_web_cookie)`.
- [ ] Add dashboard-authenticated Personal Access Token endpoints:
  - [ ] list token metadata,
  - [ ] create token and show raw value once,
  - [ ] revoke token.
- [ ] Store only hashed/HMACed Personal Access Tokens.
- [ ] Resolve MCP requests from `Authorization: Bearer <PAT>` into `ActorContext(auth_method=personal_access_token)`.
- [ ] Do not accept `X-Engram-User-Email` for MCP identity.
- [ ] Do not require or document shared `X-Engram-Api-Key` / `X-Engram-Api-Secret` headers.
- [ ] Resolve default organization from config.
- [ ] Load admin emails from config for initial role assignment or admin checks.
- [ ] Store context in request-safe context variables where useful.

## Definition of Done

- [ ] Requests without a valid web cookie or PAT fail with `401`.
- [ ] Requests with invalid Google domain fail with `403`.
- [ ] Valid unknown Workspace users can be auto-provisioned if config allows.
- [ ] Revoked or expired Personal Access Tokens fail with `401`.
- [ ] Application services do not read raw auth headers directly.
- [ ] MCP tools and dashboard APIs both consume only `ActorContext`.

---

# Phase 5: Repository Resolver

## Goal

Resolve repository identity automatically from Git metadata.

## Recommended Files

- `services/repository_resolver.py`
- `schemas/repository.py`
- `models/repository.py`

## Current Status

- `schemas/repository.py` and `models/repository.py` exist.
- `services/repository_resolver.py` exists with Bitbucket normalization, repository upsert, explicit ID validation, and low-confidence basename fallback.
- Pending integration: attach resolved `RepositoryContext` to MCP/API request context when routers are added.

## Checklist

- [x] Implement normalization for Bitbucket remotes:
  - [x] `git@bitbucket.org:tata1mg/repo.git`
  - [x] `ssh://git@bitbucket.org/tata1mg/repo.git`
  - [x] `https://bitbucket.org/tata1mg/repo.git`
  - [x] `https://username@bitbucket.org/tata1mg/repo.git`
- [x] Strip HTTPS usernames.
- [x] Strip `.git` suffix.
- [x] Lowercase host/workspace/repo slug.
- [x] Produce canonical key:
  - [x] `bitbucket.org/<workspace>/<repo_slug>`
- [x] Upsert repository row by `(org_id, repository_key)`.
- [x] Return `RepositoryContext` with confidence and source.
- [x] Support low-confidence basename fallback only if no remote exists.
- [x] Do not use local filesystem path as durable repo identity.
- [x] Treat branch and commit as metadata only.
- [x] If explicit `repo_id` and `origin_url` both exist, validate they match.

## Definition of Done

- [x] SSH and HTTPS Bitbucket remotes resolve to the same repository key.
  - Verified with local non-DB normalization examples.
- [ ] Repository context can be attached to MCP requests.
  - Resolver exists; MCP/API integration pending.
- [x] Repo-scoped memories can use `scope_type = repo` and `scope_id = repository.id`.
  - Model/schema support exists.

---

# Phase 6: RBAC Service Skeleton

## Goal

Centralize permission decisions before memory services and MCP tools are built.

## Recommended File

- `services/rbac_service.py`

## Checklist

- [x] Implement basic permission methods:
  - [x] `can_read_memory(actor, memory)`
  - [x] `can_create_memory(actor, scope_type, scope_id)`
  - [x] `can_propose_memory(actor, scope_type, scope_id)`
  - [x] `can_approve_memory(actor, proposal_or_memory)`
  - [x] `can_edit_memory(actor, memory)`
  - [x] `can_delete_memory(actor, memory)`
  - [x] `can_manage_tags(actor, org_id)`
- [x] Phase-1 default behavior:
  - [x] actor can read own user memories
  - [x] actor can create own user memories
  - [x] actor can propose repo/org memories
  - [x] admin emails can approve repo/org proposals
  - [x] repo/org direct writes are not allowed for regular users
- [x] Keep room for repo-level roles later.
  - Current implementation is role-string based and can be expanded behind `ActorContext`.

## Definition of Done

- [x] No service or router implements ad-hoc permission logic.
  - `services/memory_service.py` now calls the RBAC boundary for create/propose/review flows.
- [ ] MCP tools call services that enforce RBAC.
  - Pending MCP tools.
- [ ] Dashboard APIs can reuse the same checks.
  - Pending REST APIs.

---

# Phase 7: Core Memory Service

## Goal

Create, update, approve, reject, archive, and delete memories through one service layer.

## Recommended File

- `services/memory_service.py`

## Checklist

- [x] Implement direct user memory creation.
- [x] Implement repo/org memory proposal creation.
- [x] Implement proposal approval for create proposals.
- [x] Implement proposal rejection.
- [x] Implement edited approval.
- [x] Implement update proposal creation.
- [x] Implement deletion proposal creation.
- [x] Implement user-owned memory direct delete/archive.
- [x] Implement version insertion for approved create actions.
- [x] Extend version insertion to approved update/delete/archive actions.
- [x] Generate and store content hashes for memory facts.
- [x] Generate and store content hashes for create proposals.
- [x] Ensure approval is idempotent for already-applied proposals.
- [x] Ensure rejected/cancelled proposals cannot be applied.
- [x] Keep raw observations linked to proposals where available.
- [x] Add create-proposal idempotency-key reuse handling.
- [x] Add service-level scope validation for user/repo/org writes.

## Definition of Done

- [x] User memory can be created as approved fact at service level.
  - DB runtime smoke test still pending.
- [x] Repo/org memory can be created as pending proposal at service level.
  - DB runtime smoke test still pending.
- [x] Create-proposal approval creates an approved `MemoryFact` and a version row at service level.
  - DB runtime smoke test still pending.
- [x] Proposal rejection does not create an approved fact.
- [x] Update/delete proposals do not mutate approved memory until approved.
  - Implemented at service level; disposable mutation DB smoke is still pending.

---

# Phase 8: Basic Secret and Sensitivity Guardrail

## Goal

Avoid promoting obvious secrets into approved memory.

## Recommended File

- `services/safety_service.py`

## Checklist

- [x] Add basic detection for obvious secrets:
  - [x] private key blocks
  - [x] API-key-looking values
  - [x] JWT-looking tokens
  - [x] `.env` assignment patterns
  - [x] long high-entropy strings
  - [x] password/secret/token field names
- [x] Add `contains_possible_secret` metadata on observations/proposals.
- [x] Block auto-approval if secret-like content is detected.
- [x] Allow proposal creation with warning metadata only if product policy allows.
- [x] Never return secret-flagged pending content through MCP search.
  - MCP search/list call the approved-memory retrieval service only and never return pending proposals.

## Definition of Done

- [x] Obvious secrets are not auto-approved.
- [x] Reviewers can identify flagged proposals.
- [x] Search returns only approved safe facts.
  - Implemented through lexical retrieval and MCP search/list wiring.

---

# Phase 9: Lexical Retrieval Service

## Goal

Implement useful search before Qdrant exists.

## Recommended File

- `services/memory_retrieval_service.py`

## Checklist

- [x] Implement scoped approved-memory search from PostgreSQL.
- [x] Support default scopes for coding agents:
  - [x] current repo
  - [x] current user
  - [x] current org
- [x] Apply RBAC checks before returning results.
- [x] Support basic query matching over:
  - [x] content
  - [x] summary
  - [x] tags
  - [x] repository display fields where useful
- [x] Enforce strict limits:
  - [x] default limit
  - [x] max limit
  - [x] per-scope limits if configured
- [x] Return compact result objects for MCP.
- [x] Add score field even if lexical scoring is simple initially.
- [x] Do not return pending/rejected/deleted facts.

## Definition of Done

- [x] Approved facts can be searched by content.
- [x] Repo search automatically includes current repo facts.
- [x] User/org facts can be included in default search.
- [x] Results are bounded and compact.

---

# Phase 10: Dashboard-Ready REST APIs

## Goal

Expose governance APIs before the UI exists.

## Recommended Files

- `routers/memories.py`
- `routers/memory_proposals.py`
- `routers/tags.py`
- `routers/admin.py`
- `routers/audit.py`

## Checklist

### Memory APIs

- [x] `GET /api/memories`
- [x] `GET /api/memories/{memory_id}`
- [x] `POST /api/memories`
- [x] `PATCH /api/memories/{memory_id}`
- [x] `DELETE /api/memories/{memory_id}`
- [x] Add documented dashboard filters for scope/org/repo/owner/status/tag/creator/approver/date/query/limit/offset.

### Proposal APIs

- [x] `GET /api/memory-proposals`
- [x] `GET /api/memory-proposals/{proposal_id}`
- [x] `POST /api/memory-proposals/{proposal_id}/approve`
- [x] `POST /api/memory-proposals/{proposal_id}/reject`
- [x] `POST /api/memory-proposals/{proposal_id}/apply-edited`

### Tag APIs

- [x] `GET /api/tags`
- [x] `POST /api/tags`
- [x] `PATCH /api/tags/{tag_id}`
- [x] `DELETE /api/tags/{tag_id}`
- [x] `POST /api/memories/{memory_id}/tags/{tag_id}`
- [x] `DELETE /api/memories/{memory_id}/tags/{tag_id}`

### Admin APIs

- [x] `GET /api/admin/users`
- [x] `GET /api/admin/roles`
- [x] `GET /api/admin/role-assignments`
- [x] `POST /api/admin/role-assignments`
- [x] `DELETE /api/admin/role-assignments/{assignment_id}`

### Audit Read APIs

- [x] `GET /api/audit/memory-access-logs`
- [x] `GET /api/audit/memory-fact-versions`

## Definition of Done

- [x] Proposals can be reviewed without MCP.
- [x] Memory facts can be listed and filtered.
- [x] Tags can be managed minimally.
- [x] Admin users can inspect users/roles.

---

# Phase 11: MCP Server and Tools

## Goal

Expose the memory loop to Claude Code through MCP.

## Recommended Files

- `routers/mcp_router.py`
- `services/mcp_context_service.py`
- `schemas/mcp.py`

## Mem0 Reference Patterns to Reuse

- [x] Use direct MCP tool registration similar to OpenMemory.
- [x] Use request context variables for resolved context.
- [x] Support Streamable HTTP first. [only keep HTTP]
- [x] do not implement SSE.  [ignore SSE]
- [x] Lazily initialize optional services.
- [x] Return safe errors if optional systems are unavailable.

## Checklist

- [x] Create FastMCP server instance.
- [x] Mount endpoint similar to:
  - [x] `/mcp/http`
- [x] Build MCP context from headers for each request.
- [x] Resolve repository context from provided metadata or fallback hint.
- [x] Implement tools:
  - [x] `save_memories`
  - [x] `search_memories`
  - [x] `list_memories`
  - [x] `propose_memory_update`
  - [x] `propose_memory_deletion`
  - [x] `get_memory_review_status`
- [x] Ensure tools call service layer, not models directly.
- [x] Ensure tools return compact JSON strings/objects suitable for agents.
- [x] Ensure every tool enforces limits.
- [x] Avoid user identity in URL for non-local flows.

## Definition of Done

- [x] Claude Code can connect to MCP endpoint.
  - One MCP tool was manually smoke-tested successfully.
- [x] MCP request resolves actor and repo context.
- [x] Agent can save a memory.
- [x] Repo/org save creates a proposal.
- [x] Agent can search approved memories.
- [x] Agent cannot retrieve pending/rejected/deleted memories.

---

# Phase 12: Audit Logging

## Goal

Record important memory access and mutation events.

## Recommended File

- `services/audit_service.py`

## Checklist

- [x] Log memory searches.
- [x] Log memory list operations.
- [x] Log memory reads.
- [x] Log memory creates.
- [x] Log proposal creates.
- [x] Log proposal approvals/rejections.
- [x] Log deletes/archives.
- [x] Include useful metadata:
  - [x] request ID
  - [x] actor user ID
  - [x] client name
  - [x] query text or hash
  - [x] returned memory IDs
  - [x] scores when available
  - [x] scope filters
- [x] Keep logging failures non-fatal where possible.

## Definition of Done

- [x] Review actions are auditable.
- [x] MCP searches that return content are auditable.
- [x] Debugging a memory result is possible from logs.

---

# Phase 13: Claude Code Local Setup / Plugin Path

## Goal

Make it easy for internal users to connect Claude Code to the backend.

## Checklist

- [ ] Start with manual MCP config example.
- [ ] Validate header interpolation in the target Claude Code version.
- [ ] If interpolation works, prepare plugin config using user-config values.
- [ ] If interpolation does not work, build an installer/wrapper fallback that writes local config.
- [ ] Collect repository metadata non-blockingly:
  - [ ] `git rev-parse --show-toplevel`
  - [ ] `git config --get remote.origin.url`
  - [ ] `git branch --show-current`
  - [ ] `git rev-parse HEAD`
  - [ ] basename of Git root
- [ ] Send repository metadata with MCP requests if client/plugin supports it.
- [ ] Keep `X-Engram-Repo` as fallback only.

## Definition of Done

- [ ] A developer can configure Claude Code locally.
- [ ] Backend receives actor headers.
- [ ] Backend receives or derives repository metadata.
- [ ] Git metadata collection failure does not block agent usage.

---

# Phase 14: Animus Memory Processing

## Goal

Use Animus to convert raw observations into structured memory proposals.

## Recommended File

- `services/memory_processing_service.py`

## Checklist

- [ ] Define prompt registry:
  - [ ] `MEMORY_EXTRACTION_PROMPT_V1`
  - [ ] `MEMORY_DEDUP_PROMPT_V1`
  - [ ] `MEMORY_RERANK_PROMPT_V1` later
- [ ] Define structured output schema:
  - [ ] action: create/update/ignore
  - [ ] scope type
  - [ ] canonical content
  - [ ] summary
  - [ ] tags
  - [ ] confidence
  - [ ] sensitivity
  - [ ] requires review
  - [ ] reason
- [ ] Validate LLM output with Pydantic before storage.
- [ ] Store prompt version and model metadata in proposal metadata.
- [ ] Use lexical duplicate candidates before asking Animus to reason.
- [ ] Keep user memory auto-approval policy separate from LLM output.
- [ ] Keep repo/org memories as proposals by default.
- [ ] Make Animus unavailable state degrade to raw proposal/manual flow.

## Definition of Done

- [ ] Raw observations can become structured proposals.
- [ ] Bad/invalid LLM output does not corrupt memory tables.
- [ ] Prompt/model metadata is stored for audit and future reprocessing.

---

# Phase 15: Qdrant and Embedding Readiness

## Goal

Add semantic retrieval only after the DB/MCP/review loop is already working.

## Recommended Files

- `services/memory_embedding_service.py`
- `services/qdrant_service.py`

## Checklist

- [ ] Implement `MemoryEmbeddingService` boundary.
- [ ] Hide concrete Animus-compatible embedding implementation behind the service.
- [ ] Add deterministic fake embedding implementation for tests/dev if needed.
- [ ] Create Qdrant collection based on configured model dimensions.
- [ ] Use one collection per environment first.
- [ ] Store only approved memory facts in Qdrant.
- [ ] Use one vector per approved fact initially.
- [ ] Include payload metadata:
  - [ ] memory fact ID
  - [ ] org ID
  - [ ] scope type
  - [ ] scope ID
  - [ ] repo ID
  - [ ] owner user ID
  - [ ] status
  - [ ] tag slugs
  - [ ] embedding model
  - [ ] embedding dimensions
  - [ ] content hash
- [ ] Upsert vector after approval.
- [ ] Refresh vector after approved edit.
- [ ] Delete or deactivate vector after archive/delete/rejection.
- [ ] Always re-fetch candidate facts from PostgreSQL before returning results.

## Definition of Done

- [ ] Semantic search works behind a config flag.
- [ ] Qdrant can be rebuilt from PostgreSQL.
- [ ] Model/dimension metadata is stored.
- [ ] Authorization never depends only on Qdrant filters.

---

# Phase 16: Hybrid Retrieval and Ranking

## Goal

Improve retrieval quality after semantic search exists.

## Checklist

- [ ] Combine lexical candidates and semantic candidates.
- [ ] Normalize scores into a common range.
- [ ] Prefer repo facts when relevance is close.
- [ ] Include user/org facts where relevant.
- [ ] Consider exact identifier matches for code terms.
- [ ] Add reranking only if search quality is insufficient.
- [ ] Keep response compact for MCP.

## Definition of Done

- [ ] Search can find both semantic matches and exact code identifiers.
- [ ] Retrieval quality improves without increasing context too much.

---

# Phase 17: Repository Aliases and Merge Support

## Goal

Handle renamed repos, duplicate discovery, and low-confidence fallback reconciliation.

## Checklist

- [ ] Add repository alias model if not already added.
- [ ] Resolve aliases during repository lookup.
- [ ] Add merged/inactive repository status fields.
- [ ] Add admin merge API.
- [ ] Move repo-scoped memories from source repo to canonical repo during merge.
- [ ] Preserve old repo IDs as historical pointers.
- [ ] Add old repository keys as aliases.
- [ ] Log merge audit details.
- [ ] Queue Qdrant payload update/reindex if semantic index exists.

## Definition of Done

- [ ] Old repository keys resolve to canonical repository.
- [ ] Duplicate repo facts can be merged without deleting history.
- [ ] Local caches and old remotes do not permanently split memory scope.

---

# Phase 18: Hardening and Production Readiness

## Goal

Prepare for wider internal rollout.

## Checklist

- [ ] Replace phase-1 auth with Google OAuth web sessions and dashboard-generated Personal Access Tokens for MCP.
- [ ] Keep `ActorContext` interface unchanged during auth migration.
- [ ] Add stronger secret detection/redaction.
- [ ] Add rate limits for MCP tools.
- [ ] Add pagination to all dashboard list APIs.
- [ ] Add structured logs with request IDs.
- [ ] Add metrics for:
  - [ ] MCP tool calls
  - [ ] search latency
  - [ ] proposal approval latency
  - [ ] Qdrant failures
  - [ ] Animus failures
  - [ ] rejected unsafe memory attempts
- [ ] Add background jobs for reindexing.
- [ ] Add stale-memory detection.
- [ ] Add bulk review tools only after manual review flow is reliable.

## Definition of Done

- [ ] The system can safely support multiple internal developers and repositories.
- [ ] Failures are observable.
- [ ] Auth can migrate without rewriting memory logic.

---

# Suggested First Assignment Batch

If assigning to another agent, start with this order:

## Batch 1: Foundation

- [x] Confirm config sections and DB model registration.
  - Direct model registration is configured; real DB startup smoke is still pending.
- [x] Add core enums and schemas.
- [x] Add identity models.
- [x] Add repository model.
- [x] Add memory/proposal/version/tag/audit models.
- [ ] Smoke-test app startup with PostgreSQL available.
- [ ] Decide cleanup for unused SQLAlchemy dependency.
- [ ] Replace local committed secrets/placeholders before sharing beyond local dev.

## Batch 2: Context and Repository Resolution

- [x] Implement phase-1 header auth.
- [x] Implement user auto-provisioning.
- [x] Implement default organization resolution.
- [x] Implement `ActorContext`.
- [x] Implement Git remote normalization.
- [x] Implement `RepositoryResolver`.
- [ ] Wire actor/repository context into API/MCP request lifecycle.
- [ ] Smoke-test auth + auto-provisioning against PostgreSQL.

## Batch 3: Memory Core

- [x] Implement RBAC service skeleton.
- [x] Implement memory service create/propose/approve/reject flows for create proposals.
  - Service-level compile/import/lint checks passed; DB runtime smoke test still pending.
- [x] Implement version creation for approved creates.
  - DB runtime smoke test still pending.
- [x] Implement memory update/delete/archive flows.
  - Service-level compile/import/lint checks passed; disposable mutation DB smoke test still pending.
- [x] Implement basic secret/sensitivity guardrail.
  - Service-level compile/import/lint and deterministic safety smoke checks passed.
- [ ] Implement lexical retrieval service.

## Batch 4: APIs

- [ ] Add memory REST APIs.
- [ ] Add proposal review APIs.
- [ ] Add tag APIs.
- [ ] Add basic admin/user APIs.
- [ ] Add audit APIs or audit service hooks.

## Batch 5: MCP Loop

- [ ] Add MCP router/server.
- [ ] Add MCP context builder.
- [x] Add `save_memories` tool with typed facts and required rationale.
- [ ] Add `search_memories` tool.
- [ ] Add `list_memories` tool.
- [ ] Add update/delete proposal tools.
- [ ] Validate Claude Code connection.

## Batch 6: Intelligence and Semantic Search Later

- [ ] Add Animus processing service.
- [ ] Add Qdrant service.
- [ ] Add embedding service.
- [ ] Add semantic retrieval.
- [ ] Add hybrid retrieval.

Status: intentionally deferred until DB/manual review/MCP loop works end-to-end.

---

# Phase 13: UI Support REST APIs

## Goal

Add small backend REST APIs needed by the frontend feature build so users can select scopes and repositories without copying raw UUIDs.

## Trigger

The UI feature plan in `engram-ui/docs/frontend-feature-build-plan.md` now targets both regular developers and admin/reviewer users. Memory create/filter flows need backend-powered scope discovery.

## Recommended Files

- `schemas/repository.py`
- `schemas/context.py` or a new `schemas/scope.py`
- `services/repository_query_service.py`
- `services/scope_query_service.py`
- `routers/repositories.py`
- `routers/scopes.py`
- `main.py`

## Checklist

### Repository Discovery APIs

- [ ] Add `GET /api/repositories`.
- [ ] Add `GET /api/repositories/{repository_id}`.
- [ ] Support useful list filters:
  - [ ] `query`
  - [ ] `provider`
  - [ ] `host`
  - [ ] `workspace`
  - [ ] `repo_slug`
  - [ ] `repository_key`
  - [ ] `limit`
  - [ ] `offset`
- [ ] Return repository display fields needed by UI selectors:
  - [ ] `id`
  - [ ] `provider`
  - [ ] `host`
  - [ ] `workspace`
  - [ ] `repo_slug`
  - [ ] `repository_key`
  - [ ] `canonical_remote_url`
  - [ ] `resolver_source`
  - [ ] `resolver_confidence`
  - [ ] `created_at`
  - [ ] `updated_at`

### Organization / Scope Discovery APIs

- [ ] Add `GET /api/organizations` if multiple orgs can be visible to the actor.
- [ ] Add `GET /api/organizations/{org_id}` if organization detail is needed.
- [ ] Consider a consolidated `GET /api/scopes` endpoint that returns selectable user/repo/org scope choices for the current actor.
- [ ] Ensure returned scopes are RBAC-filtered for the current actor.
- [ ] Include enough display labels so the UI does not render raw UUIDs as primary text.

### Proposal Diff Support

- [ ] Keep `fact_id` in proposal responses for UI-side fetch-and-diff.
- [ ] Consider expanding proposal detail responses with current fact snapshot if UI-side joining becomes too chatty.
- [ ] Do not duplicate diff computation in backend unless frontend diff becomes insufficient.

### Deletion Policy Support

- [ ] Decide whether dashboard removal means archive, delete, or policy-dependent behavior.
- [ ] Ensure response/status copy can be represented cleanly in UI.
- [ ] Keep backend status transitions as source of truth.

### Audit Readability Support

- [ ] Consider optional joined display fields for audit records:
  - [ ] actor email
  - [ ] repository key/name
  - [ ] memory summary
  - [ ] proposal type/status
- [ ] Keep raw IDs in responses for support/debugging even if display fields are added.

## Definition of Done

- [ ] UI can populate repository and scope selectors from backend APIs.
- [ ] UI memory create/filter flows no longer require normal users to paste UUIDs.
- [ ] Repository/scope APIs enforce actor visibility and RBAC boundaries.
- [ ] Existing memory/proposal/tag/admin/audit contracts remain backward-compatible.

---

# Things to Avoid in Early Implementation

- [x] Do not start with Qdrant before DB/review flow works.
- [x] Do not start with Animus before manual proposals work.
- [x] Do not store repo identity only in metadata.
- [x] Do not use local path as durable repository identity.
- [ ] Do not put user identity in MCP URL for non-local flows.
- [ ] Do not return pending proposals to MCP search.
- [ ] Do not let MCP directly approve repo/org facts for regular users.
- [ ] Do not create unbounded list-all tools.
- [ ] Do not make Qdrant the authorization source.
- [ ] Do not mix embedding dimensions in one unnamed-vector collection.

Additional early guardrails:

- [ ] Do not add service logic directly inside routers or MCP tools.
- [ ] Do not make package `__init__.py` files responsible for public API/re-export wiring.
- [ ] Do not add tests/docs unless explicitly requested during this step-by-step build.
- [ ] Do not run schema generation against shared/non-local DBs without explicit confirmation.

---

# MVP Acceptance Criteria

The initial MVP is complete when all of the following are true:

- [ ] Backend starts with Vortex and Tortoise models registered.
  - Model registration is configured and validated without DB; full startup with DB remains pending.
- [ ] Valid web cookie and MCP Personal Access Token credentials resolve an `ActorContext`.
- [ ] Unknown valid `@1mg.com` users can be auto-provisioned.
- [ ] Git remote URLs resolve to stable repository records.
- [ ] Repo memory saves create pending proposals by default.
- [ ] User memory saves can create approved facts when policy allows.
- [ ] Admin/reviewer can approve or reject a proposal through API.
- [ ] Approved proposal creates a versioned `MemoryFact`.
- [ ] Lexical search returns approved memories only.
- [ ] Search includes current repo, actor user, and org scopes by default.
- [ ] MCP endpoint exposes save/search/list tools.
- [ ] Claude Code can retrieve approved memory through MCP.
- [ ] Pending/rejected/deleted memories are never returned through MCP search.
- [ ] Basic audit/version records exist for creates, approvals, and searches.

---

# Final Implementation Guidance

Build this as a governed internal memory system, not as a direct Mem0 clone.

Mem0/OpenMemory is useful for MCP and retrieval patterns, but Engram needs:

- stronger scope boundaries,
- explicit repository identity,
- review-first repo/org memory,
- RBAC-driven access,
- PostgreSQL-owned truth,
- and dashboard governance from the beginning.

The safest path is:

```text
DB models
  -> ActorContext
  -> RepositoryResolver
  -> RBAC
  -> MemoryService
  -> Review APIs
  -> Lexical Search
  -> MCP Tools
  -> Animus Processing
  -> Qdrant/Semantic Search
```