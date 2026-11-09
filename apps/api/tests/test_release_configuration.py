from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.auth.passwords import verify_password
from app.cli import seed
from app.core.config import Settings
from app.models import User, UserSession


def test_paypal_environment_padding_normalized_at_startup():
    settings = Settings(_env_file=None, paypal_client_id=" cid\n", paypal_client_secret=" secret\t")
    assert settings.paypal_client_id == "cid"
    assert settings.paypal_client_secret.get_secret_value() == "secret"


@pytest.mark.parametrize(
    "client_id,secret", [(" ", "secret"), ("cid", "\n"), ("ci d", "secret"), ("cid", "sec\nret")]
)
def test_paypal_invalid_environment_shape_rejected_at_startup(client_id, secret):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, paypal_client_id=client_id, paypal_client_secret=secret)


def test_bootstrap_preserves_existing_passwords_and_explicit_rotation_revokes_sessions(
    db, monkeypatch
):
    monkeypatch.setenv("SENTINEL_SEED_ADMIN_PASSWORD", "initial private test password")
    monkeypatch.delenv("SENTINEL_SEED_ANALYST_PASSWORD", raising=False)
    monkeypatch.delenv("SENTINEL_SEED_VIEWER_PASSWORD", raising=False)
    seed()
    user = db.scalar(select(User).where(User.email == "admin@northwind.example"))
    initial_hash = user.password_hash
    db.add(
        UserSession(
            user_id=user.id,
            token_digest="1" * 64,
            csrf_digest="2" * 64,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    db.commit()
    monkeypatch.setenv("SENTINEL_SEED_ADMIN_PASSWORD", "replacement private test password")
    seed()
    db.refresh(user)
    assert user.password_hash == initial_hash
    assert db.scalar(select(UserSession).where(UserSession.user_id == user.id)) is not None
    seed(rotate_passwords=True)
    db.refresh(user)
    assert verify_password(user.password_hash, "replacement private test password")
    assert not verify_password(user.password_hash, "initial private test password")
    assert db.scalar(select(UserSession).where(UserSession.user_id == user.id)) is None


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://sentinel:sentinel@127.0.0.1:5432/sentinel",
        "postgresql+psycopg://sentinel:sentinel@db.example:5432/sentinel_test",
        "postgresql+psycopg://sentinel:sentinel@localhost/sentinel_test_2026",
    ],
)
def test_destructive_suite_rejects_non_disposable_database(url):
    from tests.conftest import require_disposable_database

    with pytest.raises(RuntimeError, match="loopback database ending in _test"):
        require_disposable_database(url)
