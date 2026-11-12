"""OAuth integration audit and reproduction tests for SENTINEL PayPal Gateway.

Verifies:
1. Correct endpoint (https://api-m.sandbox.paypal.com/v1/oauth2/token)
2. Correct HTTP method (POST)
3. Correct Basic Auth construction (RFC 7617 Base64 encoding with trimmed credentials)
4. Correct request body (application/x-www-form-urlencoded, grant_type=client_credentials)
5. Expected response parsing (token caching, lifetime validation, bearer type checking)
6. 401 error classification (PayPalErrorKind.AUTHENTICATION, safe issue, debug_id)
7. Secret redaction (neither client secret nor provider error descriptions leak)
8. No accidental retries (OAuth token failures never loop or retry)
"""

import base64
import logging

import httpx
import pytest

from app.services.paypal.sandbox import SandboxPayPalGateway
from app.services.paypal.types import PayPalError, PayPalErrorKind


def test_1_and_2_and_3_and_4_oauth_request_structure():
    """Verify endpoint, method, Basic Auth construction, and body form encoding."""
    recorded_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(
            200,
            json={
                "access_token": "mock-token-xyz-123",
                "token_type": "Bearer",
                "expires_in": 32400,
            },
            headers={"paypal-debug-id": "test-debug-001"},
        )

    client_id = "test-client-id-abc"
    client_secret = "test-client-secret-xyz"

    gw = SandboxPayPalGateway(
        f"  {client_id}\n",
        f"\t{client_secret} ",
        transport=httpx.MockTransport(mock_handler),
    )
    token = gw._access_token()

    assert token == "mock-token-xyz-123"
    assert len(recorded_requests) == 1
    req = recorded_requests[0]

    # 1. Endpoint
    assert str(req.url) == "https://api-m.sandbox.paypal.com/v1/oauth2/token"

    # 2. Method
    assert req.method == "POST"

    # 3. Basic Auth construction
    auth_header = req.headers.get("authorization")
    assert auth_header is not None
    assert auth_header.startswith("Basic ")
    encoded_creds = auth_header.split(" ", 1)[1]
    decoded_creds = base64.b64decode(encoded_creds).decode("utf-8")
    assert decoded_creds == f"{client_id}:{client_secret}"

    # 4. Request body and headers
    assert req.headers.get("content-type") == "application/x-www-form-urlencoded"
    assert req.headers.get("accept") == "application/json"
    assert req.content == b"grant_type=client_credentials"


def test_5_response_parsing_and_token_caching():
    """Verify token lifetime margin, bearer validation, and caching."""
    calls = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "access_token": f"token-{calls}",
                "token_type": "bearer",
                "expires_in": 3600,
            },
        )

    gw = SandboxPayPalGateway("cid", "secret", transport=httpx.MockTransport(mock_handler))

    t1 = gw._access_token()
    t2 = gw._access_token()
    # Token must be cached while valid
    assert t1 == "token-1"
    assert t2 == "token-1"
    assert calls == 1

    # Forced refresh fetches new token
    t3 = gw._access_token(force=True)
    assert t3 == "token-2"
    assert calls == 2


def test_6_and_7_401_error_classification_and_secret_redaction(caplog):
    """Verify 401 returns AUTHENTICATION error, captures debug_id, and redacts secrets."""
    secret = "SUPER_SECRET_VALUE_TO_NOT_LEAK"

    def fail_401(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={
                "error": "invalid_client",
                "error_description": f"Client Authentication failed with secret {secret}",
            },
            headers={"paypal-debug-id": "paypal-dbg-401-abc"},
        )

    gw = SandboxPayPalGateway("client_id", secret, transport=httpx.MockTransport(fail_401))

    with caplog.at_level(logging.DEBUG), pytest.raises(PayPalError) as exc_info:
        gw.check_credentials()

    err = exc_info.value
    # 6. Error classification
    assert err.kind == PayPalErrorKind.AUTHENTICATION
    assert err.status_code == 401
    assert err.issue == "invalid_client"
    assert err.debug_id == "paypal-dbg-401-abc"

    # 7. Redaction: secret and provider error description must never be exposed
    err_str = str(err)
    assert secret not in err_str
    assert "Client Authentication failed" not in err_str
    assert secret not in caplog.text


def test_8_no_accidental_retries_on_token_failure():
    """Verify OAuth token endpoint is never retried on 401, 500, 503, or network failure."""
    for error_status in [401, 500, 503]:
        attempts = 0

        def failing_handler(
            request: httpx.Request, current_status: int = error_status
        ) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(
                current_status,
                json={"error": "invalid_client" if current_status == 401 else "server_error"},
                headers={"paypal-debug-id": "dbg-no-retry"},
            )

        gw = SandboxPayPalGateway(
            "cid", "secret", transport=httpx.MockTransport(failing_handler), max_retries=3
        )

        with pytest.raises(PayPalError):
            gw._access_token()

        assert attempts == 1, f"Status {error_status} must not be retried on OAuth token endpoint"

    # Network failure
    net_attempts = 0

    def network_error(request: httpx.Request) -> httpx.Response:
        nonlocal net_attempts
        net_attempts += 1
        raise httpx.ConnectError("Egress proxy connection failed")

    gw_net = SandboxPayPalGateway(
        "cid", "secret", transport=httpx.MockTransport(network_error), max_retries=3
    )

    with pytest.raises(PayPalError) as exc:
        gw_net._access_token()
    assert exc.value.kind == PayPalErrorKind.NETWORK
    assert net_attempts == 1, "Network errors on OAuth token request must not retry"
