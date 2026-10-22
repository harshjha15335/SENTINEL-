# Provider verification — 22 October 2026

## Distinct evidence levels

- Configuration presence: a variable or Edge secret name exists.
- Network reachability: a request traverses the proxy with TLS verification enabled and receives an upstream response.
- Authentication: a nonfinancial provider credential operation succeeds.
- Provider event: an actual provider event and its signature are accepted and reconciled.
- Fixture pipeline: injected verification and labelled simulated records exercise our infrastructure.

These are separate claims. No successful fixture or configured variable substitutes for genuine provider verification.

## Current PayPal findings

Read-only HEAD requests to `api.sandbox.paypal.com`, `api.paypal.com` and `api-m.paypal.com` now pass the proxy CONNECT stage and return upstream HTTP 406, 404 and 406 respectively. `api-m.sandbox.paypal.com` passes CONNECT but returns an upstream Cloudflare 403 at its root. These are different from the earlier proxy-generated CONNECT 403 denials. Curl preserved TLS verification. Local DNS did not resolve these names; the successful proxied requests show that local DNS failure does not imply the proxy cannot reach the upstream. Independent direct DNS/TCP/TLS stages were not measured outside the supported proxy path.

The draft contains the three exact certificate hosts; runtime access is now effective. This session did not publish cloud configuration. We cannot infer which UI action activated it or whether the entire saved configuration was published. No broader network permission was added to fetch blocked hosting documents.

A separate read-only-in-effect sandbox OAuth client-credentials check through `SandboxPayPalGateway.check_credentials()` failed with category **AUTHENTICATION**. It created no order and made no capture/refund call. Existing injected credentials or their delivery binding must be corrected securely; an encoded proxy-placeholder credential is not established as a transferable raw secret. No secret values or token bodies were printed or stored in this report. Do not request credentials in chat.

The Supabase receiver remains ACTIVE version 4 at:

`https://cfslzvvdjxstpupkqbpw.supabase.co/functions/v1/paypal-webhook`

All three PayPal Edge secret names are present. Python is configured with the supplied registered webhook ID. Edge-secret presence does not prove those secrets authenticate. The deployed receiver was not redeployed. No genuine PayPal payment or event has been verified. The user's restriction against initiating a genuine sandbox payment remains in effect.

## Current AI findings

The recovered application uses `SENTINEL_AI_PROVIDER`, `SENTINEL_AI_MODEL` and `SENTINEL_AI_API_KEY`. No usable real AI key/model combination is available for a provider-backed verification run in this workspace. Unit tests use scripted models; the judge scenario deliberately uses the deterministic summary. The real-AI integration test is skipped. No LLM provider success is claimed.

The operations page reports configuration and recorded merchant events/agent runs independently. Readiness explicitly says provider verification is not established by readiness. An agent-run timestamp is a stored execution record, not an independently attested model-quality result.

## Safe next checks

After secure runtime credentials/bindings are corrected, repeat only the nonfinancial OAuth check. Genuine sandbox payment, refund or dispute submission tests require separate explicit authorization. Keep provider tests separate from hosted fixtures. A real LLM investigation requires a supported model/key, network access, a bounded authorized test and an explicit record of its results.

Official hackathon URL supplied by the user is `https://paypalaihackathon.devpost.com/`. It is currently blocked by workspace CONNECT policy, so its rules/deadline were not independently verified. The supplied deadline is November 12, 2026 at 12:00 PM PST; do not present that as a fetched rules confirmation.
