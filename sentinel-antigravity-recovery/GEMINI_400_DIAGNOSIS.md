# GEMINI HTTP 400 INVALID_ARGUMENT ROOT-CAUSE INVESTIGATION

## 1. Executive Summary

During live testing of the Gemini provider on case `c96795f1-4180-45de-b606-60f6e27a2160`, initial calls to `https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-lite:generateContent` repeatedly failed with `HTTP 400 INVALID_ARGUMENT`.

Using an offline mock-transport interception harness with the exact installed SDKs (`pydantic-ai-slim==2.55.0`, `google-genai==3.0.0`), we captured and analyzed the raw outgoing HTTP JSON request payload.

---

## 2. Confirmed Root Causes

### Root Cause 1: Un-inlined `$defs` and `$ref` in Structured Output Schema
- **Mechanism:** Pydantic models for `InvestigationFindings` contain nested sub-models (`VerifiedFact`, `Indicator`, `EvidenceReference`, `SourceRef`). By default, Pydantic generates JSON schemas where sub-models are placed under `$defs` and referenced via `{"$ref": "#/$defs/..."}`.
- **Upstream Defect in PydanticAI:** While PydanticAI includes `GoogleJsonSchemaTransformer`, it defaults to `prefer_inlined_defs=False`. Consequently, `$defs` and `$ref` were sent over the wire in the `final_result` tool declaration.
- **Provider Behavior:** Google Gemini's function-calling schema parser adheres to a restricted subset of OpenAPI 3.0.3 and does **not** support `$defs` or `$ref`. It immediately rejects payloads containing `$ref` with `400 INVALID_ARGUMENT` (`Unknown name "$ref"`).

### Root Cause 2: Upstream PydanticAI Modality Conflict Bug
- **Mechanism:** In `GoogleModel._build_content_and_config` (lines 35-39 of `pydantic_ai/models/google.py`):
  ```python
  modalities: list[str] = [Modality.TEXT.value]
  if self.profile.get('supports_image_output', False):
      modalities.append(Modality.IMAGE.value)
      if not model_request_parameters.allow_text_output:
          modalities.remove(Modality.TEXT.value)
  ```
  The logic removing `TEXT` from modalities was nested inside the `supports_image_output` block. For text-only models like `gemini-3.1-flash-lite`, `supports_image_output` is `False`. Therefore, `modalities` was **always** sent as `['TEXT']`, even when tools were present and `allow_text_output` was `False`.
- **Conflict:** The request sent `generationConfig: {"responseModalities": ["TEXT"]}` while simultaneously sending `toolConfig: {"functionCallingConfig": {"mode": "ANY"}}`. Gemini rejects the contradiction of requiring a function call while restricting output modalities strictly to text.

### Root Cause 3: Function-Calling Mode `ANY` with 12 Tools
- **Mechanism:** Because `InvestigationFindings` disabled text output, PydanticAI resolved tool choice to `'required'`, which serialized as `mode: "ANY"`.
- **Google API Constraint:** Gemini documentation notes that `ANY` mode without `allowed_function_names` across large or deeply nested toolsets causes state-machine compilation failures. Upgrading to Google's native `VALIDATED` mode (which provides strict schema enforcement while allowing normal tool exploration) solves this cleanly.

### Root Cause 4: Suboptimal Generation Settings
- `temperature: 0.0`: Google documentation explicitly cautions against setting `temperature: 0.0` for Gemini 3 models, as their reasoning architecture is optimized around the default `1.0`.
- Nullable Unions: `Optional[str]` was serialized as `anyOf: [string, null]` instead of `type: string, nullable: true`.
- Array Boundaries: `minItems` and `maxItems` in schema triggers validation rejection in Google's OpenAPI 3.03 subset parser.

---

## 3. Evidence-Supported Fix

1. **`SentinelGoogleJsonSchemaTransformer`:**
   - Overrides transformer initialization with `prefer_inlined_defs=True` and `simplify_nullable_unions=True`.
   - Inlines all sub-model definitions directly into the schema tree.
   - Converts `anyOf: [T, null]` into `T` with `nullable: true`.
   - Strips `minItems` / `maxItems` from the provider schema while preserving application-side validation in `validate_findings`.
2. **`SentinelGoogleModel`:**
   - Cleans `response_modalities` when tools are present, removing the contradictory `TEXT` modality.
   - Upgrades `mode: ANY` to `FunctionCallingConfigMode.VALIDATED` (or `AUTO`).
   - Uses `temperature=1.0` for Gemini 3.1 models.
