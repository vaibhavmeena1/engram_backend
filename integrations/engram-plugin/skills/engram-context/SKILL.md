---
name: engram-context
description: Retrieve relevant Engram context for the current request across user, org, and current repository memory.
---

# Engram Context

Use this skill when a user request may depend on saved preferences, repository conventions, project decisions, or organization standards.

This is the broad context loader for task preprocessing. It searches across the current user's memories, organization memories, and current repository memories in one call.

## Retrieval Policy

- Call `get_memory_context(query=<query>)` for broad task context.
- It searches:
  - the current user's own approved memories,
  - current organization memories,
  - current repository memories only when repository resolution is high-confidence.
- Do not pass user IDs or org IDs. Auth resolves the user/org.
- Do not manually pass repository metadata unless already provided; hooks inject it automatically.
- Use `search_memories` only when the user explicitly requests a scoped memory search.
- If no useful memory is returned, say so briefly and proceed from the current conversation only.

## Steps

1. Convert the user's request into a short search query using concrete nouns and technologies.
2. Call `get_memory_context(query=<query>, limit=8)`.
3. If results are weak and the request is important, run one focused follow-up query with alternate wording.
4. Use only relevant returned memories in the answer.
5. Keep memory citations informal and compact.

## Examples

- “How should I add this API?” → `api architecture convention repository pattern`
- “Do I prefer detailed explanations?” → `explanation preference working style`
- “What should I know before editing this repo?” → `repository architecture conventions testing decisions`

## Output

```text
Relevant Engram context:
- [repo] <fact>
- [user] <fact>
```

If nothing useful is found:

```text
No relevant Engram memory found for this request.
```