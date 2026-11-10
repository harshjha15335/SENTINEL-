# SENTINEL — Post-Capture Provenance and Causal Chain Audit Report

**Date:** 2026-11-10  
**Audit Target:** Transaction `b970504f-274f-4862-b95f-b95342002421`  
**PayPal Order ID:** `2PE07332LD3413239`  
**PayPal Capture ID:** `8P799281C8558761R`  
**Risk Assessment ID:** `dae7c7f2-af13-4352-8f96-cbb74c2b02d6`  
**Capture Webhook ID:** `WH-8PS64288TE824605G-0B900988FU9876821`  
**Audit Mode:** Read-Only Verification (Zero Mutations)

---

## 1. Executive Summary

This audit establishes the exact causal provenance of SENTINEL's genuine PayPal Sandbox payment of **$25.00 USD**, the resulting `LIVE_SANDBOX` XGBoost risk assessment, and the webhook delivery lifecycle.

### Core Discoveries:
1. **Risk Assessment Preceded Webhook Generation:**
   `RiskAssessment` `dae7c7f2-af13-4352-8f96-cbb74c2b02d6` was created at **17:20:35 UTC** synchronously upon the HTTP 201 response to PayPal's capture endpoint (`POST /v2/checkout/orders/{id}/capture` completed at **17:20:33 UTC**). PayPal's asynchronous notification queue did not emit `WH-8PS64288TE824605G-0B900988FU9876821` (`PAYMENT.CAPTURE.COMPLETED`) until **17:21:35 UTC** (60 seconds later).

2. **Reconciliation of Inbox Metrics vs. Ingress Payments:**
   - PayPal emitted 3 events:
     * `WH-7CF83637DW062373H-6LR45473H4359051V` (`CHECKOUT.ORDER.APPROVED`)
     * `WH-54N10890L8355240E-53J420738E8789622` (`CHECKOUT.ORDER.COMPLETED`)
     * `WH-8PS64288TE824605G-0B900988FU9876821` (`PAYMENT.CAPTURE.COMPLETED`)
   - All 3 arrived at Supabase Edge Function `/functions/v1/paypal-webhook` and were recorded in `sentinel_webhook_inbox`.
   - The Supabase Bridge worker forwarded Events 1 and 2 to FastAPI, which verified their signatures and persisted them as `PaymentEvent` records `c4637f51-9d86-4ec4-bcf7-bb61fdf593bd` and `293db5f7-0c7b-4864-a902-791c32832e36`.
   - Event 3 (`PAYMENT.CAPTURE.COMPLETED`) was **never posted to FastAPI**. FastAPI logs show exactly two incoming webhook requests, and `WorkerHealth.processed = 2`. The bridge-to-FastAPI hop for Event 3 is unverified.

3. **Scoring Execution Path (Direct vs. Webhook):**
   - Scoring occurred strictly via `score_after_capture()` in `apps/api/app/services/checkout.py`.
   - No `RiskScoringJob` was ever enqueued (query for transaction returned 0 rows).
   - The assessment record explicitly carries `trigger: "capture"`.

---

## 2. End-to-End Timeline & Evidence Table

| Sequence | Component | Action / Event | Identifier / Hash | Timestamp (UTC) | Status / Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | SENTINEL API | Order Created | `b970504f-274f-4862-b95f-b95342002421` | 2026-11-10 17:08:18 | `ORDER_CREATED` |
| 2 | PayPal Sandbox | Buyer Approval | `DV6EHMWFVQG26` | 2026-11-10 17:15:45 | `APPROVED` |
| 3a | PayPal Webhook 1 | Emitted | `WH-7CF83637DW062373H-6LR45473H4359051V` | 2026-11-10 17:15:52 | `CHECKOUT.ORDER.APPROVED` |
| 3b | Supabase Receiver | Ingested to Inbox | Inbox Row 1 | 2026-11-10 17:15:54 | `PROCESSED` |
| 3c | FastAPI Ingress | Webhook Verified | `c4637f51-9d86-4ec4-bcf7-bb61fdf593bd` | 2026-11-10 17:15:55 | HTTP 200, `VERIFIED` |
| 4 | PayPal Sandbox | Synchronous Capture | `8P799281C8558761R` | 2026-11-10 17:20:33 | HTTP 201, `COMPLETED` |
| 5 | SENTINEL Risk Engine | Synchronous XGBoost | `dae7c7f2-af13-4352-8f96-cbb74c2b02d6` | 2026-11-10 17:20:35 | Score: `0.0869`, `trigger: "capture"` |
| 6a | PayPal Webhook 2 | Emitted | `WH-54N10890L8355240E-53J420738E8789622` | 2026-11-10 17:21:04 | `CHECKOUT.ORDER.COMPLETED` |
| 6b | Supabase Receiver | Ingested to Inbox | Inbox Row 2 | 2026-11-10 17:21:05 | `PROCESSED` |
| 6c | FastAPI Ingress | Webhook Verified | `293db5f7-0c7b-4864-a902-791c32832e36` | 2026-11-10 17:21:19 | HTTP 200, `VERIFIED` |
| 7a | PayPal Webhook 3 | Emitted | `WH-8PS64288TE824605G-0B900988FU9876821` | 2026-11-10 17:21:35 | `PAYMENT.CAPTURE.COMPLETED` |
| 7b | Supabase Receiver | Ingested to Inbox | Inbox Row 3 | 2026-11-10 17:21:49 | Metric recorded in group |
| 7c | Bridge Forwarding | Forward to FastAPI | `WH-8PS64288TE824605G-0B900988FU9876821` | — | **MISSING / UNVERIFIED** |
| 7d | Webhook Scoring Job | Enqueue to Pipeline | Transaction `b970504f...` | — | **NOT EXECUTED** (0 rows) |

---

## 3. Provenance Classification: PARTIAL PROVENANCE

- **Verified End-to-End:** Genuine PayPal Sandbox $25.00 capture, synchronous `LIVE_SANDBOX` XGBoost tree-SHAP evaluation, audit events, and order lifecycle webhooks (`CHECKOUT.ORDER.APPROVED`, `CHECKOUT.ORDER.COMPLETED`).
- **Unverified Segment:** Asynchronous forwarding of `PAYMENT.CAPTURE.COMPLETED` from the Supabase Bridge to FastAPI, and subsequent execution of a background `RiskScoringJob`.

