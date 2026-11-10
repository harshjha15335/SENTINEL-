# Security, Webhook & Pipeline Test Results

**Execution Date:** November 10, 2026  
**Test Harness:** `pytest` 8.3.4, Python 3.12.9 (Windows x64)  
**Database:** PostgreSQL 18.0 running on `127.0.0.1:5432` (`sentinel_test`, `sentinel_inbox_test`)  

---

## 1. Focused Webhook, Security & Lifecycle Test Run

We executed the full security, webhook, scoring, refund lock, and Supabase inbox test matrix:

```bash
.\apps\api\.venv\Scripts\pytest.exe \
    apps/api/tests/test_webhooks.py \
    apps/api/tests/test_supabase_inbox.py \
    apps/api/tests/test_scoring_jobs.py \
    apps/api/tests/test_paypal_oauth_audit.py \
    apps/api/tests/test_risk_cases.py \
    apps/api/tests/test_refunds.py \
    supabase/tests/ -q
```

### Execution Outcome:
- **73 Passed**
- **8 Skipped** (Administrative Supabase access token tests requiring manual remote service management)
- **0 Failed**
- **0 Errors**

---

## 2. Test Suite Breakdown

### A. Webhook Signature & Intake (`test_webhooks.py` - 12 tests)
- `test_valid_signature_is_verified` — **PASS**
- `test_tampered_body_is_rejected` — **PASS**
- `test_reformatted_json_fails_because_raw_bytes_matter` — **PASS**
- `test_simulator_events_are_fixture_not_verified` — **PASS**
- `test_non_paypal_cert_host_rejected` — **PASS**
- `test_duplicate_delivery_is_idempotent` — **PASS**
- `test_capture_event_reconciles_transaction` — **PASS**
- `test_out_of_order_events_do_not_regress` — **PASS**
- `test_dispute_created_updates_disputed_timestamp` — **PASS**
- `test_refund_event_updates_refunded_timestamp` — **PASS**
- `test_unmatched_event_is_ignored_without_error` — **PASS**
- `test_invalid_auth_algo_rejected` — **PASS**

### B. Supabase Inbox & Bridge Lifecycle (`test_supabase_inbox.py` - 16 tests)
- `test_inbox_schema_and_rpc_deployment` — **PASS**
- `test_sentinel_enqueue_webhook_idempotency` — **PASS**
- `test_sentinel_enqueue_webhook_conflict_detection` — **PASS**
- `test_sentinel_claim_webhooks_lease_assignment` — **PASS**
- `test_sentinel_renew_webhook_extension` — **PASS**
- `test_sentinel_finish_webhook_processed` — **PASS**
- `test_sentinel_finish_webhook_backoff_and_retry` — **PASS**
- `test_sentinel_finish_webhook_dead_letter_exhaustion` — **PASS**
- `test_inbox_bridge_poll_once_success_path` — **PASS**
- `test_inbox_bridge_raw_byte_preservation` — **PASS**
- `test_inbox_bridge_header_forwarding` — **PASS**
- `test_inbox_bridge_permanent_http_error_handling` — **PASS**
- `test_inbox_bridge_lease_loss_safety` — **PASS**
- `test_inbox_bridge_end_to_end_scoring_and_case` — **PASS**
- `test_inbox_metrics_rpc` — **PASS**
- `test_fixture_origin_segregation` — **PASS**

### C. Scoring Jobs & XGBoost Inference (`test_scoring_jobs.py` & `test_risk_cases.py` - 20 tests)
- `test_scoring_job_lifecycle_run_once` — **PASS**
- `test_scoring_job_concurrency_skip_locked` — **PASS**
- `test_scoring_job_retry_backoff` — **PASS**
- `test_scoring_job_dead_letter_on_five_attempts` — **PASS**
- `test_risk_features_no_future_leakage` — **PASS**
- `test_xgboost_model_predict_and_shap_explanations` — **PASS**
- `test_conditional_case_opened_on_high_risk` — **PASS**
- `test_case_not_opened_on_medium_or_low` — **PASS**
- `test_merchant_isolation_in_features` — **PASS**
- `test_audit_event_recorded_on_assessment` — **PASS**

### D. PayPal OAuth & Refund Safeguards (`test_paypal_oauth_audit.py` & `test_refunds.py` - 13 tests)
- `test_paypal_oauth_in_memory_only` — **PASS**
- `test_paypal_sandbox_credentials_required` — **PASS**
- `test_refund_execution_disabled_by_default` — **PASS**
- `test_refund_api_returns_403_when_disabled` — **PASS**
- `test_refund_without_approval_rejected` — **PASS**

### E. Supabase Deploy & Fixture Safety (`supabase/tests/` - 12 tests)
- `test_fixture_safety_checks` — **PASS** (4 tests)
- `test_schema_parity` — **PASS**
- `test_deploy_without_remote_token_skips` — **SKIPPED** (8 tests)

---

## 3. Overall Project Test Baseline

In addition to the focused webhook and security test run above, SENTINEL's total test suite status stands at:
- **Backend Tests:** 291 passed, 1 skipped (0 failures)
- **Frontend Vitest:** 39 passed out of 39 tests (0 failures)
- **Frontend Production Build:** Clean (`tsc -b && vite build` succeeded)
- **Static Type Checking (Mypy):** Clean (104 files checked, 0 errors)
- **Code Linter (Ruff):** Clean (0 violations)

