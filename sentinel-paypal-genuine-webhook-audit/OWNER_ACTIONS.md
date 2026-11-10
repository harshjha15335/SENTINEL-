# Owner Actions & Execution Readiness Checklist

**Audit Target:** SENTINEL Genuine PayPal Sandbox Webhook Integration  
**Current Milestone Status:** READY FOR AUTHORIZATION (Plan v2.0 Corrected)  

---

## 1. Summary of Current Engineering Readiness

1. **All Core Code & Infrastructure Verified:**
   - PayPal Sandbox OAuth verified (`HTTP 200`, Debug ID `ca5841d563b81`).
   - Webhook registration verified (`4J572318CT6195232` registered with wildcard `*`).
   - Supabase Edge Function receiver verified:
     - GET health check returns `HTTP 200 {"status":"ok","mode":"sandbox"}`.
     - POST handler verified live: unauthenticated requests fail closed with `HTTP 400 {"error":"invalid_signature_headers"}`.
   - 73 security, webhook, and lifecycle tests passing (0 failures).
   - Gemini multi-turn AI investigation previously verified live.

2. **Corrected Checkout & Delivery Flow:**
   - Accounted for mandatory PayPal Orders v2 buyer approval (`approve_url`).
   - Pre-mapped `Transaction.paypal_order_id` in database to ensure incoming capture webhook reconciles properly.
   - Adjusted request budget to 4 external requests.
   - Clarified that success is established by authentic `RiskAssessment` persistence with `data_origin = 'LIVE_SANDBOX'`, whether or not the transaction triggers a HIGH-risk case.

---

## 2. Immediate Prerequisite for Project Owner

Before any order can be created or captured:

### Prerequisite: Configure Supabase Service Role Key
The Supabase inbox bridge worker (`apps/api/app/workers/supabase_inbox.py`) requires `SENTINEL_SUPABASE_SERVICE_ROLE_KEY` to poll the hosted Supabase inbox via `sentinel_claim_webhooks`.

In PowerShell (Run as Administrator or User session):
```powershell
[Environment]::SetEnvironmentVariable("SENTINEL_SUPABASE_URL", "https://cfslzvvdjxstpupkqbpw.supabase.co", "User")
[Environment]::SetEnvironmentVariable("SENTINEL_SUPABASE_SERVICE_ROLE_KEY", "<YOUR_SUPABASE_SERVICE_ROLE_KEY>", "User")
```
*(Do NOT paste this secret into chat).*

---

## 3. Decision & Authorization Options

Once the prerequisite above is set, choose how to proceed:

### Option A: Authorize the Corrected Controlled Sandbox Test (Recommended)
Reply:
> `"Authorized: execute the corrected Sandbox checkout and webhook verification test."`

**What happens next:**
1. Antigravity verifies Supabase bridge connectivity and FastAPI readiness (Stage 0).
2. Antigravity creates a pending transaction and initiates the $25.00 Sandbox order (Stage 1).
3. Antigravity outputs the PayPal Sandbox `approve_url`.
4. You (the operator) open the URL in your browser, log into your PayPal Sandbox Personal account, and click **"Complete Purchase"** (Stage 2).
5. Antigravity confirms approval, captures the order (Stage 3 & 4), and traces the authentic webhook through Supabase, the inbox bridge, FastAPI, and XGBoost scoring into PostgreSQL (Stages 5–8).
6. Antigravity delivers full event-to-assessment traceability evidence.

### Option B: Deploy to Staging / Render First
If you prefer conducting the live checkout through the full frontend UI hosted on Render:
1. All deployment templates are verified (`deploy/render-continuous.yaml`).
2. Supply required environment variables directly in Render's dashboard.
3. Conduct the buyer checkout flow interactively in the web browser.
