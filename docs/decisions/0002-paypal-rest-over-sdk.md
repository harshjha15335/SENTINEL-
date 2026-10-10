# 0002 · Direct PayPal REST over HTTPX instead of the Server SDK

Status: accepted (2026-10-10)

**Context.** The brief asks to evaluate the current official PayPal Server SDK rather than the
legacy Checkout SDKs the research report recommends. We inspected `paypal-server-sdk` 2.4.0 (the
wheel): controllers cover OAuth, Orders, Payments, Vault, Subscriptions and Transaction Search.
There is no Disputes controller and no webhook verification. Its licence is a custom PayPal licence.

**Decision.** Implement `SandboxPayPalGateway` with HTTPX against documented endpoints:
`/v1/oauth2/token`, `/v2/checkout/orders`, `/v2/checkout/orders/{id}/capture`,
`/v2/payments/captures/{id}`, `/v2/payments/captures/{id}/refund`, `/v1/customer/disputes`.
Business code depends on the `PayPalGateway` protocol; a `FixturePayPalGateway` exists for offline
work and labels everything it produces `SIMULATED`.

**Consequences.** One error-classification path, one place for `PayPal-Request-Id` idempotency,
timeouts and retry rules (retries only when an idempotency key makes them safe). The base URL is
hard-coded to the sandbox host; adding live support would require a deliberate code change.
We must track API changes ourselves; HTTP-level tests pin the request shapes we rely on.
