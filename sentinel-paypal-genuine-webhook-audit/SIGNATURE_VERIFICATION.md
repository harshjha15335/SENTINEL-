# PayPal Webhook Signature Verification Audit

**Implementation:** `apps/api/app/services/webhooks.py` (`SignatureVerifier`, `classify_verification`)  
**Standard:** PayPal Developer Webhook Self-Verification Protocol (RSA-SHA256 with PKCS#1 v1.5)  

---

## 1. Cryptographic Protocol & Formula

PayPal signs webhook notifications using an asymmetric RSA key pair. SENTINEL implements the self-verification algorithm locally:

$$\text{message} = \text{transmission\_id} + "|" + \text{transmission\_time} + "|" + \text{webhook\_id} + "|" + \text{crc32}(\text{raw\_body})$$

```python
crc = zlib.crc32(raw_body) & 0xFFFFFFFF
message = f"{headers.transmission_id}|{headers.transmission_time}|{webhook_id}|{crc}"
signature = base64.b64decode(headers.transmission_sig, validate=True)
public_key.verify(signature, message.encode(), padding.PKCS1v15(), hashes.SHA256())
```

---

## 2. Security Boundaries & Safeguards

### A. Strict Certificate Host Allowlist
To prevent Server-Side Request Forgery (SSRF) and untrusted key injection, `SignatureVerifier._certificate` validates the `PAYPAL-CERT-URL`:
- Scheme must be `https:`
- Port must be default or 443
- Hostname must be in:
  - `api.paypal.com`
  - `api.sandbox.paypal.com`
  - `api-m.paypal.com`
  - `api-m.sandbox.paypal.com`
- Path must start with `/v1/notifications/certs/`
- Zero directory traversal (`..`) or URL encoding bypasses (`%`) permitted.
- Any request with an unauthorized cert URL raises `WebhookVerificationError("Certificate URL is not a PayPal HTTPS host")` and is rejected with HTTP 400.

### B. Certificate Expiry and Caching
- Certificates are parsed using Python's `cryptography.x509` module.
- Verification checks that current UTC time falls within `[not_valid_before_utc, not_valid_after_utc]`.
- Verified certificates are cached in an LRU cache (max 128 certificates) behind a thread lock.

### C. Byte-Level Integrity vs. JSON Reformats
Because PayPal calculates CRC32 over the exact bytes emitted by its HTTP client:
- Reformatting whitespace, reordering JSON keys, or pretty-printing changes the CRC32 checksum, causing verification to fail.
- SENTINEL extracts and preserves `await request.body()` exact raw bytes.

### D. Distinction: Live Sandbox vs. Webhook Simulator
- When using the Developer Dashboard simulator, PayPal signs using the literal string `"WEBHOOK_ID"` rather than the application's actual webhook ID.
- In `classify_verification`:
  ```python
  if configured_webhook_id:
      try:
          verifier.verify(headers, raw_body, configured_webhook_id)
          return EventVerification.VERIFIED
      except WebhookVerificationError:
          if not accept_simulator:
              raise
  if accept_simulator:
      verifier.verify(headers, raw_body, SIMULATOR_WEBHOOK_ID)
      return EventVerification.FIXTURE
  ```
- If an event matches the real registered webhook ID (`4J572318CT6195232`), it is tagged as `EventVerification.VERIFIED` (`DataOrigin.LIVE_SANDBOX`).
- If an event matches the simulator ID (`"WEBHOOK_ID"`), it is tagged as `EventVerification.FIXTURE` (`DataOrigin.SIMULATED`).
- In production (`settings.environment == "production"`), `accept_simulator` is strictly `False`, causing simulator events to fail closed.

---

## 3. Negative & Positive Security Test Evidence

The verification logic was executed against the following test cases in `apps/api/tests/test_webhooks.py`:

| Test Name | Scenario Exercised | Expected Outcome | Actual Result |
| :--- | :--- | :--- | :--- |
| `test_valid_signature_is_verified` | Valid RSA signature matching webhook ID | `EventVerification.VERIFIED` | **PASS** |
| `test_tampered_body_is_rejected` | Modifying 1 byte in payload after signing | `WebhookVerificationError` (400) | **PASS** |
| `test_reformatted_json_fails` | Pretty-printed JSON altering CRC32 | `WebhookVerificationError` (400) | **PASS** |
| `test_simulator_events_are_fixture` | Simulator payload with `WEBHOOK_ID` | `EventVerification.FIXTURE` | **PASS** |
| `test_simulator_rejected_when_disabled` | Simulator payload when `accept_simulator=False` | `WebhookVerificationError` (400) | **PASS** |
| `test_non_paypal_cert_host_rejected` | Malicious host `https://evil.example/cert.pem` | `WebhookVerificationError` (400) | **PASS** |
| `test_duplicate_delivery_is_idempotent` | Re-delivery of identical transmission | Returns existing event, 0 duplicates | **PASS** |

