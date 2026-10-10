# 0004 · Durable webhook processing in PostgreSQL, no broker

Status: accepted (2026-10-10)

**Decision.** The webhook endpoint verifies the signature, stores the exact raw body
(`raw_payloads`) and an event row (`payment_events`, unique `provider_event_id`), commits, and only
then returns 2xx. Processing runs after the response (FastAPI background task) and is re-driven by
`python -m app.workers.events`, which picks up RECEIVED/FAILED events under an attempt cap.
Transaction updates follow a status precedence so late or out-of-order events cannot regress state.

**Consequences.** No Redis/Celery to deploy. If job volume grows (OCR, batch scoring), introduce
a queue then; the event table already records attempts and errors.
