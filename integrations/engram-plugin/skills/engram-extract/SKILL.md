---
name: engram-extract
description: Extract high-confidence long-term Engram memory facts from visible or pasted conversation history, then save them with user/repo/org scope.
---

# Engram Extract

Use this skill when the user opens an old session, pastes a transcript, or asks to extract durable memory from earlier messages.

This is **not** a session summary workflow. Extract only facts that should improve future assistance for months.

Do not ask for or pass a user ID or org ID. Engram gets the current user and organization from authentication. If session context says repository context is available, omit `repository` because hooks inject authoritative local Git metadata. If it is unavailable and a repo fact must be saved, pass only `repository.origin_url` when the current Git remote is known.

## Core Scope Rules

- `scope="user"`: stable facts about the current user only, such as preferences, working style, expertise, recurring goals, or long-running projects. This is the default for personal facts.
- `scope="repo"`: stable facts that should apply only when this repository/project is active, such as architecture, conventions, providers, testing style, or recurring implementation patterns.
- `scope="org"`: stable facts that apply broadly across repositories in the organization, such as shared engineering standards or cross-project process rules.
- Avoid `scope="auto"` while extracting mixed facts. Prefer explicit `user`, `repo`, or `org`.

## Extraction Rubric

A candidate memory is worth saving only if it satisfies **all** of these:

1. Likely to remain true for months.
2. Useful across many future conversations.
3. Supported by repeated or high-confidence evidence.
4. Represents a stable user preference, working style, expertise, recurring project, long-term goal, repository convention, or organization standard.
5. Not obvious from the current single task alone.

Discard:

- Temporary tasks or session summaries.
- Current bugs, stack traces, line numbers, branch names, or one-off file names.
- One-off questions or short-lived implementation details.
- Sensitive personal information, credentials, tokens, secrets, or private keys.
- Low-confidence inferences.
- Anything that merely summarizes what happened in the session.

Prefer:

- User preferences: concise explanations, architecture-first discussions, examples over theory, iterative refinement.
- Technical expertise: only when strongly supported, such as experienced backend engineer or comfortable with async Python.
- Working style: likes full execution-flow understanding, reusable abstractions, backward compatibility.
- Long-running projects: only if repeatedly worked on.
- Repository memories: architecture patterns, integrations/providers, naming conventions, review expectations, test strategy.
- Organization memories: broad standards that apply across multiple repositories.

## Steps

1. Read the visible conversation or pasted transcript carefully.
2. Build a short candidate list. For each candidate ask:
   - Will this likely still help after 6 months?
   - Would remembering this reduce repeated explanations?
   - Would another assistant benefit from knowing this?
3. Drop weak candidates. If nothing passes, say that no durable memory facts were found.
4. For each retained fact, write one concise standalone sentence.
5. Assign an explicit scope: `user`, `repo`, or `org`.
6. Add 1-5 lowercase tags such as `preference`, `working-style`, `architecture`, `convention`, `repo`, or `org-standard`.
7. Call `save_memories` with the `facts` parameter set to a list of fact objects (see shape below), and set `default_scope` to the dominant scope for the batch (typically `"user"`). Individual facts may override scope. Every fact must include `rationale`, a concise explanation of why it passed the rubric. Include metadata per fact:
   - `source`: `engram-extract`
   - `confidence`: `0.8` to `1.0`
8. Report compact results:
   - saved count
   - review proposal count
   - failed count
   - proposal IDs for repo/org memories pending review

## Fact Object Shape

Each item in the `facts` list should look like this:

```json
[
  {
    "content": "The user prefers architecture-first discussions before implementation details.",
    "rationale": "The user stated this stable working preference clearly, and it will guide future technical discussions.",
    "scope": "user",
    "summary": "Architecture-first preference",
    "tags": ["preference", "working-style"],
    "metadata": {
      "source": "engram-extract",
      "confidence": 0.9
    }
  },
  {
    "content": "This repository uses a manager -> template -> repository architecture pattern.",
    "rationale": "This stable repository convention is useful when planning and reviewing future code changes.",
    "scope": "repo",
    "summary": "Repository architecture pattern",
    "tags": ["architecture", "convention", "repo"],
    "metadata": {
      "source": "engram-extract",
      "confidence": 0.85
    }
  }
]
```

Pass this array as the `facts` parameter. Use `default_scope="user"` (or `"repo"` / `"org"`) as the fallback for any fact that omits its own `scope` field.

## Safety Constraints

- Do not save secrets or sensitive personal information.
- Do not fabricate missing facts.
- Do not save “the user asked me to...” task summaries.
- Do not save repo facts as user preferences.
- Do not save user facts about anyone except the current actor.