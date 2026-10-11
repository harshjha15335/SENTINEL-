#!/usr/bin/env bash
# Start the API (which also serves the built web app) on port 8000 in the background.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/api"
if ! curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
  setsid nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    > /tmp/sentinel-api.log 2>&1 < /dev/null &
fi
echo "SENTINEL: open port 8000. Users: admin@ / analyst@ / viewer@northwind.example"
echo "Passwords: .devcontainer/demo-credentials.txt   Logs: /tmp/sentinel-api.log"
