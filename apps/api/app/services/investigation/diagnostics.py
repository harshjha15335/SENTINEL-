"""Safe, allowlisted diagnostic extraction for provider errors.

Security Boundary:
Provider error bodies and HTTP exceptions may contain echoed user prompts,
internal database values, or credential artifacts.
This module strictly extracts only predefined numeric codes, fixed enum categories,
and recognized field paths, refusing all arbitrary error prose or unstructured values.
"""

from typing import Any

from pydantic_ai.exceptions import ModelHTTPError

# Recognized schema or request field paths that Gemini or providers report
RECOGNIZED_FIELD_PATHS = frozenset(
    {
        "contents",
        "system_instruction",
        "systemInstruction",
        "tools",
        "tool_config",
        "toolConfig",
        "function_declarations",
        "functionDeclarations",
        "parameters",
        "parameters_json_schema",
        "parametersJsonSchema",
        "generation_config",
        "generationConfig",
        "max_output_tokens",
        "maxOutputTokens",
        "temperature",
        "response_modalities",
        "responseModalities",
        "response_mime_type",
        "responseMimeType",
        "thinking_config",
        "thinkingConfig",
    }
)

# Fixed diagnostic categories
DIAGNOSTIC_CATEGORIES = {
    400: "invalid_configuration_value",
    401: "authentication_failed",
    403: "permission_denied",
    404: "resource_not_found",
    429: "quota_or_rate_limit_exceeded",
    500: "provider_internal_error",
    503: "provider_unavailable",
    504: "provider_gateway_timeout",
}


def extract_safe_diagnostics(exc: Exception, provider_name: str) -> dict[str, Any]:
    """Safely extract provider error metadata without persisting untrusted provider prose."""
    status_code: int | None = None
    if isinstance(exc, ModelHTTPError):
        status_code = exc.status_code

    if status_code:
        category = DIAGNOSTIC_CATEGORIES.get(status_code, "unknown_provider_error")
    else:
        category = "network_or_transport_error"

    rejected_field = "UNAVAILABLE"
    # Attempt to extract recognized field paths from structured payload details only
    if isinstance(exc, ModelHTTPError) and isinstance(exc.body, dict):
        rejected_field = _find_recognized_field(exc.body)

    return {
        "provider": provider_name,
        "status_code": status_code,
        "category": category,
        "rejected_field": rejected_field,
    }


def _find_recognized_field(body: dict[str, Any]) -> str:
    """Scan error details for allowlisted field paths only. Return 'UNAVAILABLE' if not matched."""
    # Check Google error details format: {"error": {"details": [{"field": "..."}, ...]}}
    error_val = body.get("error") if isinstance(body, dict) else None
    error_obj = error_val if isinstance(error_val, dict) else body
    if isinstance(error_obj, dict):
        details = error_obj.get("details")
        if isinstance(details, list):
            for item in details:
                if isinstance(item, dict):
                    # Google field_violations
                    field_violations = item.get("fieldViolations") or item.get("field_violations")
                    if isinstance(field_violations, list):
                        for v in field_violations:
                            if isinstance(v, dict) and "field" in v:
                                f = str(v["field"]).split(".")[-1]
                                if f in RECOGNIZED_FIELD_PATHS:
                                    return f
                    # Google ErrorInfo metadata
                    metadata = item.get("metadata")
                    if isinstance(metadata, dict):
                        for k, val in metadata.items():
                            if str(val) in RECOGNIZED_FIELD_PATHS:
                                return str(val)
                            if str(k) in RECOGNIZED_FIELD_PATHS:
                                return str(k)

    return "UNAVAILABLE"
