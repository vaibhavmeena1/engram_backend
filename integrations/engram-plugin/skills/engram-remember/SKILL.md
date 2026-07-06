---
name: engram-remember
description: Add one durable fact to the current user's Engram memories, or explicitly to current repo/org memory.
---

# Engram Remember

Use this skill when the user says “remember this”, “save this”, “note that”, or asks to preserve a durable fact.

Default behavior is simple: **add it to your memories**. Do not ask for or pass a user ID or org ID. Engram gets the current user and organization from authentication, and repository metadata from hooks.

For extracting multiple facts from old session history, use `engram-extract`.

## Scope Rules

- `scope="user"` by default: personal preferences, stable working style, expertise, recurring goals, or long-running projects about the current user.
- `scope="repo"` only when the user explicitly says this fact belongs to the current repository/project, or the fact is clearly a repository convention/architecture/provider/testing rule.
- `scope="org"` only when the user explicitly says this fact applies broadly across the organization.
- Do not pass user IDs or org IDs. The backend resolves them from the access token.
- Do not manually pass repository metadata unless the tool call already has it; hooks inject it automatically.

## Quality Bar

Save only durable facts likely to remain useful for months.

Do not store:

- temporary tasks,
- current bugs,
- stack traces,
- branch names,
- line numbers,
- one-off file names,
- session summaries,
- secrets, credentials, tokens, private keys, or sensitive personal information.

## Steps

1. Extract one concise standalone fact from the user's request.
2. Assign scope per the **Scope Rules** section above.
3. Choose 1-5 lowercase tags.
4. Call `save_memory` with:
   - `content`: durable fact only
   - `scope`: `user`, `repo`, or `org`
   - `summary`: short optional summary
   - `tags`: concise tags
   - `metadata`: `{ "source": "engram-remember", "confidence": 1.0 }`
5. Tell the user whether it was saved directly or submitted as a review proposal.
6. If a proposal was created, mention the proposal ID and that it is pending review.

## Examples

- “Remember that I prefer concise explanations.” → `scope="user"`.
- “Remember this repo uses the Template Pattern for providers.” → `scope="repo"`.
- “Remember this applies across all 1mg repositories.” → `scope="org"`.