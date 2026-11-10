# Owner Actions & Operational Next Steps

**Audit Target:** SENTINEL Genuine PayPal Sandbox Webhook Integration  
**Current Milestone Status:** BLOCKED (Pending Genuine Sandbox Event Generation)  

---

## 1. Summary of Current State

1. **All Infrastructure & Application Code Is Verified:**
   - PayPal Sandbox OAuth works cleanly (`HTTP 200`).
   - Webhook registration is verified in PayPal Sandbox (`4J572318CT6195232` with wildcard `*`).
   - Supabase Edge Function receiver is deployed, live, and healthy (`HTTP 200 {"status":"ok","mode":"sandbox"}`).
   - FastAPI webhook route, RSA signature verifier, XGBoost scoring engine, and case management are verified with 73 passing security tests.
   - Live Gemini multi-turn AI investigation is verified.

2. **The Only Missing Link:**
   - PayPal's Sandbox event log contains **0 events**.
   - No genuine webhook has ever been fired by PayPal under this app.

---

## 2. Actions Required from Project Owner

To reach final, certified **PASS** on genuine webhook delivery:

### Action 1: Provide Supabase Service Role Key (If Live Remote Forwarding is Desired)
- To allow the local bridge worker (`app.workers.supabase_inbox`) to poll the remote Supabase inbox at `https://cfslzvvdjxstpupkqbpw.supabase.co`, configure `SENTINEL_SUPABASE_SERVICE_ROLE_KEY` in the Windows User environment:
  ```powershell
  [Environment]::SetEnvironmentVariable("SENTINEL_SUPABASE_URL", "https://cfslzvvdjxstpupkqbpw.supabase.co", "User")
  [Environment]::SetEnvironmentVariable("SENTINEL_SUPABASE_SERVICE_ROLE_KEY", "<YOUR_SERVICE_ROLE_KEY>", "User")
  ```
  *(Never paste keys into the chat).*

### Action 2: Review and Authorize the Controlled Sandbox Test
- Review [`CONTROLLED_SANDBOX_TEST_PROPOSAL.md`](CONTROLLED_SANDBOX_TEST_PROPOSAL.md).
- If approved, instruct Antigravity:
  `"Authorized: execute the controlled Sandbox payment capture test."`
- Antigravity will execute the single $25.00 Sandbox test order, capture it, and trace the genuine `PAYMENT.CAPTURE.COMPLETED` webhook through Supabase, FastAPI, and XGBoost into the database.

---

## 3. Alternative: Deploy to Staging / Render

If the owner prefers to conduct the first genuine capture test directly in a hosted staging environment on Render:
1. Review `deploy/render-continuous.yaml`.
2. Connect the Git repository to Render.
3. Configure environment variables in the Render dashboard:
   - `SENTINEL_PAYPAL_CLIENT_ID`
   - `SENTINEL_PAYPAL_CLIENT_SECRET`
   - `SENTINEL_PAYPAL_WEBHOOK_ID: 4J572318CT6195232`
   - `SENTINEL_SUPABASE_URL: https://cfslzvvdjxstpupkqbpw.supabase.co`
   - `SENTINEL_SUPABASE_SERVICE_ROLE_KEY`
   - `SENTINEL_AI_API_KEY` (Gemini API key)
4. Trigger deployment and run the first Sandbox checkout flow through the deployed frontend.
