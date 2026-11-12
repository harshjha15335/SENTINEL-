"""Mode-aware readiness without weakening required workers or integration health."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.core.config import PayPalMode, Settings, get_settings
from app.models import WorkerHealth
from app.services import readiness
from app.workers import supervisor


def worker(db, name="pipeline", status="HEALTHY", age=0):
    row = db.get(WorkerHealth, name)
    if row is None:
        row = WorkerHealth(name=name)
        db.add(row)
    row.status = status
    row.heartbeat_at = datetime.now(UTC) - timedelta(seconds=age)
    db.commit()


def test_fixture_without_supabase_keeps_pipeline_required(app_client, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "require_workers_ready", True)
    assert app_client.get("/api/v1/health").status_code == 200
    assert app_client.get("/api/v1/ready").status_code == 503
    worker(db)
    response = app_client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["checks"]["supabase_bridge"] == "not_required_fixture_mode"
    assert db.get(WorkerHealth, "supabase_bridge") is None


@pytest.mark.parametrize("status,age", [("DEGRADED", 0), ("STOPPED", 0), ("HEALTHY", 46)])
def test_fixture_worker_failure_and_recovery(app_client, db, monkeypatch, status, age):
    monkeypatch.setattr(get_settings(), "require_workers_ready", True)
    worker(db, status=status, age=age)
    assert app_client.get("/api/v1/ready").status_code == 503
    worker(db)
    assert app_client.get("/api/v1/ready").status_code == 200


def test_database_unavailable_is_not_ready(monkeypatch):
    class UnavailableDB:
        def execute(self, *_args):
            raise OperationalError("unavailable", {}, Exception())

        def rollback(self):
            pass

    ok, checks = readiness.readiness(UnavailableDB())
    assert not ok and checks["schema"] == "unavailable"


def test_sandbox_cannot_use_fixture_bridge_exemption(app_client, db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "require_workers_ready", True)
    monkeypatch.setattr(settings, "paypal_mode", PayPalMode.SANDBOX)
    worker(db)
    worker(db, "supabase_bridge")  # Even a stale/config-less row cannot replace configuration.
    response = app_client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["supabase_configuration"] == "absent"


def test_configured_fixture_bridge_must_initialize_and_recover(app_client, db, monkeypatch):
    from pydantic import SecretStr

    settings = get_settings()
    monkeypatch.setattr(settings, "require_workers_ready", True)
    monkeypatch.setattr(settings, "supabase_url", "https://offline-example.supabase.co")
    monkeypatch.setattr(settings, "supabase_service_role_key", SecretStr("OFFLINE_TEST_ONLY"))
    worker(db)
    assert app_client.get("/api/v1/ready").status_code == 503
    worker(db, "supabase_bridge", status="DEGRADED")
    assert app_client.get("/api/v1/ready").status_code == 503
    worker(db, "supabase_bridge")
    assert app_client.get("/api/v1/ready").status_code == 200


@pytest.mark.parametrize(
    "values",
    [
        {"supabase_url": "https://offline-example.supabase.co"},
        {"supabase_service_role_key": "OFFLINE_TEST_ONLY"},
        {
            "supabase_url": "http://offline-example.supabase.co",
            "supabase_service_role_key": "OFFLINE_TEST_ONLY",
        },
        {
            "supabase_url": "https://attacker.example",
            "supabase_service_role_key": "OFFLINE_TEST_ONLY",
        },
        {
            "supabase_url": "https://offline-example.supabase.co:bad",
            "supabase_service_role_key": "OFFLINE_TEST_ONLY",
        },
        {
            "supabase_url": "https://offline-example.supabase.co\n",
            "supabase_service_role_key": "OFFLINE_TEST_ONLY",
        },
    ],
)
def test_partial_or_untrusted_integration_configuration_rejected(values):
    with pytest.raises(ValidationError, match="Supabase"):
        Settings(_env_file=None, **values)


def test_sandbox_supervisor_refuses_missing_bridge_before_children(monkeypatch):
    settings = Settings(_env_file=None, paypal_mode="sandbox", require_workers_ready=True)
    monkeypatch.setattr(supervisor, "get_settings", lambda: settings)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Missing mandatory integration must fail before process startup")

    monkeypatch.setattr(supervisor.subprocess, "Popen", forbidden)
    with pytest.raises(SystemExit, match="Required Supabase"):
        supervisor.main()
