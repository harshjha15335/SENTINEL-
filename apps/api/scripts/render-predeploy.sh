#!/bin/sh
# Render runs a single executable for pre-deploy; keep migration and schema checks separate.
set -eu
alembic upgrade d105a4143283
python -m app.cli check-schema

# Pre-provision an isolated, synthetic-only viewer; never grant guest access
# to the merchant Sandbox tenant or create users inside a public API handler.
if [ "${SENTINEL_PUBLIC_DEMO_LOGIN_ENABLED:-false}" = "true" ]; then
    python -m app.cli public-demo-init
fi
