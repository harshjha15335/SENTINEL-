from fastapi.testclient import TestClient

from app.models.enums import Role
from tests.conftest import PASSWORD, Tenant, login


def test_health_and_ready(app_client: TestClient) -> None:
    assert app_client.get("/api/v1/health").json() == {"status": "ok"}
    ready = app_client.get("/api/v1/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["paypal_mode"] == "fixture"
    assert ready.headers["x-correlation-id"]


def test_login_sets_httponly_session_and_me_works(app_client: TestClient, tenant: Tenant) -> None:
    resp = app_client.post(
        "/api/v1/auth/login",
        json={"email": tenant.users[Role.ANALYST].email, "password": PASSWORD},
    )
    assert resp.status_code == 200
    cookies = resp.headers.get_list("set-cookie")
    session_cookie = next(c for c in cookies if c.startswith("sentinel_session="))
    assert "HttpOnly" in session_cookie
    me = app_client.get("/api/v1/me").json()
    assert me["role"] == "ANALYST"
    assert me["merchant"]["name"] == "Acme"


def test_wrong_password_rejected_and_audited(app_client: TestClient, tenant: Tenant, db) -> None:
    resp = app_client.post(
        "/api/v1/auth/login",
        json={"email": tenant.users[Role.ADMIN].email, "password": "nope"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"
    from sqlalchemy import select

    from app.models import AuditEvent

    actions = db.scalars(select(AuditEvent.action)).all()
    assert "auth.login_failed" in actions


def test_unknown_email_gets_same_error(app_client: TestClient) -> None:
    resp = app_client.post(
        "/api/v1/auth/login", json={"email": "ghost@nowhere.example", "password": "x"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["message"] == "Email or password is incorrect"


def test_requires_authentication(app_client: TestClient) -> None:
    assert app_client.get("/api/v1/me").status_code == 401
    assert app_client.get("/api/v1/transactions").status_code == 401


def test_mutation_requires_csrf_token(app_client: TestClient, tenant: Tenant) -> None:
    login(app_client, tenant.users[Role.ADMIN].email)
    resp = app_client.post(
        "/api/v1/paypal/orders",
        json={"product_id": str(tenant.product.id)},
        headers={"Idempotency-Key": "k" * 20},
    )
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["error"]["message"]


def test_logout_revokes_session(app_client: TestClient, tenant: Tenant) -> None:
    csrf = login(app_client, tenant.users[Role.VIEWER].email)
    old = app_client.cookies.get("sentinel_session")
    assert app_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    app_client.cookies.set("sentinel_session", old)
    assert app_client.get("/api/v1/me").status_code == 401


def test_login_rate_limited(app_client: TestClient, tenant: Tenant) -> None:
    email = tenant.users[Role.VIEWER].email
    codes = [
        app_client.post("/api/v1/auth/login", json={"email": email, "password": "bad"}).status_code
        for _ in range(7)
    ]
    assert codes[:5] == [401] * 5
    assert codes[5:] == [429, 429]


def test_audit_is_admin_only(app_client: TestClient, tenant: Tenant) -> None:
    login(app_client, tenant.users[Role.ANALYST].email)
    assert app_client.get("/api/v1/audit").status_code == 403
    login(app_client, tenant.users[Role.ADMIN].email)
    resp = app_client.get("/api/v1/audit")
    assert resp.status_code == 200
    assert any(i["action"] == "auth.login" for i in resp.json()["items"])
