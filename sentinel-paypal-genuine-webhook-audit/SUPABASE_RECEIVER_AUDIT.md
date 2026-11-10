# Supabase Edge Function Webhook Receiver Audit

**Receiver URL:** `https://cfslzvvdjxstpupkqbpw.supabase.co/functions/v1/paypal-webhook`  
**Supabase Project ID:** `cfslzvvdjxstpupkqbpw`  
**Edge Function Implementation:** `supabase/functions/paypal-webhook/receiver.ts`  
**Live Probe Execution:** 2026-11-10T09:44:15Z (15:14:15 IST)  

---

## 1. Live Accessibility Probe

An unauthenticated GET request was dispatched to probe edge runtime liveness:

```http
GET /functions/v1/paypal-webhook HTTP/1.1
Host: cfslzvvdjxstpupkqbpw.supabase.co
```

**Live Response Headers & Body:**
```http
HTTP/1.1 200 OK
Content-Type: application/json
Date: Tue, 10 Nov 2026 09:44:15 GMT
Server: cloudflare
sb-project-ref: cfslzvvdjxstpupkqbpw
x-served-by: supabase-edge-runtime
x-deno-execution-id: 4bb28c18-2e0d-44b3-b3bb-f28212731d68
x-sb-edge-region: ap-south-1

{"status":"ok","mode":"sandbox"}
```

**Assessment:**
- The Edge Function is **ONLINE**, responding directly from Supabase's edge runtime in `ap-south-1`.
- The status check confirms the receiver is compiled, loaded, and operating in `sandbox` mode.

---

## 2. Source Code & Security Architecture Audit

We inspected `supabase/functions/paypal-webhook/receiver.ts`:

### A. Strict HTTP Method & Size Controls
- Method gate: `GET` returns health status; non-POST requests return `405 method_not_allowed`.
- Payload size guard: Max `256 KB` (`262,144 bytes`). If incoming bytes exceed this limit, the reader cancels the stream and immediately returns `413 payload_too_large`.

### B. Header Preservation & Validation
The receiver mandates all 5 PayPal transmission headers:
1. `paypal-transmission-id`
2. `paypal-transmission-time`
3. `paypal-cert-url`
4. `paypal-auth-algo`
5. `paypal-transmission-sig`

- If any header is missing or exceeds 8,192 bytes, it rejects with `400 invalid_signature_headers`.
- Validates that `paypal-cert-url` is HTTPS on an approved PayPal host (`api.paypal.com`, `api.sandbox.paypal.com`, `api-m.paypal.com`, `api-m.sandbox.paypal.com`) under `/v1/notifications/certs/`.

### C. Live PayPal Pre-Verification (At Edge)
- Acquires a short-lived OAuth token from PayPal Sandbox.
- Dispatches a verification request to PayPal's `/v1/notifications/verify-webhook-signature`.
- If PayPal returns anything other than `verification_status: "SUCCESS"`, the edge function immediately rejects the request with `400 signature_rejected`.

### D. Atomic Durable Enqueue
- Dispatches an atomic PostgreSQL RPC call to Supabase:
  `POST /rest/v1/rpc/sentinel_enqueue_webhook`
  With parameters:
  - `p_event_id`: the PayPal event ID.
  - `p_event_type`: the event type string.
  - `p_raw_body`: the exact, unmodified raw JSON string.
  - `p_headers`: JSON dictionary of the 5 verified PayPal signature headers.
- If an event with the exact same ID and payload was already enqueued, the RPC returns `false`, causing the function to respond with `200 { "received": true, "duplicate": true }` (idempotent acknowledgement).
- If an event arrives with an existing ID but conflicting body, the RPC raises `409 event_body_conflict`.
- Only after the database commit succeeds does the Edge Function return `200 OK` to PayPal.

---

## 3. Findings

The Supabase Edge Function receiver represents an exemplary defensive design:
1. It validates structure, size, and certificate origin before touching the database.
2. It verifies cryptographic signatures via PayPal Sandbox API.
3. It preserves raw bytes and signature headers for downstream re-verification in FastAPI.
4. It ensures at-least-once durable ingestion into PostgreSQL before acknowledging the webhook.

