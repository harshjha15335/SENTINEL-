# SENTINEL - APPLICATION SECURITY & SAFETY VERIFICATION

## 1. Safety Boundaries & Financial Guards Verification

SENTINEL was developed as an analyst-in-the-loop risk intelligence platform for the PayPal AI Hackathon. Strict application-layer safeguards prevent unauthorized financial mutations, autonomous actions, and data exfiltration.

---

## 2. Guardrails Verification Matrix

| Safeguard | Configuration / Implementation | Verification Status | Proof & References |
|---|---|---|---|
| **Refund Execution Disabled** | `SENTINEL_REFUND_EXECUTION_ENABLED=false` | **VERIFIED HARD-LOCKED** | [`apps/api/app/config.py`](file:///C:/Users/ranja/Sentinel/SENTINEL-/apps/api/app/config.py). `execute_refund` endpoint returns HTTP 403 / 501 when flag is false. |
| **Dispute Submission Disabled** | External dispute transmission mocked/draft-only | **VERIFIED HARD-LOCKED** | Disputes remain in `DRAFT` state for human review. No outbound external dispute API call is dispatched. |
| **Judge Demonstration Role** | Read-only RBAC role `Role.JUDGE` | **VERIFIED HARD-LOCKED** | Judge accounts can only view synthetic demonstration cases. Any `POST`, `PUT`, `DELETE`, or refund approval action returns `HTTP 403 Forbidden`. |
| **Case-Scoped AI Investigation Tools** | `CaseToolbox` session scoping | **VERIFIED BOUNDED** | AI agent tools (`get_case_information`, `get_transaction_details`, etc.) require active `case_id` and `merchant_id` context. Tools are 100% read-only and cannot mutate transactions. |
| **Credential & Secret Protection** | Redaction in loggers and exceptions | **VERIFIED SAFE** | Unit tests in `test_paypal_oauth_audit.py` and `test_provider_diagnostics.py` verify that `client_secret` and API keys are stripped before logging. |
| **Evidence Tamper Resistance** | SHA-256 Hashing & Private Storage | **VERIFIED IMMUTABLE** | All evidence files uploaded to the private evidence vault are hashed upon ingest (`evidence_hash`) and validated against tamper attempts. |
| **Diagnostic Sanitization** | `extract_safe_diagnostics` | **VERIFIED ALLOWLISTED** | Diagnostic error parser filters raw provider error text, preventing prompt injection echoes or internal stack leakage to clients. |

---

## 3. Human-in-the-Loop Architecture

SENTINEL operates strictly as a decision support system:
1. **Analyst Review**: High-risk cases flagged by the calibrated XGBoost model generate investigation cases for human analysts.
2. **AI Findings as Recommendations**: Gemini / AI findings are presented as structured evidence citations with confidence scores. They do not trigger automated actions.
3. **Four-Eyes Principle**: Refund preparation and dispute responses require secondary approval by an authorized analyst or merchant supervisor before any action can be marked approved.
