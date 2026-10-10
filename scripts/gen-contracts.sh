#!/usr/bin/env bash
# Regenerate the shared API contract from the FastAPI OpenAPI schema.
# packages/contracts/openapi.json is the single source of truth for request/response shapes;
# the web app imports the generated TypeScript types from packages/contracts/openapi.ts.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/api"
PY="${PYTHON:-.venv/bin/python}"
SENTINEL_PAYPAL_MODE=fixture "$PY" -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2, sort_keys=True))" > "$ROOT/packages/contracts/openapi.json"
cd "$ROOT/apps/web"
npx openapi-typescript ../../packages/contracts/openapi.json -o ../../packages/contracts/openapi.ts
