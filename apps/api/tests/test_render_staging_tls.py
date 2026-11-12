"""Approved synthetic-only Render TLS exception; no real database/provider endpoints."""

import socket
import struct
import threading
from pathlib import Path

import pytest
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from alembic import command
from app.core.config import Settings
from app.db import session

HOST = "dpg-offline-reviewed-staging-a"
URL = f"postgresql+psycopg://sentinel_staging:OFFLINE_TEST_ONLY@{HOST}/sentinel_staging"
BASE = dict(
    hosted_deployment=True,
    environment="production",
    deployment_stage="staging",
    render_project_id="prj-dbq48lon74is739m7nl0",
    render_workspace_id="tea-d8gorhflk1mc73f4pmr0",
    cookie_secure=True,
    storage_backend="database",
    require_workers_ready=True,
    cors_origins=[],
    paypal_mode="fixture",
    ai_provider="none",
    ai_api_key=None,
    paypal_client_id=None,
    paypal_client_secret=None,
    paypal_webhook_id=None,
    supabase_url=None,
    supabase_service_role_key=None,
    database_tls_policy="render_internal_staging",
    render_internal_tls_reviewed_host=HOST,
    database_url=URL,
    database_ssl_root_cert=None,
)


def settings(**changes):
    return Settings(_env_file=None, **(BASE | changes))


def test_approved_scope_pins_identity_and_requires_tls():
    args = session.database_connect_args(settings())
    assert args == {
        "sslmode": "require",
        "gssencmode": "disable",
        "host": HOST,
        "port": "5432",
        "dbname": "sentinel_staging",
        "user": "sentinel_staging",
        "password": "OFFLINE_TEST_ONLY",
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"hosted_deployment": False},
        {"deployment_stage": "production"},
        {"deployment_stage": None},
        {"environment": "development"},
        {"render_project_id": "prj-other"},
        {"render_project_id": None},
        {"render_workspace_id": "tea-other"},
        {"render_workspace_id": None},
        {
            "paypal_mode": "sandbox",
            "paypal_return_url": "https://example.com/return",
            "paypal_cancel_url": "https://example.com/cancel",
        },
        {"ai_provider": "google"},
        {"refund_execution_enabled": True},
        {"allow_webhook_fixtures": True},
        {"cookie_secure": False},
        {"require_workers_ready": False},
        {"storage_backend": "local"},
        {"database_ssl_root_cert": "/nonexistent/offline-ca.pem"},
        {"render_internal_tls_reviewed_host": "dpg-other"},
    ],
)
def test_exception_rejects_incompatible_profiles(changes):
    with pytest.raises(ValidationError):
        settings(**changes)


def test_saved_provider_credentials_remain_dormant_in_render_fixture_staging():
    """Provisioning secret pairs must never start PayPal/Gemini/bridge traffic."""
    config = settings(
        paypal_client_id="OFFLINE_CLIENT",
        paypal_client_secret="OFFLINE_SECRET",
        paypal_webhook_id="OFFLINE_WEBHOOK",
        paypal_return_url="https://sentinel-v2-staging.onrender.com/api/v1/paypal/return",
        paypal_cancel_url="https://sentinel-v2-staging.onrender.com/api/v1/paypal/cancel",
        ai_api_key="OFFLINE_AI_KEY",
        ai_model="gemini-3.1-flash-lite",
        supabase_url="https://offline.supabase.co",
        supabase_service_role_key="OFFLINE_ROLE",
    )
    # Existing exact URL/host/TLS protections are unchanged.
    assert session.database_connect_args(config)["sslmode"] == "require"
    assert config.paypal_mode.value == "fixture"
    assert config.ai_provider.value == "none"
    assert config.paypal_credentials_configured
    assert config.supabase_configured
    assert not config.bridge_required
    assert config.worker_configuration_ready


@pytest.mark.parametrize(
    "override",
    [
        {
            "paypal_mode": "sandbox",
            "paypal_return_url": "https://sentinel-v2-staging.onrender.com/api/v1/paypal/return",
            "paypal_cancel_url": "https://sentinel-v2-staging.onrender.com/api/v1/paypal/cancel",
        },
        {"ai_provider": "google", "ai_api_key": "OFFLINE_AI_KEY"},
        {
            "paypal_mode": "sandbox",
            "paypal_client_id": "OFFLINE_CLIENT",
            "paypal_client_secret": "OFFLINE_SECRET",
            "paypal_return_url": "https://sentinel-v2-staging.onrender.com/api/v1/paypal/return",
            "paypal_cancel_url": "https://sentinel-v2-staging.onrender.com/api/v1/paypal/cancel",
            "supabase_url": "https://offline.supabase.co",
            "supabase_service_role_key": "OFFLINE_ROLE",
        },
    ],
)
def test_saved_credentials_do_not_authorize_integrated_mode(override):
    with pytest.raises(ValidationError, match="Unapproved Render"):
        settings(**override)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://sentinel_staging:OFFLINE_TEST_ONLY@attacker.example/sentinel_staging",
        URL.replace(HOST, HOST + ".singapore-postgres.render.com"),
        URL.replace(HOST, "127.0.0.1"),
        URL.replace(HOST, HOST + ",dpg-other"),
        URL.replace(HOST, HOST + ":5433"),
        URL.rsplit("/", 1)[0] + "/other",
        URL.replace("sentinel_staging:", "other:"),
        URL.replace(":OFFLINE_TEST_ONLY", ""),
        URL + "?sslmode=disable",
        URL + "?sslmode=prefer",
        URL + "?sslmode=verify-full",
        URL + "?hostaddr=127.0.0.1",
        URL + "?host=dpg-other",
        URL + "?service=other",
        URL + "?sslrootcert=/tmp/unused",
        URL + "?options=-csearch_path=other",
        "",
    ],
)
def test_exception_rejects_unreviewed_or_redirected_destinations(url):
    with pytest.raises(ValidationError):
        settings(database_url=url)


@pytest.mark.parametrize(
    "name",
    [
        "PGHOST",
        "PGHOSTADDR",
        "PGPORT",
        "PGDATABASE",
        "PGUSER",
        "PGPASSWORD",
        "PGPASSFILE",
        "PGSERVICE",
        "PGSERVICEFILE",
        "PGSSLMODE",
        "PGSSLROOTCERT",
        "PGSSLCERT",
        "PGSSLKEY",
        "PGSSLCRL",
        "PGSSLCRLDIR",
        "PGGSSENCMODE",
        "PGTARGETSESSIONATTRS",
        "PGOPTIONS",
    ],
)
def test_ambient_libpq_overrides_fail_before_connection(monkeypatch, name):
    monkeypatch.setenv(name, "OFFLINE_OVERRIDE")
    with pytest.raises(ValidationError, match="Unapproved Render"):
        settings()


def test_effective_migration_url_is_checked_not_only_settings():
    config = settings()
    with pytest.raises(ValueError, match="Unapproved Render"):
        session.database_connect_args(config, database_url=URL.replace(HOST, "attacker.example"))
    with pytest.raises(ValueError):
        session.database_connect_args(config, database_url="")


def test_alembic_override_cannot_bypass_reviewed_destination(monkeypatch):
    import sqlalchemy

    import app.core.config

    monkeypatch.setattr(app.core.config, "get_settings", lambda: settings())
    called = []

    def forbidden(*args, **kwargs):
        called.append(True)
        raise AssertionError("Unapproved migration must fail before engine construction")

    monkeypatch.setattr(sqlalchemy, "create_engine", forbidden)
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    cfg.attributes["database_url"] = URL.replace(HOST, "attacker.example")
    with pytest.raises(ValueError, match="Unapproved Render"):
        command.current(cfg)
    assert not called


def test_default_hosted_production_retains_verify_full():
    config = settings(database_tls_policy="verify_full", deployment_stage="production")
    args = session.database_connect_args(config)
    assert args["sslmode"] == "verify-full" and args["sslrootcert"]


def test_validation_logs_do_not_expose_database_password():
    with pytest.raises(ValidationError) as error:
        settings(deployment_stage="production")
    assert "OFFLINE_TEST_ONLY" not in str(error.value)


def test_worker_engine_uses_the_same_pinned_policy(monkeypatch):
    from app.workers import pipeline

    assert pipeline.get_engine is session.get_engine
    captured = {}

    def capture(url, **kwargs):
        captured.update(url=url, **kwargs)
        return object()

    monkeypatch.setattr(session, "get_settings", lambda: settings())
    monkeypatch.setattr(session, "create_engine", capture)
    session.get_engine.__wrapped__()
    assert captured["connect_args"]["sslmode"] == "require"
    assert captured["connect_args"]["host"] == HOST


def test_require_never_falls_back_to_plaintext_postgres():
    received = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(5)

        def refuse_tls():
            connection, _ = listener.accept()
            with connection:
                received.append(connection.recv(8))
                connection.sendall(b"N")

        thread = threading.Thread(target=refuse_tls)
        thread.start()
        # Redirect only this driver-protocol test to a disposable loopback listener.
        # Production helper's exact-host rejection is tested independently above.
        args = session.database_connect_args(settings()) | {
            "host": "127.0.0.1",
            "port": str(listener.getsockname()[1]),
        }
        engine = session.create_engine("postgresql+psycopg://", connect_args=args)
        try:
            with pytest.raises(OperationalError, match="does not support SSL"):
                engine.connect()
        finally:
            engine.dispose()
            thread.join(timeout=6)
    assert received == [struct.pack("!II", 8, 80877103)]
