#!/bin/sh
# Container entrypoint: migrate, seed demo users (if passwords are provided), optionally load
# the SYNTHETIC_DEMO scenario once, then serve the API (and the web app if SENTINEL_WEB_DIST).
set -eu

alembic upgrade head

if [ -n "${SENTINEL_SEED_ADMIN_PASSWORD:-}" ]; then
  python -m app.cli seed
else
  echo "SENTINEL_SEED_ADMIN_PASSWORD not set: skipping demo users"
fi

case "${SENTINEL_DEMO_AUTOLOAD:-false}" in
  1|true|TRUE|yes) python -m app.cli demo-load --if-empty ;;
esac

# Supervise the API, durable event/scoring worker and configured inbox bridge.
export PORT="${PORT:-8000}"
exec python -m app.workers.supervisor
