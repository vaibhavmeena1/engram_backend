# Repository Scope Resolution for Internal MCP Memory

## Goal

Provide a zero-intervention mechanism for repository-specific facts in the org memory bank.

When an agent is working inside a repository, the MCP layer should automatically resolve the repository identity and use it as the memory scope for:

- Writing repo-specific facts.
- Searching repo-specific facts.
- Loading context at session start.
- Auditing which repository a fact belongs to.

This mechanism must work reliably for internal Bitbucket repositories such as:

```text
git@bitbucket.org:tata1mg/catalog-autopilot-backend.git
https://vaibhavmeena2@bitbucket.org/tata1mg/catalog-autopilot-backend.git
```

Both of these must resolve to the same canonical repository identity:

```text
bitbucket.org/tata1mg/catalog-autopilot-backend
```

---

## Core Principle

Repository identity must be independent of:

- Local folder name.
- User-specific HTTPS username in the remote URL.
- SSH vs HTTPS remote style.
- Presence or absence of `.git` suffix.
- Workspace path on the developer machine.

Repository-specific facts should not be keyed by `cwd` or display name. They should be keyed by a canonical repository record stored in the backend.

---

## Terminology

| Term | Meaning |
|---|---|
| `repository_key` | Stable canonical string derived from Git remote, e.g. `bitbucket.org/tata1mg/catalog-autopilot-backend` |
| `repo_id` | Backend UUID primary key for a repository row |
| `provider` | Git hosting provider, e.g. `bitbucket` |
| `host` | Remote host, e.g. `bitbucket.org` |
| `workspace` | Bitbucket workspace/project owner, e.g. `tata1mg` |
| `repo_slug` | Repository slug, e.g. `catalog-autopilot-backend` |
| `scope_type` | Memory scope enum value: `user`, `org`, or `repo` |
| `scope_id` | ID of the scope entity. For repo memories, this is `repo_id` |

---

## Desired Behavior

### Write Path

When an agent stores a repository-specific fact:

```text
"catalog-autopilot-backend uses Celery beat for scheduled catalog sync jobs"
```

The MCP server should store it as:

```text
scope_type = repo
scope_id   = <repo_id for bitbucket.org/tata1mg/catalog-autopilot-backend>
```

It may also store helpful metadata:

```json
{
  "repository_key": "bitbucket.org/tata1mg/catalog-autopilot-backend",
  "branch": "main",
  "source": "claude-code",
  "memory_type": "architecture_decision"
}
```

But metadata is secondary. The durable scope must be `repo_id`.

### Search Path

When the agent searches memory while working in the same repo, the MCP server should automatically add a repository filter:

```text
scope_type = repo
scope_id   = <repo_id for bitbucket.org/tata1mg/catalog-autopilot-backend>
```

The user should not need to pass repo name manually.

### Context Load Path

At session start, the MCP integration should resolve the active repo and fetch relevant facts for:

1. Current repository.
2. Current user, if user-level memory is enabled.
3. Current organization, if org-level memory is enabled.

Repository facts should be loaded only for the resolved repository.

---

## Resolution Architecture

Repository resolution should be split into two layers:

```text
Agent runtime / MCP client hook
        |
        | collects local Git facts
        v
MCP request metadata
        |
        | sends origin URL, git root, branch, optional commit
        v
Backend repository resolver
        |
        | normalizes + upserts repository row
        v
RepositoryContext(repo_id, repository_key, branch, confidence)
```

Why this split:

- The backend usually cannot inspect the developer's local filesystem.
- The local MCP hook can run Git commands safely in the active workspace.
- The backend should still own canonical normalization and repository records.

---

## Local Repository Signal Collection

The MCP client or lifecycle hook should collect these values automatically:

```text
git_root        = git rev-parse --show-toplevel
origin_url      = git config --get remote.origin.url
branch          = git branch --show-current
commit_sha      = git rev-parse HEAD
repo_dir_name   = basename(git_root)
```

Recommended payload sent to backend with each MCP request:

```json
{
  "repository": {
    "git_root": "/Users/.../catalog-autopilot-backend",
    "origin_url": "git@bitbucket.org:tata1mg/catalog-autopilot-backend.git",
    "branch": "main",
    "commit_sha": "<sha>",
    "repo_dir_name": "catalog-autopilot-backend"
  }
}
```

For privacy and portability, the backend must not use `git_root` as the canonical identity. It is useful only for debugging and optional client-side cache keys.

---

## Backend Resolution Priority

The backend should resolve repository identity in this order.

### 1. Trusted Explicit Repository ID

If a trusted internal client sends a backend `repo_id`, use it after validating that:

- The repo exists.
- The actor has access to it.
- The repo belongs to the actor's organization.

This is useful for dashboard flows or future managed clients, but normal CLI/MCP usage should not require it. Phase 1 should not depend on the Bitbucket API; repo identity comes from Codex/Claude local environment and Git metadata.

### 2. Canonical Remote URL

If `origin_url` is present, normalize it into a `repository_key`.

This should be the primary path for coding agents.

Examples:

| Input remote | Canonical repository key |
|---|---|
| `git@bitbucket.org:tata1mg/catalog-autopilot-backend.git` | `bitbucket.org/tata1mg/catalog-autopilot-backend` |
| `https://vaibhavmeena2@bitbucket.org/tata1mg/catalog-autopilot-backend.git` | `bitbucket.org/tata1mg/catalog-autopilot-backend` |
| `https://bitbucket.org/tata1mg/catalog-autopilot-backend` | `bitbucket.org/tata1mg/catalog-autopilot-backend` |
| `ssh://git@bitbucket.org/tata1mg/catalog-autopilot-backend.git` | `bitbucket.org/tata1mg/catalog-autopilot-backend` |

After normalization, the backend should upsert a repository row for the canonical key.

### 3. Client-Side Repository Mapping Cache

The client may maintain a local cache similar to Mem0's `project_map.json`, but this should be an optimization, not the source of truth.

Suggested path:

```text
~/.engram/repository_map.json
```

Suggested shape:

```json
{
  "/Users/vaibhavmeena/Desktop/1mg/catalog-autopilot-backend": {
    "repository_key": "bitbucket.org/tata1mg/catalog-autopilot-backend",
    "repo_id": "<backend-uuid>",
    "origin_hash": "<sha256-of-normalized-origin>",
    "last_seen_at": "2026-07-03T12:00:00Z"
  }
}
```

The cache helps avoid repeated resolution calls, but the backend should still validate `repo_id` when received.

### 4. Directory Basename Fallback

If no Git remote is available, use the directory basename only as a low-confidence local fallback.

Example:

```text
repo_dir_name = catalog-autopilot-backend
repository_key = local/catalog-autopilot-backend
resolution_confidence = low
```

For org-wide shared repository memory, this fallback should be treated carefully because two unrelated folders can share the same basename.

Recommended behavior:

- Allow searching user-local facts if needed.
- Avoid creating shared org-visible repo facts unless a Git remote is later resolved.
- Mark memories created under fallback scope with `resolution_confidence = low`.
- Reconcile fallback memories into the canonical repo once an origin URL becomes available.

For internal Bitbucket repositories, the expected normal path is remote URL normalization, not basename fallback.

---

## Bitbucket Remote Normalization

### Supported Inputs

The resolver must support at least these formats:

```text
git@bitbucket.org:tata1mg/catalog-autopilot-backend.git
ssh://git@bitbucket.org/tata1mg/catalog-autopilot-backend.git
https://bitbucket.org/tata1mg/catalog-autopilot-backend.git
https://vaibhavmeena2@bitbucket.org/tata1mg/catalog-autopilot-backend.git
http://bitbucket.org/tata1mg/catalog-autopilot-backend.git
```

### Normalization Rules

Apply these steps:

1. Trim whitespace.
2. Remove query string and fragment, if present.
3. Convert SCP-style SSH syntax:

   ```text
   git@bitbucket.org:tata1mg/catalog-autopilot-backend.git
   ```

   into parseable URL shape:

   ```text
   ssh://git@bitbucket.org/tata1mg/catalog-autopilot-backend.git
   ```

4. Parse host and path.
5. Lowercase host.
6. Lowercase Bitbucket workspace and repo slug.
7. Remove username from HTTPS remotes.
8. Remove `.git` suffix.
9. Collapse duplicate slashes.
10. Require at least two path segments: `<workspace>/<repo_slug>`.
11. Return:

    ```text
    <host>/<workspace>/<repo_slug>
    ```

### Example

Input:

```text
https://vaibhavmeena2@bitbucket.org/tata1mg/catalog-autopilot-backend.git
```

Parsed pieces:

```text
host      = bitbucket.org
workspace = tata1mg
repo_slug = catalog-autopilot-backend
```

Canonical output:

```text
bitbucket.org/tata1mg/catalog-autopilot-backend
```

### SSH Example

Input:

```text
git@bitbucket.org:tata1mg/catalog-autopilot-backend.git
```

Converted intermediate:

```text
ssh://git@bitbucket.org/tata1mg/catalog-autopilot-backend.git
```

Canonical output:

```text
bitbucket.org/tata1mg/catalog-autopilot-backend
```

---

## Repository Table

Recommended Tortoise ORM model fields:

```text
Repository
- id UUID primary key
- org_id UUID not null
- provider string not null             # phase-1 default: bitbucket
- host string not null                 # bitbucket.org
- workspace string nullable            # tata1mg
- repo_slug string not null            # catalog-autopilot-backend
- repository_key string not null       # bitbucket.org/tata1mg/catalog-autopilot-backend
- bitbucket_origin_url string null     # git@bitbucket.org:tata1mg/catalog-autopilot-backend.git
- canonical_remote_url string null     # https://bitbucket.org/tata1mg/catalog-autopilot-backend.git
- default_branch string null
- resolver_source string null          # codex_env, claude_hook, dashboard, import
- resolver_confidence string null      # high, medium, low
- metadata jsonb default {}            # raw local git metadata, aliases, future provider data
- is_active boolean default true
- created_at datetime
- updated_at datetime
```

Constraints:

```text
unique(org_id, repository_key)
index(org_id, host, workspace, repo_slug)
index(repository_key)
```

The `repository_key` should be unique within the organization. This avoids collisions if different orgs use mirrored repos with the same host/workspace/slug.

---

## Memory Scope Storage

Repository facts should be stored through the existing memory scope model.

Recommended fields on memory/fact rows:

```text
Memory
- id UUID primary key
- org_id UUID not null
- actor_user_id UUID nullable
- scope_type enum not null          # user, org, repo
- scope_id UUID not null            # repo_id when scope_type = repo
- content text not null
- metadata jsonb default {}
- source string                     # claude-code, dashboard, service
- confidence float nullable
- created_at datetime
- updated_at datetime
```

For repository facts:

```text
scope_type = repo
scope_id = repositories.id
```

Do not rely on metadata-only repository tags for access control or retrieval isolation.

---

## Repository Context Object

Every MCP request should produce a context object before reaching memory services.

```text
RepositoryContext
- repo_id UUID | None
- repository_key string | None
- provider string | None
- host string | None
- workspace string | None
- repo_slug string | None
- branch string | None
- commit_sha string | None
- resolution_source enum
  - explicit_repo_id
  - origin_url
  - local_cache
  - basename_fallback
  - none
- resolution_confidence enum
  - high
  - medium
  - low
```

Memory services should consume this object rather than re-resolving repository identity.

---

## MCP Integration Contract

### Add Memory Tool

The MCP tool can expose a simple interface to the agent:

```text
add_memory(text, scope="auto", metadata={...})
```

The agent should not need to pass repo identifiers manually.

Internally:

1. MCP middleware resolves actor context.
2. MCP middleware resolves repository context from request metadata.
3. If `scope = auto` and repository context exists:
   - Use `scope_type = repo`.
   - Use `scope_id = repo_id`.
4. If repository context does not exist:
   - Use `scope_type = user` or reject, depending on tool policy.

Recommended default for coding agents:

```text
scope = repo when high-confidence repo context exists
scope = user when no repo context exists
```

### Search Memory Tool

The MCP search tool can expose:

```text
search_memory(query, scope="auto")
```

For `scope = auto`, search should include:

1. Repository facts for the resolved repo.
2. User facts for the actor.
3. Org facts that are globally applicable.

Recommended filter structure:

```text
OR(
  scope_type = repo AND scope_id = current_repo_id,
  scope_type = user AND scope_id = current_user_id,
  scope_type = org  AND scope_id = current_org_id
)
```

The response should include `scope_type` and repository display information so the agent knows where each fact came from.

---

## Client Hook Behavior

The Claude Code or internal MCP hook should inject repository metadata into every tool call or session initialization request.

Pseudo-flow:

```text
on_session_start or before_tool_call:
  git_root = git rev-parse --show-toplevel
  origin_url = git config --get remote.origin.url
  branch = git branch --show-current
  commit_sha = git rev-parse HEAD

  send repository metadata with MCP request
```

If Git commands fail:

```text
origin_url = null
repo_dir_name = basename(cwd)
resolution_source = basename_fallback
```

The hook must never block the agent session. If resolution fails, it should continue without repo context and let the backend decide fallback behavior.

---

## Why Not Use Category for Repository?

Categories are semantic labels such as:

- `architecture_decisions`
- `bug_fixes`
- `testing_patterns`
- `api_contracts`

Repository identity is not a semantic category. It is an access-control and retrieval scope.

Correct model:

```text
repo_id / scope_id     = which repository this fact belongs to
category / type        = what kind of fact it is
metadata.branch        = which branch observed it, if relevant
```

Example:

```json
{
  "scope_type": "repo",
  "scope_id": "<repo-id>",
  "content": "catalog-autopilot-backend uses pytest with uv run pytest.",
  "metadata": {
    "category": "testing_patterns",
    "branch": "main"
  }
}
```

---

## Branch Handling

Branch should be metadata, not primary scope.

Most repository facts should apply across branches. Branch-specific facts can be represented with metadata:

```json
{
  "branch": "feature/catalog-sync-refactor",
  "branch_specific": true
}
```

Search behavior:

- Always include repo-wide facts.
- Optionally boost facts from the current branch.
- Do not exclude repo facts just because branch differs.

Branch should not create a separate repository identity.

---

## Forks, Mirrors, and Renames

### Forks

For internal org usage, the canonical key should include workspace:

```text
bitbucket.org/tata1mg/catalog-autopilot-backend
bitbucket.org/some-user/catalog-autopilot-backend
```

These are different repositories.

If a personal fork should share memory with the upstream repo, that must be handled explicitly through a repository alias table, not URL normalization.

### Mirrors

If the same repository is mirrored across remotes, support aliases:

```text
RepositoryAlias
- id UUID
- repository_id UUID
- alias_key string unique
- source string
```

Example aliases:

```text
bitbucket.org/tata1mg/catalog-autopilot-backend
bitbucket.org/tata1mg/catalog-autopilot-service
```

For phase 1, aliases are mainly for Bitbucket repo renames or duplicate remotes. Cross-provider aliasing can be added later if needed.

### Renames

If a Bitbucket repo slug changes, the old key should become an alias pointing to the same `repo_id`.

Do not rewrite historical memories. Keep the `repo_id` stable.

---

## Admin Repository Merge

Admins must be able to merge repositories and their facts when the resolver created duplicate repository records or when the organization intentionally wants two repository identities to share one memory scope.

Common cases:

- A repo was first seen through a low-confidence basename fallback, then later resolved through Bitbucket origin.
- The same repo appears through multiple remotes or mirrors.
- A repository was renamed and both old and new records were created before aliasing existed.
- A team decides that a fork or split repo should inherit facts from an upstream repository.
- Historical imports created duplicate `Repository` rows for the same codebase.

### Merge Model

Repository merge should choose one canonical repository and one or more source repositories:

```text
canonical_repo_id = repo that survives
source_repo_ids   = repos being merged into canonical
```

The merge operation should:

1. Move repo-scoped memories from each source repo to the canonical repo.
2. Move repository aliases from each source repo to the canonical repo.
3. Add each source repository's `repository_key` as an alias of the canonical repo.
4. Mark source repositories as merged/inactive instead of hard-deleting them.
5. Preserve audit history showing who merged what and why.

### Recommended Repository Fields for Merge Support

Add these fields to `Repository`:

```text
- merged_into_repo_id UUID nullable
- merge_status enum default active      # active, merged, archived
- merged_at datetime nullable
- merged_by_user_id UUID nullable
- merge_reason text nullable
```

A merged repository row remains as a historical pointer. New resolver hits for the old key should follow `merged_into_repo_id` to the canonical repo.

### Memory Migration

For each source repository:

```text
UPDATE memories
SET scope_id = canonical_repo_id
WHERE scope_type = 'repo'
  AND scope_id = source_repo_id
```

Also update any derived indexes or vector payload metadata that duplicates `repo_id` or `repository_key`.

If Qdrant payloads include repository fields, enqueue a background reindex/update job rather than doing it synchronously inside the admin request.

### Alias Migration

Before marking the source repo as merged:

```text
RepositoryAlias(alias_key = source.repository_key, repository_id = canonical_repo_id)
```

Then move existing aliases:

```text
UPDATE repository_aliases
SET repository_id = canonical_repo_id
WHERE repository_id = source_repo_id
```

If an alias conflict exists, keep the alias that already points to the canonical repo and record the skipped duplicate in the merge audit log.

### Conflict Handling

Merging facts can create duplicate or contradictory memories. The merge operation should not silently delete facts.

Recommended behavior:

- Move all facts first.
- Mark obvious duplicates for later review.
- Keep contradictory facts but flag them for memory-review workflow.
- Preserve original source repo information in memory metadata or audit records.

Optional metadata to add during migration:

```json
{
  "merged_from_repo_id": "<source-repo-id>",
  "merged_from_repository_key": "bitbucket.org/tata1mg/old-repo-key",
  "repository_merge_id": "<merge-operation-id>"
}
```

### Merge Audit Table

Recommended table:

```text
RepositoryMergeAudit
- id UUID primary key
- org_id UUID not null
- canonical_repo_id UUID not null
- source_repo_ids UUID[] not null
- moved_memory_count integer not null
- moved_alias_count integer not null
- skipped_alias_conflicts jsonb default []
- initiated_by_user_id UUID not null
- reason text nullable
- created_at datetime
```

### Admin API

Recommended dashboard/admin endpoint:

```text
POST /admin/repositories/{canonical_repo_id}/merge
```

Payload:

```json
{
  "source_repo_ids": ["<repo-id-1>", "<repo-id-2>"],
  "reason": "Same Bitbucket repository was discovered once by basename and once by origin URL."
}
```

Response:

```json
{
  "canonical_repo_id": "<canonical-repo-id>",
  "merged_repo_ids": ["<repo-id-1>", "<repo-id-2>"],
  "moved_memory_count": 128,
  "moved_alias_count": 3,
  "reindex_job_id": "<job-id-or-null>"
}
```

### Resolver Behavior After Merge

After merge, repository resolution must follow aliases and merged pointers:

1. Normalize remote into `repository_key`.
2. Check active repository by `(org_id, repository_key)`.
3. Check `RepositoryAlias.alias_key`.
4. If matched repo has `merge_status = merged`, follow `merged_into_repo_id`.
5. Return the canonical active repo context.

This guarantees old remotes, old local caches, and old repo IDs eventually resolve to the merged canonical repo.

---

## Security and Trust

Repository context affects what facts an agent can read. Treat it as security-sensitive.

Backend checks should include:

1. Actor belongs to the organization.
2. Repository belongs to the same organization.
3. Actor has permission to access the repository memory scope.
4. Client-supplied `repo_id` matches the normalized `origin_url`, when both are present.
5. Unknown or low-confidence repositories do not expose shared org-visible repo facts by default.

For internal MCP, initial access can be org-wide, but the model should leave room for repo-level ACLs.

---

## Failure Modes

| Failure | Behavior |
|---|---|
| Not inside a Git repo | No repo context, or basename fallback with low confidence |
| Git remote missing | Basename fallback, do not create high-trust shared repo facts |
| Remote URL malformed | No repo context; log resolver error |
| Remote host unsupported | Normalize as generic Git remote if possible; provider = `unknown` |
| Repo not in DB | Upsert repository row from canonical key |
| Actor lacks repo access | Do not return repo facts; optionally return authorization error |
| Client sends mismatched `repo_id` and `origin_url` | Prefer normalized `origin_url`, log mismatch, reject if suspicious |

---

## Recommended Resolver API

Internal service interface:

```text
RepositoryResolver.resolve(
  org_id,
  actor_user_id,
  origin_url=None,
  repo_id=None,
  git_root=None,
  repo_dir_name=None,
  branch=None,
  commit_sha=None,
) -> RepositoryContext
```

Responsibilities:

1. Validate explicit `repo_id`, if provided.
2. Normalize `origin_url`, if provided.
3. Upsert repository row for canonical key.
4. Attach branch and commit metadata.
5. Return resolution confidence.
6. Emit audit/debug event.

---

## Normalization Pseudocode

```python
def normalize_git_remote(origin_url: str) -> NormalizedRepository:
    raw = origin_url.strip()
    raw = remove_query_and_fragment(raw)

    if looks_like_scp_ssh(raw):
        raw = convert_scp_ssh_to_url(raw)

    parsed = urlparse(raw)
    host = parsed.hostname.lower()
    path = parsed.path.strip("/")

    if path.endswith(".git"):
        path = path[:-4]

    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        raise InvalidRemoteUrl(origin_url)

    workspace = parts[-2].lower()
    repo_slug = parts[-1].lower()

    repository_key = f"{host}/{workspace}/{repo_slug}"

    return NormalizedRepository(
        provider=detect_provider(host),
        host=host,
        workspace=workspace,
        repo_slug=repo_slug,
        repository_key=repository_key,
    )
```

SCP-style SSH detection:

```text
^[^@]+@[^:]+:.+$
```

SCP-style conversion:

```text
git@bitbucket.org:tata1mg/catalog-autopilot-backend.git
```

becomes:

```text
ssh://git@bitbucket.org/tata1mg/catalog-autopilot-backend.git
```

---

## Example End-to-End Flow

### Input Repository

Developer is working in:

```text
/Users/vaibhavmeena/Desktop/1mg/catalog-autopilot-backend
```

Git origin:

```text
https://vaibhavmeena2@bitbucket.org/tata1mg/catalog-autopilot-backend.git
```

### Hook Collects

```json
{
  "origin_url": "https://vaibhavmeena2@bitbucket.org/tata1mg/catalog-autopilot-backend.git",
  "git_root": "/Users/vaibhavmeena/Desktop/1mg/catalog-autopilot-backend",
  "branch": "main",
  "repo_dir_name": "catalog-autopilot-backend"
}
```

### Backend Normalizes

```text
repository_key = bitbucket.org/tata1mg/catalog-autopilot-backend
provider       = bitbucket
host           = bitbucket.org
workspace      = tata1mg
repo_slug      = catalog-autopilot-backend
```

### Backend Upserts Repository

```text
repositories.id = 6f4c... 
repositories.repository_key = bitbucket.org/tata1mg/catalog-autopilot-backend
```

### Memory Write

```text
scope_type = repo
scope_id = 6f4c...
content = "catalog-autopilot-backend uses Celery beat for scheduled catalog sync jobs."
```

### Memory Search

```text
query = "scheduled catalog sync"
filters include:
  scope_type = repo
  scope_id = 6f4c...
```

---

## Implementation Plan

### Phase 1: Backend Repository Resolver

- Add `Repository` model.
- Add unique constraint on `(org_id, repository_key)`.
- Implement `normalize_git_remote`.
- Implement `RepositoryResolver.resolve`.
- Add repository context to MCP request handling.

### Phase 2: MCP Tool Integration

- Add repository metadata field to MCP request context.
- Resolve repository before memory tool execution.
- Default `add_memory(scope="auto")` to repo scope when confidence is high.
- Default `search_memory(scope="auto")` to include repo, user, and org scopes.

### Phase 3: Client Hook

- Add local Git signal collection.
- Send `origin_url`, `git_root`, `branch`, `commit_sha`, and `repo_dir_name` with MCP calls.
- Add non-blocking failure behavior.
- Optionally cache backend `repo_id` in `~/.engram/repository_map.json`.

### Phase 4: Governance and Dashboard Support

- Show repository key and display name on memory records.
- Allow admins to merge aliases if a repo is renamed.
- Support admin-driven repository merges that move facts from duplicate/source repos into a canonical repo.
- Preserve repository merge audit logs with moved fact counts, alias changes, and merge reasons.
- Show resolver confidence and source in audit logs.
- Add repo-level memory filters to dashboard APIs.

---

## Acceptance Criteria

1. Both Bitbucket remotes below resolve to the same repository key:

   ```text
   git@bitbucket.org:tata1mg/catalog-autopilot-backend.git
   https://vaibhavmeena2@bitbucket.org/tata1mg/catalog-autopilot-backend.git
   ```

   Expected:

   ```text
   bitbucket.org/tata1mg/catalog-autopilot-backend
   ```

2. Repository facts are stored with:

   ```text
   scope_type = repo
   scope_id = repositories.id
   ```

3. Search inside a repo automatically filters by the resolved `repo_id`.

4. User does not need to manually pass repository name or ID during normal MCP usage.

5. HTTPS usernames are stripped and never become part of repository identity.

6. Local filesystem paths are never used as durable repository identity.

7. Basename fallback is low-confidence and does not accidentally merge unrelated repositories.

8. Repository identity remains stable across branch changes.

9. Admins can merge duplicate repositories into a canonical repository.

10. Repository merge moves repo-scoped facts to the canonical `repo_id` without deleting historical source repository records.

11. Old repository keys and aliases continue resolving to the canonical repository after merge.

---

## Final Recommendation

Use Git remote normalization as the primary zero-intervention mechanism.

For internal Bitbucket repositories, the canonical repository key should be:

```text
bitbucket.org/<workspace>/<repo_slug>
```

Use this key to upsert a backend `Repository` row, then store and retrieve repository-specific facts through:

```text
scope_type = repo
scope_id = repo_id
```

Do not use categories for repository identity. Categories should describe the fact type; repository scope should determine where the fact belongs.