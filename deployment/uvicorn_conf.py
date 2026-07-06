"""Uvicorn configuration for Catalog Autopilot Backend."""

import json
from pathlib import Path

project_root = Path(__file__).parent.parent
config_path = project_root / "config.json"

with config_path.open() as f:
    cfg = json.load(f)

HOST = cfg.get("HOST", "0.0.0.0")
PORT = cfg.get("PORT", 8080)
WORKERS = cfg.get("WORKERS", 4)
