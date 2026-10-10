import json

import pytest
from fastapi.testclient import TestClient

from app.models.enums import DataOrigin, Role
from app.services.paypal.sandbox import SandboxPayPalGateway
from app.services.paypal.types import (
    CreateOrderInput,
    LineItem,
    Money,
    PayPalError,
    PayPalErrorKind,
)
from tests.conftest import Tenant, login
from tests.paypal_mock import FakePayPal


def _gateway(fake: FakePayPal) -> SandboxPayPalGateway:
    return SandboxPayPalGateway("cid", "secret", transport=fake.transport())


def _order(request_id: str = "req-1") -> CreateOrderInput:
    return CreateOrderInput(
        reference_id="ref-1",
        request_id=request_id,
        items=[LineItem("Widget", "SKU-1", 3, Money(1999, "USD"))],
    )


def test_money_conversion_round_trips() -> None:
    assert Money(1999, "USD").to_paypal_value() == "19.99"
    assert Money(5, "USD").to_paypal_value() == "0.05"
    assert Money(1200, "JPY").to_paypal_value() == "1200"
    assert Money.from_paypal("19.9", "USD") == Money(1990, "USD")
    assert Money.from_paypal("1200", "JPY") == Money(1200, "JPY")


def test_create_order_sends_server_amount_and_idempotency_header() -> None:
    fake = FakePayPal()
    result = _gateway(fake).create_order(_order())
    req = fake.calls[-1]
    body = json.loads(req.content)
    assert req.headers["paypal-request-id"] == "req-1"
    assert body["intent"] == "CAPTURE"
    assert body["purchase_units"][0]["amount"]["value"] == "59.97"
    assert body["purchase_units"][0]["items"][0]["quantity"] == "3"
    assert result.status == "PAYER_ACTION_REQUIRED"
    assert result.approve_url and "checkoutnow" in result.approve_url


def test_token_is_cached_and_refreshed_on_401() -> None:
    fake = FakePayPal()
    gw = _gateway(fake)
    gw.create_order(_order("a"))
    gw.create_order(_order("b"))
    assert fake.token_calls == 1
    fake.fail_next = [401]
    gw.create_order(_order("c"))
    assert fake.token_calls == 2


def test_errors_are_classified_without_secrets() -> None:
    fake = FakePayPal(fail_next=[422])
    with pytest.raises(PayPalError) as exc:
        _gateway(fake).create_order(_order())
    assert exc.value.kind is PayPalErrorKind.UNPROCESSABLE
    assert exc.value.issue == "ISSUE_422"
    assert exc.value.debug_id == "dbg123"
    assert "secret" not in str(exc.value)


def test_transient_errors_retry_only_with_request_id() -> None:
    fake = FakePayPal(fail_next=[503])
    result = _gateway(fake).create_order(_order())
    assert result.order_id
    fake = FakePayPal(fail_next=[503])
    with pytest.raises(PayPalError) as exc:
        _gateway(fake).get_order("5O000000000000001")  # GET has no request id: no retry
    assert exc.value.kind is PayPalErrorKind.PROVIDER_ERROR


def test_rejects_unsafe_resource_ids() -> None:
    with pytest.raises(PayPalError):
        _gateway(FakePayPal()).get_order("../v1/oauth2/token")


def test_dispute_permission_failure_is_reported() -> None:
    with pytest.raises(PayPalError) as exc:
        _gateway(FakePayPal()).list_disputes()
    assert exc.value.kind is PayPalErrorKind.PERMISSION


@pytest.fixture
def sandbox_client(app_client: TestClient):
    from app.api.deps import paypal_gateway
    from app.main import app

    fake = FakePayPal()
    gw = _gateway(fake)
    app.dependency_overrides[paypal_gateway] = lambda: gw
    return app_client, fake


def test_api_flow_against_mocked_sandbox(sandbox_client, tenant: Tenant) -> None:
    client, fake = sandbox_client
    csrf = login(client, tenant.users[Role.ANALYST].email)
    order = client.post(
        "/api/v1/paypal/orders",
        json={"product_id": str(tenant.product.id), "quantity": 2},
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "sandbox-key-000000001"},
    ).json()
    assert order["data_origin"] == DataOrigin.LIVE_SANDBOX.value
    sent = json.loads(fake.calls[-1].content)
    assert sent["purchase_units"][0]["amount"]["value"] == "50.00"

    txn = client.post(
        f"/api/v1/paypal/orders/{order['paypal_order_id']}/capture",
        headers={"X-CSRF-Token": csrf},
    ).json()
    assert txn["status"] == "CAPTURED"
    assert txn["payer_reference"] == "QYR5Z8XDVJNXQ"
    capture_req = fake.calls[-1]
    assert capture_req.headers["paypal-request-id"] == f"sentinel-capture-{txn['id']}"
    detail = client.get(f"/api/v1/transactions/{txn['id']}").json()
    # Buyer email from the PayPal response is not persisted.
    assert "buyer@example.com" not in json.dumps(detail)


def test_amount_mismatch_is_not_marked_captured(sandbox_client, tenant: Tenant) -> None:
    client, fake = sandbox_client
    fake.capture_amount_override = "1.00"
    csrf = login(client, tenant.users[Role.ADMIN].email)
    order = client.post(
        "/api/v1/paypal/orders",
        json={"product_id": str(tenant.product.id)},
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "sandbox-key-000000002"},
    ).json()
    txn = client.post(
        f"/api/v1/paypal/orders/{order['paypal_order_id']}/capture",
        headers={"X-CSRF-Token": csrf},
    ).json()
    assert txn["status"] == "CAPTURE_FAILED"
    assert "differs" in txn["failure_reason"]


def test_provider_failure_records_state(sandbox_client, tenant: Tenant) -> None:
    client, fake = sandbox_client
    csrf = login(client, tenant.users[Role.ADMIN].email)
    order = client.post(
        "/api/v1/paypal/orders",
        json={"product_id": str(tenant.product.id)},
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "sandbox-key-000000003"},
    ).json()
    fake.fail_next = [422]
    resp = client.post(
        f"/api/v1/paypal/orders/{order['paypal_order_id']}/capture",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 502
    assert resp.json()["error"]["details"]["kind"] == "UNPROCESSABLE"
    detail = client.get(f"/api/v1/transactions/{order['transaction_id']}").json()
    assert detail["status"] == "CAPTURE_FAILED"
