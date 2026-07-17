#!/usr/bin/env bash
# SessionStart hook for Engram.
# Resolves local Git identity, persists required environment values for Claude
# subprocesses, and emits authenticated repository-memory status.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT="$(cat)"
REPO_JSON="$(printf '%s' "$INPUT" | python3 "$SCRIPT_DIR/repository_context.py" 2>/dev/null || echo '{}')"

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  ENGRAM_PERSONAL_ACCESS_TOKEN="${ENGRAM_PERSONAL_ACCESS_TOKEN:-}" \
    python3 - "$REPO_JSON" "$CLAUDE_ENV_FILE" <<'PYEOF' 2>/dev/null || true
import json
import os
import sys

repo_json = sys.argv[1] if len(sys.argv) > 1 else "{}"
env_file = sys.argv[2] if len(sys.argv) > 2 else ""
try:
    metadata = json.loads(repo_json)
except json.JSONDecodeError:
    metadata = {}
if not env_file:
    raise SystemExit(0)

mapping = {
    "origin_url": "ENGRAM_REPOSITORY_ORIGIN_URL",
    "git_root": "ENGRAM_REPOSITORY_GIT_ROOT",
    "repo_dir_name": "ENGRAM_REPOSITORY_DIR_NAME",
    "branch": "ENGRAM_REPOSITORY_BRANCH",
    "commit_sha": "ENGRAM_REPOSITORY_COMMIT",
}

def write_export(handle, key, value):
    if not value:
        return
    escaped_value = str(value).replace("\\", "\\\\").replace('"', '\\"')
    handle.write(f'export {key}="{escaped_value}"\n')

with open(env_file, "a", encoding="utf-8") as handle:
    if isinstance(metadata, dict):
        for source_key, env_key in mapping.items():
            write_export(handle, env_key, metadata.get(source_key))
    # Copy the inherited shell PAT into Claude's environment for later MCP calls.
    write_export(handle, "ENGRAM_PERSONAL_ACCESS_TOKEN", os.environ.get("ENGRAM_PERSONAL_ACCESS_TOKEN"))
PYEOF
fi

python3 "$SCRIPT_DIR/session_status.py" "$REPO_JSON" 2>/dev/null || true

exit 0