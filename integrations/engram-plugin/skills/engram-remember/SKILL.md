---
name: engram-remember
description: Proactively or explicitly save one newly established durable user, repository, or organization fact to Engram.
---

# Engram Remember

Use this skill in either situation:

- **Explicit:** the user says “remember this”, “save this”, “note that”, or otherwise asks to preserve a durable fact.
- **Proactive:** the recent conversation clearly establishes one new high-confidence fact that will remain useful for months, such as a stable user preference, repository convention, architecture decision, or organization standard.

Do not wait for explicit wording when one fact clearly meets the quality bar. Proactive saving is advisory, not mandatory: if the evidence or durability is uncertain, do not save anything and do not announce an empty memory check.

Default behavior is simple: **add one durable fact to the appropriate memory scope**. Do not ask for or pass a user ID or org ID. Engram gets the current user and organization from authentication, and repository metadata from hooks.

For extracting multiple facts, reviewing a longer running conversation, or processing old session history, use `engram-extract` or `engram-checkpoint`.

## Scope Rules

- `scope="user"` by default: personal preferences, stable working style, expertise, recurring goals, or long-running projects about the current user.
- `scope="repo"` only when the user explicitly says this fact belongs to the current repository/project, or the fact is clearly a repository convention/architecture/provider/testing rule.
- `scope="org"` only when the user explicitly says this fact applies broadly across the organization.
- Do not pass user IDs or org IDs. The backend resolves them from the access token.
- If session context reports that the repository is available, omit `repository`; hooks inject authoritative Git metadata.
- If session context reports that repository resolution is unavailable and you must save a repo fact, pass only `repository: { "origin_url": "<current Git remote>" }` when known.

## Quality Bar

Save only durable facts likely to remain useful for months.

For proactive saves, require direct evidence from the visible conversation. Do not turn guesses, ordinary task completion, or a single temporary implementation choice into memory. Save no more than one proactive fact from a meaningful exchange; use `engram-extract` when several facts need evaluation.

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

1. Identify the trigger as explicit or proactive, then extract one concise standalone fact from the visible conversation.
2. Verify that the fact is newly established, directly supported, and likely to remain useful for months. If not, stop without saving.
3. Assign scope per the **Scope Rules** section above.
4. Choose 1-5 lowercase tags.
5. Call `save_memories` with one item in `facts`:
   - `content`: durable fact only
   - `rationale`: why the fact is well-supported, durable, and useful in future work
   - `scope`: `user`, `repo`, or `org`
   - `summary`: short optional summary
   - `tags`: concise tags
   - explicit metadata: `{ "source": "engram-remember", "confidence": 1.0 }`
   - proactive metadata: `{ "source": "engram-remember-proactive", "confidence": 0.85 }`
6. For an explicit request, tell the user whether it was saved directly or submitted as a review proposal. For a proactive direct save, mention it only when useful and keep the note brief.
7. Always disclose a pending repo/org proposal, including its proposal ID.

## Examples

- “Remember that I prefer concise explanations.” → explicit `scope="user"`, confidence `1.0`.
- The user repeatedly establishes a preference for architecture-first explanations without saying “remember” → proactive `scope="user"`, confidence `0.85`.
- A substantial implementation confirms that the repository consistently uses the Template Pattern for providers → proactive `scope="repo"`, normally submitted for review.
- “Remember this applies across all 1mg repositories.” → explicit `scope="org"`, normally submitted for review.