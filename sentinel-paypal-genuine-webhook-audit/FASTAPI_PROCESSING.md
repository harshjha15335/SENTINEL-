# FastAPI Webhook Intake & Processing Audit

**Route File:** `apps/api/app/api/v1/webhooks.py` (`POST /api/v1/webhooks/paypal`)  
**Processing Engine:** `apps/api/app/services/webhooks.py` (`store_event`, `process_event`, `_apply`)  

---

## 1. Webhook Endpoint Contract

The `/api/v1/webhooks/paypal` route acts as SENTINEL's durable ingestion boundary:

```python
@router.post("/paypal")
async def paypal_webhook(
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    verifier: SignatureVerifier = Depends(get_verifier),
) -> JSONResponse:
```

### Execution Flow:
1. **Payload Size Guard:** Verifies `len(raw) <= 256 KB`. Returns `413 payload_too_large` if exceeded.
2. **Signature Verification:** Runs `classify_verification(verifier, headers, raw, settings.paypal_webhook_id)`.
3. **Durable Persistence (`store_event`):**
   - Computes SHA-256 of raw bytes.
   - Inserts into `raw_payloads` table with `ON CONFLICT DO NOTHING`.
   - Inserts into `payment_events` table with unique constraint on `provider_event_id`.
   - If an event with the same ID arrives again:
     - If payload SHA-256 and verification status match: increments `delivery_count` and returns `duplicate: true`.
     - If payload SHA-256 differs: raises `WebhookVerificationError("Event id conflicts with a stored delivery")`.
4. **Immediate Acknowledgment:**
   Returns HTTP 200 with receipt metadata:
   ```json
   {
     "received": true,
     "duplicate": false,
     "durable": true,
     "event_id": "<PAYPAL_EVENT_ID>",
     "payload_sha256": "<SHA256>",
     "verification_status": "VERIFIED",
     "data_origin": "LIVE_SANDBOX"
   }
   ```
5. **Asynchronous Background Processing:**
   Only if `created == True`, schedules `process_event(db, event.id)` via FastAPI `BackgroundTasks`.

---

## 2. Event Reconciliation Logic (`_apply`)

When `process_event` runs, it executes `_apply`:

```
PaymentEvent (PAYMENT.CAPTURE.COMPLETED)
       │
       ▼
Extract resource.id (Capture ID) and supplementary_data.related_ids.order_id
       │
       ▼
Query Transaction WHERE paypal_capture_id = capture_id OR paypal_order_id = order_id
       │
       ├─► [No Matching Txn] ──► Status: IGNORED ("No matching SENTINEL transaction")
       │
       └─► [Matching Txn Found]
               │
               ▼
       Validate amount and currency match exactly
               │
               ▼
       Update Transaction.status = CAPTURED (with status rank precedence)
               │
               ▼
       Record AuditEvent: "paypal.webhook.status_applied"
               │
               ▼
       Enqueue RiskScoringJob (app.services.risk.jobs.enqueue)
```

### Key Safety Guarantees:
1. **Rank Precedence Prevents Regressions:**
   Statuses are monotonic: `ORDER_CREATED (0) -> CAPTURE_PENDING (1) -> CAPTURED (2) -> PARTIALLY_REFUNDED (3) -> REFUNDED (4)`.
   A delayed or out-of-order `PAYMENT.CAPTURE.PENDING` event can never regress a transaction that has already reached `CAPTURED`.
2. **Amount & Currency Validation:**
   If `resource.amount` does not match `txn.amount_minor` and `txn.currency`, the transition is aborted with a `ValueError`.
3. **Audit Trail Preservation:**
   Every status transition records an immutable `AuditEvent` with actor type `PAYPAL_WEBHOOK`, containing the previous status, new status, and PayPal event ID.
