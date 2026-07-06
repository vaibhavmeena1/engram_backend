#!/usr/bin/env bash
# SessionStart hook for Engram.
# Emits a compact status banner and persists local repository facts for Bash/tool
# subprocesses when Claude exposes CLAUDE_ENV_FILE.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT="$(cat)"

printf '%s' "$INPUT" | python3 "$SCRIPT_DIR/repository_context.py" --banner 2>/dev/null || true

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  REPO_JSON="$(printf '%s' "$INPUT" | python3 "$SCRIPT_DIR/repository_context.py" 2>/dev/null || echo '{}')"
  python3 - "$REPO_JSON" "$CLAUDE_ENV_FILE" <<'PYEOF' 2>/dev/null || true
import json
import sys

repo_json = sys.argv[1] if len(sys.argv) > 1 else "{}"
env_file = sys.argv[2] if len(sys.argv) > 2 else ""
try:
    metadata = json.loads(repo_json)
except json.JSONDecodeError:
    metadata = {}
if not env_file or not isinstance(metadata, dict):
    raise SystemExit(0)

mapping = {
    "origin_url": "ENGRAM_REPOSITORY_ORIGIN_URL",
    "git_root": "ENGRAM_REPOSITORY_GIT_ROOT",
    "repo_dir_name": "ENGRAM_REPOSITORY_DIR_NAME",
    "branch": "ENGRAM_REPOSITORY_BRANCH",
    "commit_sha": "ENGRAM_REPOSITORY_COMMIT",
}
with open(env_file, "a", encoding="utf-8") as handle:
    for source_key, env_key in mapping.items():
        value = str(metadata.get(source_key) or "")
        if not value:
            continue
        escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
        handle.write(f'export {env_key}="{escaped_value}"\n')
PYEOF
fi

exit 0