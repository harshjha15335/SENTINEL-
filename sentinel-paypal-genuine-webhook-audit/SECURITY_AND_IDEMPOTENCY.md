# Security, Merchant Isolation & Idempotency Audit

**Components:** Multi-tenant boundaries, Database constraints, Cryptographic controls  
**Scope:** Prevention of unauthorized financial mutations, replay attacks, cross-tenant leaks, and resource exhaustion  

---

## 1. Zero Unauthorized Financial Mutation Guarantee

SENTINEL enforces strict, hard-coded guardrails preventing automated or unauthorized movements of money:

1. **Refund Execution Lock:**
   - Setting: `SENTINEL_REFUND_EXECUTION_ENABLED = false`
   - Verified via: `apps/api/app/core/config.py` and `deploy/render-continuous.yaml`.
   - In `apps/api/app/api/v1/refunds.py`:
     Any attempt to dispatch a refund to PayPal Sandbox when this flag is `false` raises HTTP 403 Forbidden with error code `"refund_execution_disabled"`.
2. **Dispute Non-Submission:**
   Dispute tools and routes read stored records only. No PayPal dispute response or evidence upload is initiated automatically.
3. **Investigation Read-Only Sandbox:**
   The PydanticAI investigation agent is bound exclusively to read-only tools on `CaseToolbox`. Zero tools exist for capturing, voiding, or refunding payments.

---

## 2. Multi-Tenant Merchant Isolation

SENTINEL isolates data across distinct merchants at both the database and service levels:

1. **Foreign Key Integrity:**
   Every `Transaction`, `Case`, `PaymentEvent`, `RiskAssessment`, and `AuditEvent` carries a mandatory `merchant_id` foreign key referencing `merchants.id`.
2. **Scoping in Queries:**
   - `load_history` strictly queries `Transaction.merchant_id == txn.merchant_id`. Payer transactions with merchant A are never exposed to merchant B.
   - `CaseToolbox` is instantiated for a specific `case_id` pre-authenticated under the user's merchant session. Tool signatures accept zero merchant IDs from the LLM, making tenant escalation impossible.
3. **Database Constraints:**
   Composite indexes on `(merchant_id, created_at)` enforce partition isolation and query performance.

---

## 3. Cryptographic Signature & SSRF Defense

1. **Certificate Host Protection:**
   The `SignatureVerifier` strictly checks that `PAYPAL-CERT-URL` originates from PayPal-managed domains:
   - `api.paypal.com`
   - `api.sandbox.paypal.com`
   - `api-m.paypal.com`
   - `api-m.sandbox.paypal.com`
   Any custom or internal URL (e.g. `http://169.254.169.254` or internal loopback) is rejected before network resolution, eliminating SSRF vulnerabilities.
2. **Max Certificate Size:**
   Certificate streaming limits response length to `64 KB`. Responses exceeding this are rejected, mitigating Denial of Service (DoS) attacks via memory exhaustion.

---

## 4. Webhook Idempotency & Replay Resistance

Webhooks are untrusted, inherently at-least-once networks where duplicate deliveries, network retries, and out-of-order packets frequently occur. SENTINEL protects against duplicates at every tier:

| Tier | Deduplication Mechanism | Behavior on Duplicate |
| :--- | :--- | :--- |
| **Supabase Receiver** | `sentinel_enqueue_webhook` RPC with `ON CONFLICT (provider_event_id)` | Returns `200 { received: true, duplicate: true }`. Zero duplicate rows inserted. |
| **Durable Inbox** | `sentinel_claim_webhooks` with `FOR UPDATE SKIP LOCKED` | Only one worker can hold the lease token. Concurrent workers skip locked row. |
| **FastAPI Ingestion** | `payment_events.provider_event_id` unique constraint | Increments `delivery_count`, preserves single row, skips background job. |
| **Scoring Jobs** | `risk_scoring_jobs.transaction_id` unique constraint | `ON CONFLICT DO NOTHING` prevents duplicate scoring runs for the same transaction. |
| **Transaction Status** | Monotonic Status Precedence (`_RANK`) | Out-of-order events cannot regress a `CAPTURED` transaction back to `PENDING`. |

All idempotency and deduplication mechanisms passed testing in `apps/api/tests/test_webhooks.py` and `apps/api/tests/test_supabase_inbox.py`.
