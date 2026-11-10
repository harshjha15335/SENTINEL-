# Durable Webhook Inbox & Bridge Worker Audit

**PostgreSQL Inbox Schema:** `public.sentinel_webhook_inbox`  
**Bridge Worker:** `apps/api/app/workers/supabase_inbox.py`  
**Bridge Forwarding Engine:** `apps/api/app/services/inbox_bridge.py`  

---

## 1. Database Schema & RPC Functions

The webhook inbox in Supabase is managed through two versioned SQL migrations:
- `supabase/migrations/202610200001_webhook_inbox.sql`
- `supabase/migrations/202610220002_bridge_lifecycle.sql`

### Key Schema Characteristics:
1. **Row-Level Security (RLS) Enforced:**
   `REVOKE ALL ON public.sentinel_webhook_inbox FROM public, anon, authenticated;`
   `GRANT SELECT, INSERT, UPDATE ON public.sentinel_webhook_inbox TO service_role;`
   The table is completely invisible and inaccessible to standard web clients or anonymous API calls. Only the server-side `service_role` key can interact with it.

2. **State & Concurrency Control:**
   - Table columns: `id`, `provider_event_id` (unique), `event_type`, `raw_body`, `signature_headers` (JSONB), `received_at`, `processed_at`, `attempts`, `lease_token` (UUID), `available_at`, `last_error`, `data_origin` (`LIVE_SANDBOX` / `SIMULATED`), `status` (`PENDING`, `RUNNING`, `PROCESSED`, `DEAD`).
   - Partial index:
     `sentinel_webhook_pending ON public.sentinel_webhook_inbox (available_at, received_at) WHERE processed_at IS NULL;`

3. **Atomic RPC Operations:**
   - `sentinel_claim_webhooks(p_limit, p_origin)`:
     Uses PostgreSQL `FOR UPDATE SKIP LOCKED`.
     Claims up to `p_limit` rows where `status IN ('PENDING', 'RUNNING')` and `available_at <= now()`.
     Generates a unique `lease_token = gen_random_uuid()`, updates `available_at = now() + 2 minutes`, increments `attempts`, and sets `status = 'RUNNING'`.
     Dead-letters any row exceeding 10 attempts (`status = 'DEAD', last_error = 'LeaseExhausted'`).
   - `sentinel_renew_webhook(p_id, p_lease_token)`:
     Extends the lease by 2 minutes provided the worker still holds the matching token.
   - `sentinel_finish_webhook(p_id, p_lease_token, p_success, p_error)`:
     If successful: marks `status = 'PROCESSED', processed_at = now(), lease_token = null`.
     If failed: marks `status = 'PENDING'`, releases lease, and calculates exponential backoff:
     `available_at = now() + least(300, 5 * 2^attempts) seconds`.
     If error is permanent (`p_error LIKE 'PERMANENT_%'`) or `attempts >= 10`: marks `status = 'DEAD'`.

---

## 2. Inbox Bridge Implementation (`inbox_bridge.py`)

The bridge worker polls Supabase and forwards receipts to FastAPI:

```
[Supabase Inbox] --(sentinel_claim_webhooks)--> [Bridge Worker] --(HTTP POST exact raw bytes)--> [FastAPI /api/v1/webhooks/paypal]
       ^                                                |                                                        |
       |                                                v                                                        v
       +--(sentinel_finish_webhook: PROCESSED)<---------+<-----------------(HTTP 200 {received: true, durable: true})--+
```

### Critical Reliability Safeguards:
1. **Raw Byte Fidelity:**
   The bridge extracts `row["raw_body"]` and encodes it directly as UTF-8 bytes (`raw = row["raw_body"].encode("utf-8")`). It does NOT re-serialize or reformat the JSON, guaranteeing that the CRC32 checksum in PayPal's signature remains 100% valid.
2. **Signature Header Forwarding:**
   Extracts and attaches the exact original transmission headers:
   - `paypal-transmission-id`
   - `paypal-transmission-time`
   - `paypal-cert-url`
   - `paypal-auth-algo`
   - `paypal-transmission-sig`
3. **Defense Against Premature Acknowledgment:**
   The bridge checks the JSON response from FastAPI against strict criteria:
   - `received == True`
   - `durable == True`
   - `event_id == payload["id"]`
   - `payload_sha256 == sha256(raw)`
   - `verification_status == "VERIFIED"`
   If any check fails or FastAPI returns an error, the bridge **refuses** to acknowledge the receipt.
4. **Lease Protection & Idempotency:**
   If a worker crashes mid-forwarding, the lease expires after 2 minutes, and another worker safely reclaims the event. Because FastAPI and PostgreSQL enforce unique constraint deduplication, retried deliveries are idempotent and do not create duplicate transactions or scoring jobs.

---

## 3. Test Verification

The entire lifecycle (claiming, lease renewal, raw forwarding, acknowledgment, lease expiry, and retry backoff) is covered by 28 passing integration tests in:
- `apps/api/tests/test_supabase_inbox.py`
- `apps/api/tests/test_webhooks.py`

