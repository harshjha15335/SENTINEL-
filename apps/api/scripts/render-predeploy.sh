#!/bin/sh
# Render runs a single executable for pre-deploy; keep migration and schema checks separate.
set -eu
alembic upgrade d105a4143283
python -m app.cli check-schema
