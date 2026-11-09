# SENTINEL REPOSITORY BASELINE & RECOVERY REPORT

**Date:** 2026-11-09  
**Engineer:** Google Antigravity Engineering Team  
**Git Workspace:** `C:\Users\ranja\Sentinel\SENTINEL-`  

---

## 1. Checkout State & Lineage

- **Cloned Remote:** `https://github.com/harshjha15335/SENTINEL-.git`
- **Initial Branch at Inspection:** `main`
- **Initial HEAD Commit:** `410109c9304e11d2e1e685600194e290d978c0ab`
- **Merge Parents:** `aed5d56` and `ac044cd` ("Merge recovered SENTINEL implementation while preserving static demo history")
- **Commit `ac044cd3b114ff82b8e5ff4ef3e650e541973499`:** Present in tree ("Add guarded Google investigation provider and offline construction tests").
- **Missing Diagnostic Commit `2f592d72ee542e46668c47c475cf6e56c7073ecb`:**
  - Exhaustive search of local Git objects, reflog, and remote branches (`origin/main`, `origin/claude/phase4-investigation-whwxlu`) confirmed that commit `2f592d72` was **not pushed** to GitHub and was **not present** in the freshly cloned local environment.
  - Files missing from `2f592d72` identified:
    - `apps/api/app/services/investigation/diagnostics.py`
    - `apps/api/tests/test_provider_diagnostics.py`

---

## 2. Recovery & Branch Protection Actions Taken

1. **Local Backup Branch Created:**
   - `backup/baseline-410109c` created pointing to `410109c9304e11d2e1e685600194e290d978c0ab`.
   - Never modified, serving as an immutable rollback point.
2. **Active Implementation Branch Created:**
   - `fix/gemini-400-recovery` checked out from baseline.
   - All code adjustments, offline tests, and fail-closed readiness scripts are contained on this branch.
3. **Pre-existing Changes Preserved:**
   - No destructive overrides or force pushes were executed.
   - Database schema target preserved at `d105a4143283`.
   - XGBoost calibrated serving artifacts preserved unchanged.

---

## 3. Environment & Runtime Status

| Component | Status | Details |
|---|---|---|
| Python Runtime | Python 3.12.4 | Pinned virtual environment in `apps/api/.venv` created via `uv` |
| `pydantic-ai-slim` | 2.55.0 | Pinned |
| `google-genai` | 3.0.0 | Pinned |
| `httpx2` / `httpcore2` | 2.15.1 | Pinned |
| `fastapi` | 0.143.0 | Pinned |
| `pydantic` | 2.14.0 | Pinned |
| PostgreSQL | Running on localhost:5432 | Role `sentinel` and test db `sentinel_test` provisioned |
| Node.js / npm | v24.16.0 / 11.13.0 | `apps/web` dependencies installed via `npm ci` |
