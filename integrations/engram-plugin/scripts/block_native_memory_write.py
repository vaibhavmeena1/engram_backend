#!/usr/bin/env python3
"""Allow Claude native-memory writes while preferring Engram persistence."""

from __future__ import annotations

import json
import sys
from pathlib import PurePath
from typing import Any


def _read_input() -> dict[str, Any]:
    try:
        value = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _file_path(hook_input: dict[str, Any]) -> str:
    tool_input = hook_input.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return ""
    return str(tool_input.get("file_path") or tool_input.get("path") or "").strip()


def _is_claude_native_memory(file_path: str) -> bool:
    normalized_parts = [part.lower() for part in PurePath(file_path).parts]
    if ".claude" not in normalized_parts:
        return False
    claude_index = normalized_parts.index(".claude")
    claude_parts = normalized_parts[claude_index + 1 :]
    return "memory" in claude_parts or bool(
        claude_parts and claude_parts[-1] == "memory.md"
    )


def main() -> int:
    file_path = _file_path(_read_input())
    if not file_path or not _is_claude_native_memory(file_path):
        return 0

    context = (
        f"The native-memory write to {file_path} is allowed. If the durable information "
        "being written has not already been saved in Engram, also save it with "
        "`save_memories`. Prefer Engram as the authoritative durable memory store while "
        "still completing the requested native-memory write."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
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
        # Advisory hooks must never block native-memory writes.
        raise SystemExit(0)