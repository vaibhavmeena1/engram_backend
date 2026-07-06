#!/bin/sh
set -e

# Load config from Python module
CONFIG_OUTPUT=$(python - <<'EOF'
from deployment.uvicorn_conf import HOST, PORT, WORKERS
print(HOST, PORT, WORKERS)
EOF
)
# Use positional params instead of herestring (bash-only) for portability
# shellcheck disable=SC2086
set -- $CONFIG_OUTPUT
HOST=$1; PORT=$2; WORKERS=$3

# Initialize Animus models once at service startup
# python scripts/init_animus_models.py

uvicorn app.main:app \
 --loop uvloop \
 --http httptools \
 --host "$HOST" \
 --port "$PORT" \
 --workers "$WORKERS" \
 --access-log