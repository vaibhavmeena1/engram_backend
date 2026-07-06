---
name: engram-search
description: Search the current user's Engram memories by default, with explicit repo/org search when requested.
---

# Engram Search

Use this skill when the user explicitly asks to search, list, or inspect saved Engram memory. This is a user-directed lookup, not automatic task preprocessing.

Default behavior is simple: **search your memories**. Do not ask for or pass a user ID or org ID. Engram gets the current user and organization from authentication, and repository metadata from hooks.

## Search Policy

- Use `search_memories(query=<query>)` for “search my/your memories”. The default scope is the current user's memories.
- Use `list_memories()` for “show/list my memories”. The default scope is the current user's memories.
- Use `scope="repo"` only when the user asks for current repository/project memory.
- Use `scope="org"` only when the user asks for organization-wide memory.
- Use `scope="auto"` only when the request should combine user, org, and high-confidence current repository memory.
- Do not pass user IDs or org IDs.
- Do not invent saved context when no result is returned.

## Steps

1. Derive a short search query from the user request.
2. For personal memory search, call `search_memories(query=<query>, limit=10)`.
3. For browsing, call `list_memories(limit=10)`.
4. For explicit shared scope, pass `scope="repo"`, `scope="org"`, or `scope="auto"`.
5. Summarize only relevant memories.

## Output

Keep results compact:

```text
Engram results:
- [user] <fact>
- [repo] <fact>
```