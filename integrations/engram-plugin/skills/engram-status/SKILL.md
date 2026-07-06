---
name: engram-status
description: Verify Engram MCP auth and repository resolution for the current workspace.
---

# Engram Status

Use this skill when the user asks whether Engram is connected, which user/org is active, which repository is active, or why repository-scoped memory is not working.

## Identity Model

- Do not pass a user ID or org ID.
- The authenticated user and organization come from the access token.
- Repository metadata is injected by hooks from the local Git workspace.
- The repository is resolved under the authenticated organization.

## Steps

1. Call `get_current_context` with no manual `repository` argument.
2. Show a compact status:
   - actor email
   - organization slug
   - repository key, if resolved
   - resolver source and confidence
   - branch and commit, if available
3. If `repository` is null, explain that Git metadata was not available and repository memory cannot be used automatically.
4. If `resolver_confidence` is below `0.8`, treat it as low-confidence fallback. Do not encourage repo-scope writes unless an origin URL is configured.

## Expected Output

```text
Engram Active
user: <email>
org: <org_slug>
repo: <repository_key or unresolved>
source: <resolver_source or none>
confidence: <resolver_confidence or none>
branch: <branch or unknown>
```