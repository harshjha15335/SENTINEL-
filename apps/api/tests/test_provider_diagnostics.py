"""Unit tests for safe provider diagnostic extraction and privacy boundary."""

from pydantic_ai.exceptions import ModelHTTPError

from app.services.investigation.diagnostics import extract_safe_diagnostics


def test_extract_safe_diagnostics_known_field():
    body = {
        "error": {
            "code": 400,
            "message": "Sensitive customer message should NOT be in output",
            "status": "INVALID_ARGUMENT",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.BadRequest",
                    "fieldViolations": [
                        {
                            "field": "tools[0].function_declarations[11].parameters",
                            "description": "Private database column name echoed by provider",
                        }
                    ],
                }
            ],
        }
    }
    exc = ModelHTTPError(400, "INVALID_ARGUMENT", body)
    diag = extract_safe_diagnostics(exc, "google")

    assert diag["provider"] == "google"
    assert diag["status_code"] == 400
    assert diag["category"] == "invalid_configuration_value"
    assert diag["rejected_field"] == "parameters"
    # Ensure confidential text is not in diagnostic output
    assert "Sensitive customer message" not in str(diag)
    assert "Private database column" not in str(diag)


def test_extract_safe_diagnostics_unknown_field_refused():
    body = {
        "error": {
            "code": 400,
            "status": "INVALID_ARGUMENT",
            "details": [
                {
                    "fieldViolations": [
                        {
                            "field": "untrusted_arbitrary_attacker_payload",
                            "description": "Exploit attempt",
                        }
                    ]
                }
            ],
        }
    }
    exc = ModelHTTPError(400, "INVALID_ARGUMENT", body)
    diag = extract_safe_diagnostics(exc, "google")

    assert diag["category"] == "invalid_configuration_value"
    # Unknown field must be masked as UNAVAILABLE
    assert diag["rejected_field"] == "UNAVAILABLE"
    assert "untrusted_arbitrary_attacker_payload" not in str(diag)


def test_extract_safe_diagnostics_status_categories():
    for status, expected_cat in [
        (401, "authentication_failed"),
        (403, "permission_denied"),
        (404, "resource_not_found"),
        (429, "quota_or_rate_limit_exceeded"),
        (500, "provider_internal_error"),
        (503, "provider_unavailable"),
        (504, "provider_gateway_timeout"),
    ]:
        exc = ModelHTTPError(status, "Error", {})
        diag = extract_safe_diagnostics(exc, "google")
        assert diag["status_code"] == status
        assert diag["category"] == expected_cat


def test_extract_safe_diagnostics_malformed_error_body():
    exc = ModelHTTPError(400, "Error", "not a dict")
    diag = extract_safe_diagnostics(exc, "google")
    assert diag["status_code"] == 400
    assert diag["rejected_field"] == "UNAVAILABLE"
