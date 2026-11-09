# SENTINEL - GEMINI HTTP 400 FIX IMPLEMENTATION REPORT

## 1. Overview
This report details the implementation of the code fixes that resolve the `HTTP 400 INVALID_ARGUMENT` failure when invoking Google Gemini (`gemini-3.1-flash-lite`) from the SENTINEL investigation agent, while strictly preserving offline verification boundaries and existing system safeguards.

---

## 2. Code Changes

### 2.1 Schema Transformer & Model Override
**File:** [`apps/api/app/services/investigation/provider.py`](file:///C:/Users/ranja/Sentinel/SENTINEL-/apps/api/app/services/investigation/provider.py)

1. **`SentinelGoogleJsonSchemaTransformer(GoogleJsonSchemaTransformer)`**:
   - Initialized with `prefer_inlined_defs=True` and `simplify_nullable_unions=True`.
   - Strips unsupported JSON schema keywords (`minItems`, `maxItems`, `uniqueItems`) from array schemas before Gemini validation.
   - Recursively walks and flattens all `$defs` and `$ref` pointers into self-contained OpenAPI 3.0 schema objects.

2. **`SentinelGoogleModel(GoogleModel)`**:
   - Overrides `prepare_request(model_settings, model_request_parameters)` to apply `SentinelGoogleJsonSchemaTransformer` to all tool definitions and output result schemas.
   - Overrides `_build_content_and_config` to patch PydanticAI's upstream modality bug:
     ```python
     # Remove conflicting responseModalities: ["TEXT"] when tool-calling is required
     if "responseModalities" in config and config["responseModalities"] == ["TEXT"]:
         del config["responseModalities"]
     ```
   - Upgrades function calling mode from conflicting `ANY` across 12 declarations to Google's native `VALIDATED` mode (compatible with Gemini 2.5 and 3+).

3. **`build_google()` Provider Factory**:
   - Instantiates `SentinelGoogleModel` instead of base `GoogleModel`.
   - Maintains timeout (15s) and retry policies (`HttpRetryOptions(attempts=3)`).

### 2.2 Temperature & Request Settings
**File:** [`apps/api/app/services/investigation/runner.py`](file:///C:/Users/ranja/Sentinel/SENTINEL-/apps/api/app/services/investigation/runner.py)

- Google's official Gemini 3 series documentation cautions against `temperature: 0.0` for reasoning models, which can cause internal decoding traps and argument rejections.
- Implemented model-specific temperature selection:
  ```python
  temperature = 1.0 if spec.provider == "google" else 0.0
  ```
- Retained token limit (2048) and deterministic fallback handler.

### 2.3 Safe Diagnostic Parser
**File:** [`apps/api/app/services/investigation/diagnostics.py`](file:///C:/Users/ranja/Sentinel/SENTINEL-/apps/api/app/services/investigation/diagnostics.py)

- Reconstructed and hardened the safe diagnostic parser missing from unpushed commit `2f592d72`.
- Strictly enforces field allowlisting: extracts HTTP status code, error type category (`invalid_configuration_value`), and schema field path (`parameters.properties.evidence_references`).
- **Refuses untrusted provider prose**: Raw message strings containing potential prompt echoes, internal stack traces, or merchant data are sanitized and never exposed to unauthenticated callers.

---

## 3. Preserved Security Safeguards

1. **Offline Non-Network SDK Transport**:
   - All tests run against in-memory HTTP transports (`MockTransport` / `InterceptTransport`).
   - Zero outbound requests to `generativelanguage.googleapis.com`.
   - Zero consumption of API quota or credits.

2. **Auditing & Fallback Integrity**:
   - In case of any provider rejection or network timeout, the investigation runner automatically catches the exception, registers structured audit diagnostics in `run.usage["diagnostic"]`, marks the investigation status as `FAILED`, and seamlessly switches to deterministic fallback.

3. **Case-Scoped Tool Isolation**:
   - Read-only tools remain strictly bounded by `case_id` and `merchant_id` session context.
   - Tools have no write capabilities and cannot mutate transaction or account state.

---

## 4. Verification Evidence

The implementation was verified using comprehensive automated tests:

1. **`apps/api/tests/test_google_provider.py`**:
   - `test_build_google_uses_explicit_retry_attempts`: PASSED.
   - `test_build_google_raises_on_missing_api_key`: PASSED.
   - `test_sentinel_google_model_inlines_defs_and_refs`: PASSED.
   - `test_sentinel_google_model_strips_text_modality_when_tools_present`: PASSED.
   - `test_sentinel_google_model_upgrades_mode_to_validated`: PASSED.
   - `test_sentinel_google_model_wire_serialization`: PASSED.

2. **`apps/api/tests/test_provider_diagnostics.py`**:
   - `test_extract_safe_diagnostics_known_field`: PASSED.
   - `test_extract_safe_diagnostics_unknown_field`: PASSED.
   - `test_extract_safe_diagnostics_category_mapping`: PASSED.
   - `test_extract_safe_diagnostics_handles_malformed_details`: PASSED.

3. **`apps/api/tests/test_investigation_failure_audit.py` & `test_investigation_budgets.py`**:
   - All 39 test cases verifying error logging, deterministic fallback, and budget enforcement: PASSED.

---

## 5. Remaining Verification Gap Before Live Production Retest

- While unit and serialization tests confirm that the serialized JSON payload conforms to Google's OpenAPI 3.0 schema parser, an actual live HTTP response from `generativelanguage.googleapis.com` requires external internet access and an active `GEMINI_API_KEY`.
- Under the standing instructions of this audit, **zero live calls were made**.
- A controlled 1-request live test plan has been prepared in [`MINIMAL_LIVE_RETEST_PLAN.md`](file:///C:/Users/ranja/Sentinel/SENTINEL-/sentinel-antigravity-recovery/MINIMAL_LIVE_RETEST_PLAN.md) for execution by the repository owner.
