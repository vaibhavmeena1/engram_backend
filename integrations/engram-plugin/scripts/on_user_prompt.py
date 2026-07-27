#!/usr/bin/env python3
"""Periodically remind Claude to persist durable Engram learnings."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

REMINDER_INTERVAL = 3
MINIMUM_PROMPT_LENGTH = 20


def _read_input() -> dict[str, Any]:
    try:
        value = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _counter_path(session_id: str) -> Path:
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:20]
    return Path(os.environ.get("TMPDIR", "/tmp")) / f"engram_prompt_count_{digest}"


def _increment_counter(path: Path) -> int:
    try:
        count = int(path.read_text(encoding="utf-8").strip()) if path.exists() else 0
    except (OSError, ValueError):
        count = 0
    count += 1
    try:
        path.write_text(str(count), encoding="utf-8")
    except OSError:
        pass
    return count


def main() -> int:
    hook_input = _read_input()
    prompt = str(hook_input.get("prompt") or "").strip()
    if len(prompt) < MINIMUM_PROMPT_LENGTH:
        return 0

    session_id = str(hook_input.get("session_id") or f"process-{os.getppid()}")
    count = _increment_counter(_counter_path(session_id))
    if count % REMINDER_INTERVAL != 0:
        return 0

    context = (
        "Engram memory checkpoint: after responding, briefly inspect the recent exchange. "
        "If it established a new high-confidence fact that will remain useful for months, "
        "save at most 1-3 standalone facts with `save_memories`. Appropriate facts include "
        "stable user preferences, repository conventions, architecture decisions, and "
        "organization standards. This checkpoint is advisory: if no fact clearly meets the "
        "durability bar, do not save anything. Never save session summaries, temporary task "
        "state, current bugs, stack traces, secrets, or one-off implementation details. Save "
        "durable task outcomes incrementally so they are preserved before session end or "
        "context compaction."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(0)