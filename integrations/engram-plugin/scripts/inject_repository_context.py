#!/usr/bin/env python3
"""PreToolUse hook that injects repository metadata into Engram MCP calls."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from repository_context import resolve_repository_metadata  # noqa: E402


ENGRAM_TOOL_PREFIXES = (
    "mcp__engram__",
    "mcp__plugin_engram_engram__",
)


def _read_hook_input() -> dict[str, Any]:
    raw_input = sys.stdin.read()
    if not raw_input.strip():
        return {}
    try:
        parsed_input = json.loads(raw_input)
    except json.JSONDecodeError:
        return {}
    return parsed_input if isinstance(parsed_input, dict) else {}


def _tool_input(hook_input: dict[str, Any]) -> dict[str, Any]:
    value = hook_input.get("tool_input") or {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(parsed_value) if isinstance(parsed_value, dict) else {}
    return {}


def _is_engram_tool(tool_name: str) -> bool:
    return any(tool_name.startswith(prefix) for prefix in ENGRAM_TOOL_PREFIXES)


def _merge_repository(
    existing_value: Any, resolved_repository: dict[str, str]
) -> tuple[dict[str, Any], bool]:
    if not resolved_repository:
        return {}, False

    if isinstance(existing_value, dict):
        merged_repository = dict(existing_value)
        changed = False
        for key, value in resolved_repository.items():
            if not merged_repository.get(key):
                merged_repository[key] = value
                changed = True
        return merged_repository, changed

    return resolved_repository, True


def _emit_updated_input(updated_input: dict[str, Any]) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "updatedInput": updated_input,
                }
            },
            separators=(",", ":"),
        )
    )


def main() -> int:
    hook_input = _read_hook_input()
    tool_name = str(hook_input.get("tool_name") or "")
    if tool_name and not _is_engram_tool(tool_name):
        return 0

    updated_input = _tool_input(hook_input)
    resolved_repository = resolve_repository_metadata(hook_input)
    repository, changed = _merge_repository(
        updated_input.get("repository"), resolved_repository
    )
    if not changed:
        return 0

    updated_input["repository"] = repository
    _emit_updated_input(updated_input)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # Hooks must never block user work. Fail open silently.
        raise SystemExit(0)
