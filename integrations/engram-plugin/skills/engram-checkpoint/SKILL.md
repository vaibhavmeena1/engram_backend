---
name: engram-checkpoint
description: At an advisory task-completion, session-end, or pre-compaction checkpoint, preserve only newly established durable facts from the visible conversation.
---

# Engram Checkpoint

Use this skill after a substantial task, when the conversation is likely to end, before context compaction, or when an Engram checkpoint reminder appears.

This is an advisory quality gate, not a requirement to create memory. If the visible conversation contains no new fact likely to remain useful for months, do nothing.

## Eligible Facts

Save at most three newly established facts:

- stable user preferences or working style,
- repository architecture or conventions,
- durable technical decisions and their lasting rationale,
- organization-wide engineering standards.

Do not save:

- a session summary or chronology,
- temporary task state or next steps,
- current bugs, stack traces, branches, line numbers, or one-off file changes,
- facts already saved during the conversation,
- low-confidence inferences,
- secrets, credentials, tokens, or sensitive personal information.

## Steps

1. Inspect only the visible recent conversation.
2. Identify facts that are both new and likely to remain useful for months.
3. If no fact passes, continue without calling a memory tool or announcing an empty checkpoint.
4. For each retained fact, write one concise standalone sentence and a short durability rationale.
5. Assign explicit `user`, `repo`, or `org` scope. Never use `auto` for a mixed batch.
6. Call `save_memories` once with at most three facts. Add 1-5 lowercase tags and metadata:
   - `source`: `engram-checkpoint`
   - `confidence`: `0.8` to `1.0`
7. Do not interrupt the primary response with verbose memory reporting. Mention saves compactly only when useful; always disclose pending repo/org review proposals.