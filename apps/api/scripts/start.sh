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

# --proxy-headers so the login rate limit sees the client address behind the host's proxy.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips "${SENTINEL_FORWARDED_ALLOW_IPS:-*}"
