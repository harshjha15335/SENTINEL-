import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import Role
from tests.conftest import Tenant, login


def _create(client: TestClient, csrf: str, product_id: uuid.UUID, key: str, **extra):
    return client.post(
        "/api/v1/paypal/orders",
        json={"product_id": str(product_id), **extra},
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
    )


def test_fixture_order_create_and_capture(app_client: TestClient, tenant: Tenant) -> None:
    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    resp = _create(app_client, csrf, tenant.product.id, "order-key-0000000001", quantity=2)
    assert resp.status_code == 201, resp.text
    order = resp.json()
    assert order["paypal_order_id"].startswith("SIM-ORDER-")
    assert order["data_origin"] == "SIMULATED"

    cap = app_client.post(
        f"/api/v1/paypal/orders/{order['paypal_order_id']}/capture",
        headers={"X-CSRF-Token": csrf},
    )
    assert cap.status_code == 200, cap.text
    txn = cap.json()
    assert txn["status"] == "CAPTURED"
    assert txn["amount_minor"] == 5000  # server price x quantity
    assert txn["paypal_capture_id"].startswith("SIM-CAPTURE-")

    detail = app_client.get(f"/api/v1/transactions/{txn['id']}").json()
    assert [a["action"] for a in detail["audit"]] == [
        "paypal.order.created",
        "paypal.order.captured",
        "risk.assessment.created",
    ]
    assert detail["risk_band"] in ("LOW", "MEDIUM", "HIGH")
    listing = app_client.get("/api/v1/transactions").json()
    assert listing["total"] == 1


def test_client_cannot_supply_amount(app_client: TestClient, tenant: Tenant) -> None:
    csrf = login(app_client, tenant.users[Role.ADMIN].email)
    resp = _create(app_client, csrf, tenant.product.id, "order-key-0000000002", amount_minor=1)
    assert resp.status_code == 422


def test_create_is_idempotent(app_client: TestClient, tenant: Tenant) -> None:
    csrf = login(app_client, tenant.users[Role.ADMIN].email)
    a = _create(app_client, csrf, tenant.product.id, "order-key-0000000003").json()
    b = _create(app_client, csrf, tenant.product.id, "order-key-0000000003").json()
    assert a["transaction_id"] == b["transaction_id"]
    clash = _create(app_client, csrf, tenant.product.id, "order-key-0000000003", quantity=3)
    assert clash.status_code == 409


def test_capture_twice_is_safe(app_client: TestClient, tenant: Tenant) -> None:
    csrf = login(app_client, tenant.users[Role.ADMIN].email)
    oid = _create(app_client, csrf, tenant.product.id, "order-key-0000000004").json()[
        "paypal_order_id"
    ]
    first = app_client.post(f"/api/v1/paypal/orders/{oid}/capture", headers={"X-CSRF-Token": csrf})
    second = app_client.post(f"/api/v1/paypal/orders/{oid}/capture", headers={"X-CSRF-Token": csrf})
    assert first.json()["paypal_capture_id"] == second.json()["paypal_capture_id"]
    detail = app_client.get(f"/api/v1/transactions/{first.json()['id']}").json()
    assert [a["action"] for a in detail["audit"]].count("paypal.order.captured") == 1


def test_viewer_cannot_create_orders(app_client: TestClient, tenant: Tenant) -> None:
    csrf = login(app_client, tenant.users[Role.VIEWER].email)
    resp = _create(app_client, csrf, tenant.product.id, "order-key-0000000005")
    assert resp.status_code == 403


def test_merchant_isolation(app_client: TestClient, tenant: Tenant, other_tenant: Tenant) -> None:
    csrf = login(app_client, tenant.users[Role.ADMIN].email)
    order = _create(app_client, csrf, tenant.product.id, "order-key-0000000006").json()
    # Another merchant's product is invisible.
    assert (
        _create(app_client, csrf, other_tenant.product.id, "order-key-0000000007").status_code
        == 404
    )

    csrf2 = login(app_client, other_tenant.users[Role.ADMIN].email)
    assert app_client.get(f"/api/v1/transactions/{order['transaction_id']}").status_code == 404
    assert app_client.get("/api/v1/transactions").json()["total"] == 0
    cap = app_client.post(
        f"/api/v1/paypal/orders/{order['paypal_order_id']}/capture",
        headers={"X-CSRF-Token": csrf2},
    )
    assert cap.status_code == 404


def test_bad_idempotency_key_rejected(app_client: TestClient, tenant: Tenant) -> None:
    csrf = login(app_client, tenant.users[Role.ADMIN].email)
    assert _create(app_client, csrf, tenant.product.id, "short").status_code == 400


def test_sandbox_without_credentials_reports_dependency(
    app_client: TestClient, tenant: Tenant, monkeypatch
) -> None:
    from app.core.config import PayPalMode, get_settings
    from app.services.paypal.factory import get_gateway

    monkeypatch.setattr(get_settings(), "paypal_mode", PayPalMode.SANDBOX)
    get_gateway.cache_clear()
    try:
        csrf = login(app_client, tenant.users[Role.ADMIN].email)
        resp = _create(app_client, csrf, tenant.product.id, "order-key-0000000008")
        assert resp.status_code == 503
        assert resp.json()["error"]["details"]["credential_dependency"] is True
        status = app_client.get("/api/v1/paypal/status").json()
        assert status["mode"] == "sandbox"
        assert status["credentials_configured"] is False
        assert status["token_check"] == "not_attempted"
    finally:
        get_gateway.cache_clear()


def test_checkout_stage1_principal_construction_and_capture_offline(
    db: Session, tenant: Tenant
) -> None:
    from app.auth.deps import Principal
    from app.models import UserSession
    from app.services import checkout
    from app.services.paypal.fixture import FixturePayPalGateway

    user = tenant.users[Role.ADMIN]
    session = UserSession(user_id=user.id, token_digest="cli_test", csrf_digest="cli_test")
    principal = Principal(user=user, session=session)

    # Invariants: tenant isolation and role preservation
    assert principal.merchant_id == tenant.merchant.id
    assert principal.role == Role.ADMIN
    assert principal.user.id == user.id

    gateway = FixturePayPalGateway()
    txn = checkout.create_order(
        db,
        gateway,
        principal,
        product_id=tenant.product.id,
        quantity=1,
        idempotency_key=f"offline-test-{uuid.uuid4()}",
    )
    assert txn.id is not None
    assert txn.paypal_order_id is not None
    assert txn.amount_minor == 2500

    captured = checkout.capture_order(
        db,
        gateway,
        principal,
        paypal_order_id=txn.paypal_order_id,
    )
    assert captured.paypal_capture_id is not None
    assert captured.status.value == "CAPTURED"


def test_checkout_return_and_cancel_endpoints(app_client: TestClient) -> None:
    # Test GET /api/v1/paypal/return with token and PayerID
    resp = app_client.get(
        "/api/v1/paypal/return",
        params={"token": "TEST-TOKEN-123", "PayerID": "TEST-PAYER-456"},
    )
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "TEST-TOKEN-123" in resp.text
    assert "TEST-PAYER-456" in resp.text
    assert "SANDBOX APPROVAL RECORDED" in resp.text

    # Test GET /api/v1/paypal/cancel with token
    cancel_resp = app_client.get(
        "/api/v1/paypal/cancel",
        params={"token": "TEST-CANCEL-789"},
    )
    assert cancel_resp.status_code == 200
    assert "text/html" in cancel_resp.headers["content-type"]
    assert "TEST-CANCEL-789" in cancel_resp.text
    assert "SANDBOX APPROVAL CANCELLED" in cancel_resp.text

    # Verify query parameter HTML escaping protects against injection
    xss_resp = app_client.get(
        "/api/v1/paypal/return",
        params={"token": "<script>alert(1)</script>", "PayerID": "safe"},
    )
    assert xss_resp.status_code == 200
    assert "<script>alert(1)</script>" not in xss_resp.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in xss_resp.text
