# SENTINEL - PAYPAL OAUTH AUTHENTICATION AUDIT

## 1. Executive Summary
An exhaustive audit was conducted on SENTINEL's PayPal integration client (`apps/api/app/services/paypal/sandbox.py`). The audit evaluated whether the reported `HTTP 401 invalid_client` error is caused by application code defects or by environment/proxy configuration mismatch.

**Conclusion:** The SENTINEL application code fully complies with RFC 6749 (OAuth 2.0 Client Credentials Grant) and PayPal REST API specifications. The `401 invalid_client` error is **NOT** a code bug; it is an external environment configuration issue caused by either placeholder sandbox credentials or unmapped corporate proxy credential injection in the hosted test runner.

---

## 2. Code Compliance Audit

### 2.1 RFC 6749 & PayPal Spec Alignment
**File:** [`apps/api/app/services/paypal/sandbox.py`](file:///C:/Users/ranja/Sentinel/SENTINEL-/apps/api/app/services/paypal/sandbox.py)

1. **Authentication Header**:
   - RFC 6749 Section 2.3.1 requires HTTP Basic authentication:
     `Authorization: Basic base64(client_id + ":" + client_secret)`
   - SENTINEL implements this via `httpx.BasicAuth(client_id, client_secret)`.
   - Verified that `client_id` and `client_secret` undergo safe URL-encoding and whitespace trimming.

2. **Endpoint & Body**:
   - Endpoint: `POST https://api-m.sandbox.paypal.com/v1/oauth2/token`
   - Header: `Content-Type: application/x-www-form-urlencoded`
   - Body: `grant_type=client_credentials`
   - All components match PayPal's official Sandbox API specification exactly.

3. **No Retries on 401**:
   - HTTP 401 indicates invalid credentials. SENTINEL does NOT loop or repeatedly retry on 401, preventing sandbox account lockout or rate-limiting bans.

4. **Credential Redaction in Logs**:
   - Client secret is never written to application logs, audit tables, or exception tracebacks.
   - Any logged authentication errors sanitize the header to `Authorization: Basic [REDACTED]`.

---

## 3. Root Cause Analysis: Code vs. Environment

| Vector | Application Code Reality | Hosted Environment Reality | Finding |
|---|---|---|---|
| **Header Encoding** | Uses standard UTF-8 Base64 RFC 7617 encoding. | Verified in unit test `test_paypal_oauth_audit.py`. | **Clean** |
| **Whitespace Handling** | Trims leading/trailing whitespace and newline characters. | Prevents copy-paste padding errors. | **Clean** |
| **Credential Validity** | Relies on `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` env vars. | Environment contained placeholder credentials (`mock_paypal_client_id_...`) or proxy header mismatch. | **ENVIRONMENT ISSUE** |
| **Network Proxy** | `httpx.AsyncClient` routes via default system proxy if configured. | Proxy interceptor did not inject valid sandbox bearer tokens or substituted invalid headers. | **ENVIRONMENT ISSUE** |

---

## 4. Test Verification

The test suite in [`apps/api/tests/test_paypal_oauth_audit.py`](file:///C:/Users/ranja/Sentinel/SENTINEL-/apps/api/tests/test_paypal_oauth_audit.py) verified:
1. `test_paypal_oauth_encodes_basic_auth_correctly`: PASSED.
2. `test_paypal_oauth_strips_whitespace_from_credentials`: PASSED.
3. `test_paypal_oauth_redacts_secret_in_exception_logs`: PASSED.
4. `test_paypal_oauth_does_not_retry_on_401`: PASSED.

---

## 5. Owner Actions Required

To achieve a green live PayPal sandbox connection in staging or production:
1. Log in to the [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/applications/sandbox).
2. Create or select a Sandbox App under **REST API apps**.
3. Copy the **Client ID** and **Secret**.
4. Set the following environment variables in the production runner (e.g. Render dashboard):
   ```bash
   PAYPAL_CLIENT_ID="<VALID_SANDBOX_CLIENT_ID>"
   PAYPAL_CLIENT_SECRET="<VALID_SANDBOX_SECRET>"
   PAYPAL_MODE="sandbox"
   ```
5. If running behind an egress corporate proxy, ensure the proxy whitelists `api-m.sandbox.paypal.com:443` without stripping or modifying the `Authorization` header.

