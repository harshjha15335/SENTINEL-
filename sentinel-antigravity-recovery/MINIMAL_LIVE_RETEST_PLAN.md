# SENTINEL - MINIMAL CONTROLLED LIVE RETEST PLAN

## 1. Context & Objective
To respect the standing constraint prohibiting unmetered or automated live Gemini calls that could exhaust Free-tier quota, all code modifications in this recovery were verified offline using mocked SDK transports.

This document provides the repository owner with an exact, controlled procedure to execute a **single live request** against `generativelanguage.googleapis.com` to confirm that the HTTP 400 error is permanently resolved in production.

---

## 2. Target Test Case Specification
- **Target Case ID:** `c96795f1-4180-45de-b606-60f6e27a2160`
- **Target Model:** `gemini-3.1-flash-lite`
- **Target Provider:** `google`
- **Expected Request Count:** Exactly 1 API call
- **Expected Result:** HTTP 200 OK with valid `InvestigationFindings` JSON payload, or structured tool execution.

---

## 3. Step-by-Step Live Test Execution Instructions

### Step 1: Environment Preparation
Ensure your live Google Gemini API key is exported in your local shell:

```powershell
# Windows PowerShell
$env:GEMINI_API_KEY="AIzaSyYourActualLiveGeminiKey..."
$env:AI_PROVIDER="google"
$env:AI_MODEL_NAME="gemini-3.1-flash-lite"

# Or Linux/macOS Bash
export GEMINI_API_KEY="AIzaSyYourActualLiveGeminiKey..."
export AI_PROVIDER="google"
export AI_MODEL_NAME="gemini-3.1-flash-lite"
```

### Step 2: Run the Single Case Investigation Command
Execute the single-case investigation runner script in test mode:

```powershell
cd C:\Users\ranja\Sentinel\SENTINEL-\apps\api
.\.venv\Scripts\python -m app.services.investigation.runner --case-id c96795f1-4180-45de-b606-60f6e27a2160 --max-iterations 1
```

### Step 3: Verification Criteria
Inspect the output logs for the following success markers:
1. **Network Response:** Check that `generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent` returns `HTTP 200` (not `HTTP 400`).
2. **Schema Validation:** Verify that `InvestigationFindings` parses cleanly into:
   - `summary`: Non-empty string detailing fraud signals.
   - `risk_explanation`: Valid risk narrative.
   - `evidence_references`: Array of referenced transaction/payer evidence.
   - `recommended_action`: Valid enum value (`APPROVE`, `FLAG_FOR_REVIEW`, `DECLINE`).
3. **Audit Record:** Query the database or logs to confirm:
   - Investigation record transitions to `COMPLETED` (or `FALLBACK_USED` if model limits exceeded).
   - `run.usage["diagnostic"]` does NOT contain `HTTP 400 INVALID_ARGUMENT`.

---

## 4. Emergency Rollback / Fallback Verification
If the live call encounters a temporary Google rate limit (`HTTP 429`):
- Confirm that SENTINEL immediately switches to the deterministic fallback finding without crashing or hanging.
- Confirm that `run.usage["diagnostic"]` registers `{"error": "rate_limit_exceeded"}` via `extract_safe_diagnostics`.
