# SENTINEL - BACKEND STARTUP & READINESS GATE AUDIT

## 1. Problem Statement
During automated deployment and continuous test orchestration, backend processes were frequently subject to race conditions:
- Test runners initiated requests before database migrations completed.
- FastAPI processes accepted traffic before the database connection pool was warmed up.
- Flaky tests resulted when downstream test suites polled an unresponsive TCP port without a timeout or failed to check worker process supervisor health.
- Existing scripts either hung indefinitely or exited blindly after an arbitrary `sleep 5`, leading to cascading test failures.

---

## 2. Implementation: Bounded Fail-Closed Readiness Gate

To resolve this defect, an enterprise-grade readiness polling tool was implemented:
- **Location:** [`scripts/wait-for-readiness.py`](file:///C:/Users/ranja/Sentinel/SENTINEL-/scripts/wait-for-readiness.py) (and importable alias [`scripts/wait_for_readiness.py`](file:///C:/Users/ranja/Sentinel/SENTINEL-/scripts/wait_for_readiness.py)).

### 2.1 Multi-Stage Verification Pipeline
The script executes a strict sequence of sequential gates:

1. **Gate 1: TCP Socket Reachability**:
   - Tests raw TCP connectivity to `host:port`.
   - Rejects immediately if connection is refused after timeout.

2. **Gate 2: HTTP Liveness Check (`/api/v1/health`)**:
   - Verifies the web server is running and responding with HTTP 200.

3. **Gate 3: HTTP Readiness Check (`/api/v1/ready`)**:
   - Verifies the application has established healthy database connectivity and background service bindings.

4. **Gate 4: Database Migration Revision Check**:
   - Inspects the Alembic migration status.
   - Ensures the active database schema revision matches the expected target revision (e.g. `d105a4143283`).
   - If the database is still on an older revision or mid-migration, readiness is denied.

5. **Gate 5: Background Worker Supervision Check**:
   - Optionally validates that payment scoring workers and Supabase inbox bridge listeners are alive and active.

### 2.2 CLI Specification & Usage

```bash
python scripts/wait-for-readiness.py \
  --host localhost \
  --port 8000 \
  --timeout 30 \
  --interval 1.0 \
  --expected-revision d105a4143283 \
  --check-workers
```

#### Exit Codes:
- `0`: All gates verified successfully within timeout. System is 100% ready.
- `1`: Timeout exceeded or unrecoverable error encountered (fail-closed).
- `2`: Schema revision mismatch detected.

---

## 3. Test Coverage

The readiness gate is thoroughly tested in [`apps/api/tests/test_readiness_gate.py`](file:///C:/Users/ranja/Sentinel/SENTINEL-/apps/api/tests/test_readiness_gate.py):
1. `test_readiness_gate_passes_when_all_healthy`: PASSED.
2. `test_readiness_gate_fails_on_connection_refused`: PASSED.
3. `test_readiness_gate_fails_on_http_503_timeout`: PASSED.
4. `test_readiness_gate_fails_on_schema_revision_mismatch`: PASSED.
5. `test_readiness_gate_fails_when_worker_unhealthy`: PASSED.
6. `test_readiness_gate_recovers_after_transient_failure`: PASSED.

---

## 4. Integration into CI/CD & Test Automation

The readiness gate can be embedded into Docker entrypoints, Render build scripts, or GitHub Actions workflows:

```dockerfile
# Example Docker / Start Script integration
python scripts/wait-for-readiness.py --host 127.0.0.1 --port ${PORT:-8000} --timeout 45 || exit 1
```

This guarantees that external ingress traffic and automated test runners will never hit half-initialized containers.
