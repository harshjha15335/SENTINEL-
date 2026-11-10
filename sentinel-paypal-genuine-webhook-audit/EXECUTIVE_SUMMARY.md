# SENTINEL — Genuine PayPal Sandbox Webhook Audit: Executive Summary

**Verification Date:** November 10, 2026  
**Auditor:** Google Antigravity (Autonomous Senior PayPal Integration & Security Team)  
**Workspace:** `C:\Users\ranja\Sentinel\SENTINEL-`  
**Current Branch:** `fix/gemini-400-recovery`  
**Current Commit:** `bcf085d` (Clean working tree with recovery bundle preserved)  

---

## 1. High-Level Audit Classification

### **Current Classification: BLOCKED (No Genuine Event Generated Yet)**

> [!IMPORTANT]
> **Definitive Finding:** Zero genuine PayPal webhook events have ever been generated under the active PayPal Sandbox application.
> 
> A live, read-only query to PayPal Sandbox API endpoint `GET /v1/notifications/webhooks-events` returned **`total_count: 0`** (Debug ID: `ca5841d58fa34`).
> No payment captures, orders, refunds, or disputes have ever been processed under this Sandbox REST application.
> Consequently, no genuine PayPal event has ever reached the Supabase receiver, the durable inbox, or the FastAPI backend.

| Architectural Component | Status | Empirical Evidence |
| :--- | :--- | :--- |
| **PayPal Sandbox OAuth** | **VERIFIED PASS** | HTTP 200, Debug ID `ca5841d563b81`. In-memory token acquisition. |
| **PayPal Sandbox Webhook Registration** | **VERIFIED PASS** | Webhook ID `4J572318CT6195232` registered to `https://cfslzvvdjxstpupkqbpw.supabase.co/functions/v1/paypal-webhook` with wildcard `*`. |
| **PayPal Event History (Sandbox)** | **EMPTY (0 Events)** | `GET /v1/notifications/webhooks-events` returned 0 events (Debug ID `ca5841d58fa34`). |
| **Supabase Edge Receiver** | **VERIFIED ACTIVE** | Endpoint `https://cfslzvvdjxstpupkqbpw.supabase.co/functions/v1/paypal-webhook` returns `HTTP 200 {"status":"ok","mode":"sandbox"}`. |
| **Supabase Durable Inbox RPCs** | **VERIFIED CODE/SCHEMA** | Migrations `202610200001` and `202610220002` implement atomic claim, lease token renew, and acknowledge. |
| **Inbox Bridge Forwarder** | **VERIFIED CODE/TESTS** | Byte-for-byte forwarding to FastAPI `/api/v1/webhooks/paypal` with CRC32 signature preservation and lease recovery. |
| **FastAPI Signature Verification** | **VERIFIED TESTS** | Strict RSA-SHA256 verification against PayPal certificates from approved hosts (`api.sandbox.paypal.com`). Malformed/tampered rejected. |
| **XGBoost Scoring & Case Engine** | **VERIFIED PASS** | Fully operational. Offline and synthetic test suites confirm atomic `RiskAssessment` and conditional HIGH-risk `Case` creation. |
| **Live Multi-Turn Gemini Investigation** | **HISTORICALLY VERIFIED** | Case `c96795f1-4180-45de-b606-60f6e27a2160` completed in 7.18s across 3 HTTP requests, 7 tools executed, 100% grounded. |

---

## 2. Key Audit Highlights

1. **Working Infrastructure Is Intact:**
   - The Supabase Edge Function receiver is deployed, healthy, and accessible over HTTPS.
   - The registered PayPal Sandbox webhook (`4J572318CT6195232`) is subscribed to `*` (All events wildcard), which strictly includes all 9 required SENTINEL events (`PAYMENT.CAPTURE.COMPLETED`, `CHECKOUT.ORDER.APPROVED`, `CUSTOMER.DISPUTE.*`, etc.).
   - The FastAPI backend correctly enforces cryptographic signature verification on incoming webhooks, distinguishing genuine `VERIFIED` application events from `FIXTURE` simulator events.

2. **Why Delivery Has Not Occurred:**
   - In PayPal's Sandbox architecture, webhooks are triggered **only** when an action occurs within the Sandbox merchant/buyer account tied to that specific REST app.
   - Because no buyer has checked out, and no seller has captured a payment under these Sandbox credentials, PayPal's notification engine has never had reason to dispatch an HTTP notification.
   - SENTINEL has strictly adhered to financial safeguards: **zero unauthorized payments, captures, charges, or refunds have been executed.**

3. **What Is Required for Full End-to-End PASS:**
   - To achieve genuine `PASS`, a single, controlled Sandbox payment must be initiated and captured between designated test accounts.
   - Once captured, PayPal Sandbox will dispatch `PAYMENT.CAPTURE.COMPLETED` to Supabase, which inserts into `sentinel_webhook_inbox`, bridged to FastAPI, scored by XGBoost, and persisted into the database.
   - A complete, zero-cost, strictly bounded test proposal is provided in [`CONTROLLED_SANDBOX_TEST_PROPOSAL.md`](CONTROLLED_SANDBOX_TEST_PROPOSAL.md) awaiting owner authorization.

---

## 3. End-to-End Status Matrix

| Pipeline Stage | Expected Behavior | Actual Empirical Result | Status |
| :--- | :--- | :--- | :--- |
| **1. PayPal Sandbox OAuth** | HTTP 200, access token | HTTP 200, Debug ID `ca5841d563b81` | **PASS** |
| **2. Webhook Registration** | Webhook exists, URL matches | ID `4J572318CT6195232`, URL matches, `*` wildcard | **PASS** |
| **3. Genuine Event Generation** | Event logged in PayPal | `GET /v1/notifications/webhooks-events` reports 0 events | **BLOCKED** |
| **4. Event Delivery to Receiver** | PayPal POST to Supabase | Never fired by PayPal (0 events exist) | **NOT EXECUTED** |
| **5. Supabase Receiver Intake** | HTTP 200, insert to inbox | Function online (`HTTP 200 {"status":"ok","mode":"sandbox"}`) | **READY** |
| **6. Durable Inbox Claim** | Bridge leases row | Tested & verified in `test_supabase_inbox.py` | **READY** |
| **7. FastAPI Intake & Auth** | Signature verified | Verifier rejects tampered/untrusted, passes authentic | **READY** |
| **8. Transaction Persistence** | Tx updated to CAPTURED | Verified in `test_webhooks.py` | **READY** |
| **9. Scoring Job Enqueue** | RiskScoringJob created | Atomic on-conflict-do-nothing enqueue verified | **READY** |
| **10. XGBoost Inference** | Operational model runs | Model artifacts loaded, features computed cleanly | **READY** |
| **11. Risk Assessment** | Assessment stored in DB | Tested across full lifecycle | **READY** |
| **12. High-Risk Case Creation** | Conditional case opened | Opens case if threshold met, audited in DB | **READY** |
| **13. AI Investigation** | Gemini multi-turn run | Successfully verified live on synthetic demo case | **HISTORICALLY VERIFIED** |

