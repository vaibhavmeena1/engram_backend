#!/usr/bin/env python3
"""Fetch and render repository-aware Engram status for SessionStart."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_API_BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT_SECONDS = 4


def _repository_metadata() -> dict[str, str]:
    raw_value = sys.argv[1] if len(sys.argv) > 1 else "{}"
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if item}


def _request_headers(metadata: dict[str, str], token: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "X-Engram-Client": "claude-code",
    }
    header_mapping = {
        "origin_url": "X-Engram-Repository-Origin-Url",
        "git_root": "X-Engram-Repository-Path",
        "branch": "X-Engram-Repository-Branch",
        "commit_sha": "X-Engram-Repository-Commit",
    }
    for source_key, header_name in header_mapping.items():
        value = metadata.get(source_key)
        if value:
            headers[header_name] = value
    return headers


def _fetch_status(metadata: dict[str, str], token: str) -> dict[str, Any] | None:
    base_url = os.environ.get("ENGRAM_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
    request = urllib.request.Request(
        f"{base_url}/api/plugin/session-status",
        headers=_request_headers(metadata, token),
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.HTTPError, urllib.error.URLError):
        return None

    if not isinstance(payload, dict):
        return None
    if isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload


def _repository_label(
    metadata: dict[str, str], status: dict[str, Any] | None
) -> str:
    repository = status.get("repository") if status else None
    if isinstance(repository, dict):
        return str(
            repository.get("repository_key")
            or repository.get("repo_slug")
            or metadata.get("repo_dir_name")
            or "unresolved"
        )
    return metadata.get("origin_url") or metadata.get("repo_dir_name") or "unresolved"


def main() -> int:
    metadata = _repository_metadata()
    token = os.environ.get("ENGRAM_PERSONAL_ACCESS_TOKEN", "").strip()
    branch = metadata.get("branch") or "unknown"
    repository_label = _repository_label(metadata, None)

    if not token:
        status_line = (
            f"Engram — Setup Required | repo={repository_label} | "
            f"branch={branch} | auth=none"
        )
        print("## Engram — Setup Required")
        print()
        print(f"`{status_line}`")
        print()
        print("IMPORTANT: In your FIRST response, display this exact status line as your opening line:")
        print()
        print(f"`{status_line}`")
        print()
        print("ENGRAM_PERSONAL_ACCESS_TOKEN is not available in Claude's environment.")
        return 0

    status = _fetch_status(metadata, token)
    repository_label = _repository_label(metadata, status)
    repository_resolved = bool(status and status.get("repository_resolved"))
    resolution = "resolved" if repository_resolved else "unresolved"

    if repository_resolved and status:
        user_memory_count = status.get("user_memory_count")
        repository_memory_count = status.get("repository_memory_count")
        organization_memory_count = status.get("organization_memory_count")
        user_memory_count = user_memory_count if isinstance(user_memory_count, int) else "?"
        repository_memory_count = (
            repository_memory_count
            if isinstance(repository_memory_count, int)
            else "?"
        )
        organization_memory_count = (
            organization_memory_count
            if isinstance(organization_memory_count, int)
            else "?"
        )
        memory_summary = (
            f"user memories={user_memory_count} | "
            f"repo memories={repository_memory_count} | "
            f"org memories={organization_memory_count}"
        )
    else:
        memory_summary = "memories=?"

    status_line = (
        f"Engram Active | repo={repository_label} | branch={branch} | "
        f"{memory_summary} | repository={resolution}"
    )
    print("## Engram Active")
    print()
    print(f"`{status_line}`")
    print()
    print("IMPORTANT: In your FIRST response, display this exact status line as your opening line:")
    print()
    print(f"`{status_line}`")
    print()
    print(
        "After completing a substantial task or making a durable decision, proactively "
        "save high-confidence learnings with the Engram `save_memories` tool. Store stable "
        "user preferences in user scope and repository conventions or architecture in repo "
        "scope. Do not store secrets, transient errors, or temporary task state."
    )
    if repository_resolved:
        print(
            "Repository context is available: omit the tool's repository parameter because "
            "the pre-tool hook injects authoritative local Git metadata."
        )
    else:
        print(
            "Repository context is unavailable: for a repo-scoped save, provide only "
            "repository.origin_url when you know the current Git remote."
        )
    if status is None:
        print("Engram status could not be fetched; memory counts are unavailable.")
    elif not repository_resolved:
        print("Repository scope was not resolved with enough confidence; repository memory count was skipped.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(0)