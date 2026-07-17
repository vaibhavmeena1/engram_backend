#!/usr/bin/env python3
"""Block Claude native-memory writes so Engram remains authoritative."""

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

    print(
        f"BLOCKED: Do not write to {file_path}. Use the Engram `save_memories` tool "
        "for one or more durable facts. "
        "This project uses Engram as the authoritative memory store.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())