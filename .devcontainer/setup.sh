#!/usr/bin/env bash
# One-time setup for GitHub Codespaces / dev containers: install, build the web app, migrate,
# create demo users with random passwords, and load the SYNTHETIC_DEMO scenario.
# PayPal runs in fixture mode: every payment created here is labelled SIMULATED.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CREDS="$ROOT/.devcontainer/demo-credentials.txt"
DB_URL="${SENTINEL_DATABASE_URL:-postgresql+psycopg://sentinel:sentinel@127.0.0.1:5432/sentinel}"

python3 -m venv "$ROOT/apps/api/.venv"
"$ROOT/apps/api/.venv/bin/pip" install --quiet --upgrade pip
"$ROOT/apps/api/.venv/bin/pip" install --quiet -e "$ROOT/apps/api[dev]"
(cd "$ROOT/apps/web" && npm ci --no-audit --no-fund && npm run build)

if [ ! -f "$CREDS" ]; then
  python3 - "$CREDS" <<'PY'
import secrets, sys
roles = ("ADMIN", "ANALYST", "VIEWER")
with open(sys.argv[1], "w") as f:
    for role in roles:
        f.write(f"SENTINEL_SEED_{role}_PASSWORD={secrets.token_urlsafe(12)}\n")
PY
  chmod 600 "$CREDS"
fi

if [ ! -f "$ROOT/apps/api/.env" ]; then
  cat > "$ROOT/apps/api/.env" <<ENV
SENTINEL_DATABASE_URL=$DB_URL
SENTINEL_PAYPAL_MODE=fixture
SENTINEL_WEB_DIST=$ROOT/apps/web/dist
SENTINEL_CORS_ORIGINS=["http://localhost:8000"]
ENV
fi

cd "$ROOT/apps/api"
for _ in $(seq 1 30); do
  .venv/bin/python -c "import psycopg,sys; psycopg.connect(sys.argv[1].replace('+psycopg', '')).close()" "$DB_URL" 2>/dev/null && break
  sleep 2
done
.venv/bin/alembic upgrade head
set -a; . "$CREDS"; set +a
.venv/bin/python -m app.cli seed
.venv/bin/python -m app.cli demo-load --if-empty
echo "SENTINEL is set up. Sign-in passwords: .devcontainer/demo-credentials.txt"
