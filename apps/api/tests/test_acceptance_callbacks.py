import pytest
from pydantic import ValidationError

from app.core.config import Settings, validate_checkout_url


@pytest.mark.parametrize(
    "url",
    [
        "https://",
        "https:///return",
        "https://example.org:99999/return",
        "https://example.org:/return",
        "https://example.org:0/return",
        "https://bad_host/path",
        "https://example.org/\x00return",
        "https://example.org/\vreturn",
        "https://example.org/\x7f",
        "\nhttps://example.org/return",
        "https://example.org/return\n",
        "ftp://example.org/return",
        "https://user@example.org/return",
        "https://:secret@example.org/return",
        "http://example.org/return",
        "https://[invalid]/return",
        "https://-bad.example/return",
        "",
    ],
)
def test_malformed_callback_rejected(url):
    with pytest.raises(ValueError):
        validate_checkout_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/return",
        "https://example.org:443/return?q=1",
        "http://localhost:3000/return",
        "http://127.0.0.1:8040/return",
        "http://[::1]:8040/return",
    ],
)
def test_valid_callback_preserved_without_normalization(url):
    assert validate_checkout_url(url) == url


@pytest.mark.parametrize("url", [None, "http://localhost:8040/return", "https://127.0.0.1/return"])
def test_hosted_sandbox_requires_explicit_public_https_callbacks(url):
    with pytest.raises(ValidationError, match="public HTTPS callback"):
        Settings(
            _env_file=None,
            hosted_deployment=True,
            environment="production",
            cookie_secure=True,
            cors_origins=[],
            storage_backend="database",
            require_workers_ready=True,
            paypal_mode="sandbox",
            paypal_return_url=url,
            paypal_cancel_url=url,
        )


def test_hosted_sandbox_accepts_explicit_public_https_callbacks():
    settings = Settings(
        _env_file=None,
        hosted_deployment=True,
        environment="production",
        cookie_secure=True,
        cors_origins=[],
        storage_backend="database",
        require_workers_ready=True,
        paypal_mode="sandbox",
        paypal_return_url="https://sentinel.example.org/api/v1/paypal/return",
        paypal_cancel_url="https://sentinel.example.org/api/v1/paypal/cancel",
    )
    assert settings.paypal_return_url


@pytest.mark.parametrize("path", ["return", "cancel"])
@pytest.mark.parametrize("token", [None, "FABRICATED", "<script>alert(1)</script>"])
def test_callback_is_unverified_nonmutating_and_secured(app_client, monkeypatch, path, token):
    from app.services.paypal.factory import get_gateway

    # Callback must not ask the provider for approval or mutate state.
    monkeypatch.setattr(
        get_gateway(), "capture_order", lambda *a, **k: pytest.fail("provider call")
    )
    response = app_client.get(
        f"/api/v1/paypal/{path}", params={} if token is None else {"token": token}
    )
    assert response.status_code == 200
    assert "Approval Confirmed" not in response.text
    assert "Approval Cancelled" not in response.text
    assert "APPROVAL RECORDED" not in response.text
    assert "does not" in response.text
    assert "<script>" not in response.text
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "name='viewport'" in response.text


def test_callback_cannot_change_existing_recorded_payment(db, tenant, app_client):
    from sqlalchemy import func, select

    from app.models import AuditEvent, PaymentEvent, Transaction
    from tests.phase4 import make_txn

    txn = make_txn(db, tenant)
    txn.paypal_order_id = "RECORDED-LOCAL-ORDER"
    db.commit()
    models = (Transaction, PaymentEvent, AuditEvent)
    before = [db.scalar(select(func.count()).select_from(m)) for m in models]
    for path in ("return", "cancel"):
        response = app_client.get(f"/api/v1/paypal/{path}", params={"token": txn.paypal_order_id})
        assert response.status_code == 200
        assert "Approval Confirmed" not in response.text
        assert "does not" in response.text
    db.refresh(txn)
    assert txn.status.value == "CAPTURED"
    assert before == [db.scalar(select(func.count()).select_from(m)) for m in models]
