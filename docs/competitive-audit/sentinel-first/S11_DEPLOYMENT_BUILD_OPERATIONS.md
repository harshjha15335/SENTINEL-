# S11 — DEPLOYMENT, BUILD, AND CLOUD OPERATIONS AUDIT

**System:** SENTINEL Production Containerization & Cloud Operations  
**Target Platform:** Render Docker Web Service + Managed PostgreSQL  
**Audit Scope:** Dockerfile, Blueprint Manifests, Process Supervision & Cloud Readiness  

---

## 1. CONTAINER SPECIFICATION & RUNTIME ARCHITECTURE

- **Multi-Stage Dockerfile:** [`Dockerfile`](file:///C:/Users/ranja/Sentinel/SENTINEL-/Dockerfile)
  * **Stage 1 (Web Builder):** `node:24-slim` executes `npm ci` and `npm run build`, producing production bundles in `/src/apps/web/dist`.
  * **Stage 2 (Runtime Host):** `python:3.12-slim` mounts the built SPA at `/app/web` (`SENTINEL_WEB_DIST=/app/web`), installs Python dependencies via `pip install .`, and runs as non-privileged user `sentinel` (UID 10001).
  * **Single-Origin Topology:** FastAPI hosts both `/api/v1/*` backend endpoints and static UI assets on port `8000`, completely avoiding cross-origin CORS complexity.

---

## 2. STARTUP SEQUENCE & PROCESS SUPERVISION

The container entrypoint [`apps/api/scripts/start.sh`](file:///C:/Users/ranja/Sentinel/SENTINEL-/apps/api/scripts/start.sh) executes a strict startup contract:

1. **Alembic Auto-Migration:**
   Executes `alembic upgrade "${SENTINEL_MIGRATION_TARGET:-d105a4143283}"`.
2. **Schema Verification Gate:**
   Executes `python -m app.cli check-schema` to verify table definitions before launching processes.
3. **Demo User Seeding:**
   Runs `python -m app.cli seed` if `SENTINEL_SEED_ADMIN_PASSWORD` is provided.
4. **Supervised Process Launch:**
   Executes `python -m app.workers.supervisor` which spawns and monitors:
   - `uvicorn app.main:app` (FastAPI Web Server)
   - `python -m app.workers.pipeline` (Durable Scoring Pipeline Worker, advisory lock `7682346`)
   - `python -m app.workers.supabase_inbox` (Supabase Webhook Bridge, when configured)

---

## 3. CLOUD DEPLOYMENT & AUTODEPLOY RISK AUDIT

- **Render Blueprint Manifest:** [`render.yaml`](file:///C:/Users/ranja/Sentinel/SENTINEL-/render.yaml)
  ```yaml
  services:
    - type: web
      name: sentinel
      runtime: docker
      plan: free
      autoDeploy: true
  ```
- **AutoDeploy Risk Identified:**
  Because `render.yaml` sets `autoDeploy: true`, pushing commits to GitHub `main` triggers automated container builds on Render.
- **Rollout & Advisory Lock Constraint:**
  The background pipeline worker holds PostgreSQL advisory lock `7682346`. If Render attempts overlapping (zero-downtime) rollouts with two concurrent instances, the replacement worker will repeatedly exit until the old container terminates. A single desired replica (`numInstances: 1`) is mandatory.

---

## 4. HEALTH & READINESS PROBES

- **Liveness Probe (`/api/v1/health`):**
  Lightweight HTTP check returning `{ "status": "ok" }`.
- **Readiness Probe (`/api/v1/ready`):**
  Deep operational check:
  1. Tests database connection and transaction rollback.
  2. Verifies Alembic schema version matches target `d105a4143283`.
  3. Inspects `worker_health` table to confirm pipeline worker has reported a heartbeat within the last 60 seconds.
  4. Returns `HTTP 503 Service Unavailable` if workers are dead or schema is out of sync.

