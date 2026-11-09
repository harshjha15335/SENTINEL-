# SENTINEL - OWNER & OPERATOR ACTION CHECKLIST

## 1. Overview
The following actions require external system credentials, human authorization, or administrative rights that are strictly reserved for the repository owner / project lead.

---

## 2. Action Checklist

| Priority | Action Item | Description | Context / Guidance |
|---|---|---|---|
| **P0** | **Execute Controlled Live Gemini Test** | Run the 1-request verification plan for case `c96795f1-4180-45de-b606-60f6e27a2160`. | Follow instructions in [`MINIMAL_LIVE_RETEST_PLAN.md`](file:///C:/Users/ranja/Sentinel/SENTINEL-/sentinel-antigravity-recovery/MINIMAL_LIVE_RETEST_PLAN.md). Verify that Google returns HTTP 200 without `400 INVALID_ARGUMENT`. |
| **P1** | **Supply Live PayPal Sandbox Credentials** | Replace mock credentials in environment settings with active PayPal developer credentials. | In Render / staging environment, configure `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`. See [`PAYPAL_AUTH_AUDIT.md`](file:///C:/Users/ranja/Sentinel/SENTINEL-/sentinel-antigravity-recovery/PAYPAL_AUTH_AUDIT.md). |
| **P1** | **Review and Merge Git Changes** | Review the local branch `fix/gemini-400-recovery` and push to GitHub remote. | A local backup branch `backup/baseline-410109c` and a self-contained Git bundle `sentinel-recovery-bundle.bundle` have been created. Run `git push origin fix/gemini-400-recovery` when ready. |
| **P2** | **Verify Supabase Bridge Ingress** | Confirm webhook signing secret on Supabase edge function matching the backend receiver. | Ensure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are populated in the hosted deployment. |
| **P2** | **Trigger Production Deploy on Render** | Deploy the unified Docker container on Render according to `render.yaml`. | Ensure migrations (`alembic upgrade head`) execute prior to traffic ingress, verified via `scripts/wait-for-readiness.py`. |
