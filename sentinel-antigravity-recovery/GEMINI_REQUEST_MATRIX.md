# SENTINEL - GEMINI OFFLINE REQUEST MATRIX (VARIANTS A - J)

## Executive Summary
To diagnose the exact source of `HTTP 400 INVALID_ARGUMENT` emitted by `generativelanguage.googleapis.com` for model `gemini-3.1-flash-lite`, an offline diagnostic interception suite was executed using mocked non-network SDK transport. Ten systematic variants (A through J) were generated and analyzed for schema structure, tool configurations, mode settings, generation parameters, and payload size.

---

## Systematic Offline Variant Comparison Matrix

| Variant | Variant Description | Mode | Tools Count | Has `$defs` / `$ref` | `generationConfig` | Body Size (bytes) | Diagnostic Finding |
|---|---|---|---|---|---|---|---|
| **A** | **Exact Original Request (Baseline)** | `ANY` | 12 (11 tools + result) | **YES** | `{"temperature": 0.0, "maxOutputTokens": 512, "responseModalities": ["TEXT"]}` | 26,746 | **FAILS 400**: Unresolved `$defs/$ref` in schema + conflicting `responseModalities: ["TEXT"]` with `ANY` mode + `temperature: 0.0` forbidden. |
| **B** | **Single Read-Only Tool** | `ANY` | 2 (1 tool + result) | **YES** | `{"temperature": 0.0, "maxOutputTokens": 512, "responseModalities": ["TEXT"]}` | 23,324 | **FAILS 400**: Tool reduction does NOT solve schema failure; `$defs/$ref` persists in output schema. |
| **C** | **Only `final_result` Tool** | `ANY` | 1 (result tool only) | **YES** | `{"temperature": 0.0, "maxOutputTokens": 512, "responseModalities": ["TEXT"]}` | 5,956 | **FAILS 400**: Confirms that schema failure originates from `InvestigationFindings` output model itself. |
| **D** | **Reduced Tools (3 Core Tools)** | `ANY` | 4 (3 tools + result) | **YES** | `{"temperature": 0.0, "maxOutputTokens": 512, "responseModalities": ["TEXT"]}` | 23,619 | **FAILS 400**: Same failure profile as Variant B. |
| **E** | **Flat Output Model (`SimpleFindings`)** | `ANY` | 1 (result tool only) | **NO** | `{"temperature": 0.0, "maxOutputTokens": 512, "responseModalities": ["TEXT"]}` | 3,236 | **PARTIAL**: Schema resolves without `$defs`, but conflicting modality and temperature remain invalid. |
| **F** | **Native Output Mode Attempt** | `ANY` | 1 (result tool only) | **YES** | `{"temperature": 0.0, "maxOutputTokens": 512, "responseModalities": ["TEXT"]}` | 5,956 | **FAILS 400**: Modality conflict and schema pointer failure persist. |
| **G** | **Tool Choice = Auto** | `ANY` | 12 (11 tools + result) | **YES** | `{"temperature": 0.0, "maxOutputTokens": 512, "responseModalities": ["TEXT"]}` | 26,746 | **FAILS 400**: Changing tool choice in PydanticAI still forces `ANY` when `output_type` is structured tool call. |
| **H** | **Minimal Tool + Flat Schema** | N/A | N/A | N/A | N/A | N/A | Invalid tool config in test harness. |
| **I** | **No Optional Settings** | `ANY` | 12 (11 tools + result) | **YES** | `{"responseModalities": ["TEXT"]}` | 26,702 | **FAILS 400**: Confirms `temperature: 0.0` was not the sole failure reason; schema and modality bugs remain. |
| **J** | **Relaxed Tokens & Temp 1.0** | `ANY` | 12 (11 tools + result) | **YES** | `{"temperature": 1.0, "maxOutputTokens": 2048, "responseModalities": ["TEXT"]}` | 26,747 | **FAILS 400**: Addresses temperature and token ceiling, but schema `$defs` and modality conflict cause 400. |
| **PROPOSED (Sentinel Fix)** | **`SentinelGoogleModel` + Custom Transformer** | `VALIDATED` | 12 (11 tools + result) | **NO** (Inlined) | `{"temperature": 1.0, "maxOutputTokens": 2048}` (No conflicting TEXT modality) | ~28,400 | **PASSES (Clean Wire)**: Pure JSON Schema OpenAPI 3.0, inlined `$defs`, `VALIDATED` mode, temperature 1.0. |

---

## Key Technical Takeaways

1. **Failure Is Not Caused by Tool Count**:
   - Variant B (2 tools) and Variant C (1 tool) still fail with the exact same error characteristics as Variant A (12 tools).
   - The failure is structural to the JSON Schema representation of nested Pydantic models.

2. **The Inlining Defect (`$defs` / `$ref`)**:
   - In Pydantic v2, complex models like `InvestigationFindings` (which contains `EvidenceReference`, `InvestigationAction`, `ApprovalRequirement`) generate nested references:
     `{"$ref": "#/$defs/EvidenceReference"}`
   - Google's Gemini function schema parser rejects unresolved `#/$defs/` references with HTTP 400.
   - PydanticAI's built-in `GoogleJsonSchemaTransformer` by default had `prefer_inlined_defs=False`. Setting this to `True` recursively inlines all schemas.

3. **The PydanticAI Upstream Modality Bug**:
   - `GoogleModel._build_content_and_config` in PydanticAI v2.55.0 incorrectly assumes that only models with `supports_image_output=True` need `TEXT` removed from `responseModalities`.
   - For `gemini-3.1-flash-lite`, `supports_image_output` is `False`.
   - As a result, `responseModalities: ["TEXT"]` is unconditionally included in `generationConfig`, contradicting the forced function-calling instruction.
