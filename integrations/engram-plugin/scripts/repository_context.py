#!/usr/bin/env python3
"""Resolve local Git repository metadata for Engram Claude plugin hooks.

The backend owns canonical repository identity. This helper only collects local
signals that the backend cannot see: origin URL, git root, branch, commit, and
repo directory name. It is intentionally dependency-free and fail-open.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse


GIT_TIMEOUT_SECONDS = 1.5


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _read_hook_input() -> dict[str, Any]:
    raw_input = sys.stdin.read()
    if not raw_input.strip():
        return {}
    try:
        parsed_input = json.loads(raw_input)
    except json.JSONDecodeError:
        return {}
    return parsed_input if isinstance(parsed_input, dict) else {}


def _candidate_cwd(hook_input: dict[str, Any]) -> str:
    for key in ("cwd", "project_dir", "workspace", "workspace_dir"):
        value = _safe_str(hook_input.get(key))
        if value:
            return value

    for env_key in ("CLAUDE_PROJECT_DIR", "PWD"):
        value = _safe_str(os.environ.get(env_key))
        if value:
            return value

    return os.getcwd()


def _git(args: list[str], cwd: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    value = result.stdout.strip()
    return value or None


def _first_remote_url(cwd: str) -> str | None:
    remotes_output = _git(["remote"], cwd)
    if not remotes_output:
        return None

    for remote_name in remotes_output.splitlines():
        remote_name = remote_name.strip()
        if not remote_name:
            continue
        remote_url = _git(["remote", "get-url", remote_name], cwd)
        if remote_url:
            return remote_url
    return None


def _sanitize_remote_url(remote_url: str | None) -> str | None:
    value = _safe_str(remote_url)
    if not value:
        return None

    # SCP-style SSH remotes such as git@bitbucket.org:tata1mg/repo.git are
    # useful as-is and do not contain URL username/password components.
    if "://" not in value:
        return value.split("?", 1)[0].split("#", 1)[0]

    parsed_url = urlparse(value)
    if parsed_url.scheme in {"http", "https", "ssh", "git"}:
        hostname = parsed_url.hostname or ""
        netloc = hostname
        if parsed_url.port:
            netloc = f"{netloc}:{parsed_url.port}"
        if parsed_url.scheme == "ssh" and parsed_url.username:
            # Keep git@ for ssh remotes because it is standard and non-secret.
            netloc = f"{parsed_url.username}@{netloc}"
        sanitized_url = urlunparse(
            (parsed_url.scheme, netloc, parsed_url.path, "", "", "")
        )
        return sanitized_url or value

    return value.split("?", 1)[0].split("#", 1)[0]


def resolve_repository_metadata(
    hook_input: dict[str, Any] | None = None,
) -> dict[str, str]:
    hook_input = hook_input or {}
    cwd = _candidate_cwd(hook_input)

    git_root = _git(["rev-parse", "--show-toplevel"], cwd)
    command_cwd = git_root or cwd
    origin_url = _git(["config", "--get", "remote.origin.url"], command_cwd)
    if not origin_url:
        origin_url = _git(["remote", "get-url", "origin"], command_cwd)
    if not origin_url:
        origin_url = _first_remote_url(command_cwd)

    branch = _git(["branch", "--show-current"], command_cwd)
    if not branch:
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], command_cwd)
    commit_sha = _git(["rev-parse", "HEAD"], command_cwd)

    repo_dir_name = Path(git_root or cwd).resolve().name

    metadata = {
        "origin_url": _sanitize_remote_url(origin_url),
        "git_root": git_root,
        "repo_dir_name": repo_dir_name,
        "branch": branch,
        "commit_sha": commit_sha,
    }
    return {key: value for key, value in metadata.items() if value}


def _status_line(metadata: dict[str, str]) -> str:
    repo_label = (
        metadata.get("origin_url") or metadata.get("repo_dir_name") or "unresolved"
    )
    branch = metadata.get("branch") or "unknown"
    commit = metadata.get("commit_sha", "")[:12] or "unknown"
    return f"Engram Active | repo={repo_label} | branch={branch} | commit={commit}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--banner",
        action="store_true",
        help="Print a compact status banner instead of JSON",
    )
    args = parser.parse_args()

    hook_input = _read_hook_input()
    metadata = resolve_repository_metadata(hook_input)

    if args.banner:
        print(_status_line(metadata))
        if metadata:
            print("Repository metadata will be injected into Engram MCP tool calls.")
        else:
            print(
                "Repository metadata was not resolved; Engram will use user/org scope until Git context is available."
            )
        return 0

    print(json.dumps(metadata, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
