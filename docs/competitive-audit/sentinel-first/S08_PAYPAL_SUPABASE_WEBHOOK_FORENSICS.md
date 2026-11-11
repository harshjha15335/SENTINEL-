# S08 — PAYPAL SANDBOX AND SUPABASE WEBHOOK FORENSICS

**Audit Subject:** Genuine PayPal Sandbox Transaction & Webhook Lifecycle  
**Target Order ID:** `2PE07332LD3413239` ($25.00 USD)  
**Authoritative Status:** `COMPLETED` / `CAPTURED`  

---

## 1. TRANSACTION AND PAYMENT PROVENANCE LEDGER

| Dimension | Identifier / Value | Database Verification | Authoritative Proof |
| :--- | :--- | :--- | :--- |
| **PayPal Sandbox Order** | `2PE07332LD3413239` | `orders.provider_order_id` | PayPal Orders v2 GET: status `COMPLETED` |
| **PayPal Sandbox Capture** | `8P799281C8558761R` | `transactions.provider_capture_id` | PayPal Capture v2 GET: status `COMPLETED` |
| **Local Transaction Record**| `b970504f-274f-4862-b95f-b95342002421`| `transactions.id` | Status: `CAPTURED`, idempotency key intact |
| **XGBoost Risk Assessment**| `dae7c7f2-af13-4352-8f96-cbb74c2b02d6`| `risk_assessments.id` | Score: `0.0869`, Band: `MEDIUM`, Decision: `REVIEW` |
| **Scoring Job Record** | `b27c85dc-4d62-4aba-97c9-da57a43557a5`| `risk_scoring_jobs.id` | Status: `COMPLETED`, points to `dae7c7f2` |
| **Dual-Path Idempotency** | Exactly **1** RiskAssessment row | `risk_assessments` table | Zero duplicate evaluations, zero re-scores |

---

## 2. WEBHOOK RECONCILIATION SUMMARY (3/3 RECONCILED)

```
Event 1: CHECKOUT.ORDER.APPROVED
  - Provider Event ID: WH-7CF83637DW062373H-6LR45473H4359051V
  - Local PaymentEvent ID: c4637f51-9d86-4ec4-bcf7-bb61fdf593bd
  - Processing Status: PROCESSED | Verification: VERIFIED

Event 2: PAYMENT.CAPTURE.COMPLETED
  - Provider Event ID: WH-8PS64288TE824605G-0B900988FU9876821
  - Supabase Inbox Row: 9881abb6-c422-4432-9004-f9a49d9a16c2
  - Local PaymentEvent ID: 65d36059-d0e3-4cb7-bd0b-5b9ab279f1c9
  - Processing Status: PROCESSED | Verification: VERIFIED

Event 3: CHECKOUT.ORDER.COMPLETED
  - Provider Event ID: WH-54N10890L8355240E-53J420738E8789622
  - Local PaymentEvent ID: 293db5f7-0c7b-4864-a902-791c32832e36
  - Processing Status: PROCESSED | Verification: VERIFIED
```

---

## 3. ROOT CAUSE AUDIT: INBOX ROW `9881abb6-c422-4432-9004-f9a49d9a16c2`

### The Discrepancy:
Supabase inbox row `9881abb6-c422-4432-9004-f9a49d9a16c2` held genuine event `WH-8PS64288TE824605G-0B900988FU9876821` (`PAYMENT.CAPTURE.COMPLETED`). Its status in Supabase was `PROCESSED` with `claim_count = 1` and `processed_at = 2026-11-10T17:21:49 UTC`. However, FastAPI had not received this event at that time, and Uvicorn access logs recorded zero HTTP requests at `17:21:49 UTC`.

### Audit of All Writers:
1. `inbox_bridge.py`: Requires HTTP 2xx and matching FastAPI receipt JSON before calling `sentinel_finish_webhook`. The live bridge on port `8040` was healthy but recorded only 2 successful events.
2. `supabase/migrations/202610220002_bridge_lifecycle.sql` (Line 8): Migration backfill `UPDATE sentinel_webhook_inbox SET status = 'PROCESSED' WHERE processed_at IS NOT NULL;`.
3. Offline test or diagnostic script with `service_role` credentials.

> [!WARNING]
> **Definitive Finding on Historical Root Cause:**
> The exact process or caller that updated row `9881abb6` at `17:21:49 UTC` cannot be conclusively identified from surviving database records because PostgreSQL row updates do not preserve caller process identifiers.
> 
> **Operational Risk:** Manual recovery demonstrated that the event payload was authentic and could be processed idempotently. However, **manual recovery does not constitute an unconditional guarantee of automatic webhook delivery in a live cloud environment**. This remains an operational risk until validated on the hosted staging host.

