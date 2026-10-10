# PayPal Integration

## What is real today
| Capability | Code | Verified how |
|---|---|---|
| OAuth2 client-credentials token, cached with refresh margin, forced refresh on 401 | `SandboxPayPalGateway._access_token` | HTTP-level tests with `httpx.MockTransport` (`tests/test_sandbox_gateway.py`) |
| Create order (`POST /v2/checkout/orders`, intent CAPTURE, item breakdown, `PayPal-Request-Id`) | `create_order` | Mock tests assert body and headers |
| Capture (`POST /v2/checkout/orders/{id}/capture`, deterministic request id) | `capture_order` | Mock + API-level tests, amount mismatch test |
| Get order / capture, refund capture | `get_order`, `get_capture`, `refund_capture` | Implemented; refund is not exposed through any endpoint until the approval workflow exists |
| List/get disputes | `list_disputes`, `get_dispute` | 403 permission classification tested |
| Webhook signature verification | `services/webhooks.py` | Tests with a generated RSA cert: valid, tampered, reformatted JSON, simulator id, foreign cert host |
| Buyer approval UI | `CheckoutPage.tsx` (v6 `PayPalProvider` + `PayPalOneTimePaymentButton`) | Type-checked and built; renders only with a real client id |

**No request has been made to PayPal's sandbox in this session** because no credentials were
provided. Nothing in the repository claims otherwise.

## Credential dependency (exact)
1. Create a sandbox REST app at developer.paypal.com → Apps & Credentials (Sandbox).
2. Set in `apps/api/.env`: `SENTINEL_PAYPAL_MODE=sandbox`, `SENTINEL_PAYPAL_CLIENT_ID=…`, `SENTINEL_PAYPAL_CLIENT_SECRET=…`.
3. For webhooks: expose the API over HTTPS (e.g. a tunnel or the Render deployment), subscribe
   `https://<host>/api/v1/webhooks/paypal` to `PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.CAPTURE.PENDING`,
   `PAYMENT.CAPTURE.DENIED`, `PAYMENT.CAPTURE.REFUNDED`, `PAYMENT.CAPTURE.REVERSED`,
   `CHECKOUT.ORDER.APPROVED`, `CUSTOMER.DISPUTE.CREATED`, `CUSTOMER.DISPUTE.UPDATED`,
   `CUSTOMER.DISPUTE.RESOLVED`, and set `SENTINEL_PAYPAL_WEBHOOK_ID` to the id PayPal assigns.
4. Sandbox buyer account (Developer Dashboard → Sandbox accounts) to approve payments.
5. `GET /api/v1/paypal/status` (or Settings screen) shows whether the token request succeeds.

## Safety properties
- Base URL is hard-coded to `api-m.sandbox.paypal.com`. There is no live configuration path.
- Client never sends an amount; `CreateOrderRequest` forbids extra fields.
- Retries happen only for idempotent requests (`PayPal-Request-Id` present) on 429/5xx/timeouts.
- Resource ids are validated before being placed in URL paths.
- Errors are classified (`AUTHENTICATION`, `PERMISSION`, `VALIDATION`, `UNPROCESSABLE`, `NOT_FOUND`, `CONFLICT`, `RATE_LIMITED`, `PROVIDER_ERROR`, `NETWORK`) and surfaced with PayPal's `debug_id`, never with tokens.
- Webhooks: raw bytes preserved for CRC32; cert URL must be HTTPS on a PayPal API host; events persisted before 2xx; duplicates counted, not reprocessed; simulator events (`WEBHOOK_ID`) stored as `FIXTURE`/`SIMULATED` and rejected entirely when `SENTINEL_ENVIRONMENT=production`.

## Disputes (planned, Phase 5)
Capability detection via `list_disputes`: a `PERMISSION` error marks disputes unavailable for the
account and the UI switches to a clearly labelled simulated fixture. Sandbox dispute creation may
require buyer-side flows or account enablement; this is documented, not assumed.
