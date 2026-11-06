"""Credential-free classification of outbound failures without exception-body logging."""

from urllib.parse import urlparse

import httpx


def failure_diagnostic(exc: Exception, destination: str, purpose: str) -> dict[str, object]:
    result: dict[str, object] = {
        "host": urlparse(destination).hostname or "invalid",
        "purpose": purpose,
        "category": type(exc).__name__,
        "tls_verification": "enabled",
        "upstream_reached": "unknown",
    }
    if isinstance(exc, httpx.ProxyError):
        result.update(stage="proxy_connect", upstream_reached=False)
        if "403" in str(exc):
            result["proxy_status"] = 403
    elif isinstance(exc, httpx.HTTPStatusError):
        result.update(
            stage="upstream_http", upstream_reached=True, http_status=exc.response.status_code
        )
    elif isinstance(exc, httpx.TimeoutException):
        result["stage"] = "timeout"
    else:
        result["stage"] = "transport_or_application"
    return result
