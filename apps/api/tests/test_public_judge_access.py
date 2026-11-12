"""Regression: public judge login must never create a privileged or real-data session."""
from types import SimpleNamespace

from app.api.v1 import auth
from app.models import Merchant, User
from app.models.enums import MerchantEnvironment, Role
from app.auth.passwords import hash_password
from app.services.demo.judge import JUDGE_EMAIL, MERCHANT, prepare


def _enable(monkeypatch):
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(public_demo_login_enabled=True, session_ttl_minutes=60),
    )
    auth._demo_limiter.clear()


def test_guest_login_disabled_by_default(app_client):
    r = app_client.post(
        "/api/v1/auth/demo",
        headers={"Origin": "https://sentinel-v2-staging.onrender.com"},
    )
    assert r.status_code == 404
    assert "sentinel_session" not in r.cookies


def test_guest_login_rejects_wrong_origin_and_unprepared_tenant(app_client, monkeypatch):
    _enable(monkeypatch)
    wrong = app_client.post(
        "/api/v1/auth/demo",
        headers={"Origin": "https://attacker.example"},
    )
    assert wrong.status_code == 403
    absent = app_client.post(
        "/api/v1/auth/demo",
        headers={"Origin": "https://sentinel-v2-staging.onrender.com"},
    )
    assert absent.status_code == 404


def test_guest_login_is_tenant_isolated_and_read_only(app_client, db, monkeypatch, tenant):
    _enable(monkeypatch)
    prepared = prepare(db, password="synthetic-demo-test-password", fresh=False)
    result = app_client.post(
        "/api/v1/auth/demo",
        headers={"Origin": "https://sentinel-v2-staging.onrender.com"},
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["user"]["role"] == "VIEWER"
    assert body["user"]["merchant"]["environment"] == "DEMO"
    assert body["user"]["email"] == JUDGE_EMAIL
    assert "HttpOnly" in result.headers["set-cookie"]
    assert "Secure" in result.headers["set-cookie"]
    assert "no-store" == result.headers.get("cache-control")
    assert app_client.get("/api/v1/demo/scenario").status_code == 200
    assert app_client.get(f"/api/v1/cases/{prepared['case_id']}").status_code == 200
    # Unrelated merchant's records are not visible.
    other = app_client.get(f"/api/v1/transactions/{tenant.product.id}")
    assert other.status_code in (404, 422)
    # A valid CSRF header still cannot grant VIEWER operator privileges.
    blocked = app_client.post(
        f"/api/v1/cases/{prepared['case_id']}/investigations",
        headers={"X-CSRF-Token": body["csrf_token"]},
        json={"mode": "auto"},
    )
    assert blocked.status_code == 403
    # A guest session must not be silently replaced by another guest session.
    replacement = app_client.post(
        "/api/v1/auth/demo",
        headers={"Origin": "https://sentinel-v2-staging.onrender.com"},
    )
    assert replacement.status_code == 409
    assert app_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": body["csrf_token"]},
    ).status_code == 204


def test_public_demo_does_not_use_untrusted_merchant(app_client, db, monkeypatch):
    _enable(monkeypatch)
    merchant = Merchant(name=MERCHANT, environment=MerchantEnvironment.SANDBOX)
    db.add(merchant)
    db.flush()
    db.add(
        User(
            merchant_id=merchant.id,
            email=JUDGE_EMAIL,
            password_hash=hash_password("not-used"),
            role=Role.VIEWER,
        )
    )
    db.commit()
    r = app_client.post(
        "/api/v1/auth/demo",
        headers={"Origin": "https://sentinel-v2-staging.onrender.com"},
    )
    assert r.status_code == 404
