from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.models import RiskScoringJob, StoredBlob, WorkerHealth
from app.models.enums import DataOrigin, Role
from app.services.worker_health import heartbeat
from tests.conftest import login
from tests.test_risk_cases import T0, _txn


def test_readiness_rejects_migration_mismatch(app_client, db):
    revision = db.scalar(text("select version_num from alembic_version"))
    try:
        db.execute(text("update alembic_version set version_num='unreviewed'"))
        db.commit()
        response = app_client.get("/api/v1/ready")
        assert response.status_code == 503
        assert response.json()["checks"]["schema"] == "incompatible"
    finally:
        db.execute(text("update alembic_version set version_num=:v"), {"v": revision})
        db.commit()


@pytest.mark.parametrize(
    "offset,status,expected",
    [(-46, "HEALTHY", 503), (10, "HEALTHY", 503), (0, "DEGRADED", 503), (0, "HEALTHY", 200)],
)
def test_readiness_requires_fresh_healthy_workers(
    app_client, db, monkeypatch, offset, status, expected
):
    monkeypatch.setattr(get_settings(), "require_workers_ready", True)
    for name in ("pipeline", "supabase_bridge"):
        db.add(
            WorkerHealth(
                name=name, status=status, heartbeat_at=datetime.now(UTC) + timedelta(seconds=offset)
            )
        )
    db.commit()
    response = app_client.get("/api/v1/ready")
    assert response.status_code == expected
    assert response.json()["checks"]["paypal_provider_verification"] == "unverified_by_readiness"


def test_operations_permissions_tenant_origin_and_snapshot_scope(
    app_client, db, tenant, other_tenant, monkeypatch
):
    assert app_client.get("/api/v1/operations/webhooks").status_code == 401
    for role in (Role.ANALYST, Role.VIEWER):
        login(app_client, tenant.users[role].email)
        assert app_client.get("/api/v1/operations/webhooks").status_code == 403
    own = _txn(db, tenant, at=T0, origin=DataOrigin.SIMULATED)
    other = _txn(db, other_tenant, at=T0, origin=DataOrigin.LIVE_SANDBOX)
    db.add_all(
        [
            RiskScoringJob(transaction_id=own.id, status="DEAD"),
            RiskScoringJob(transaction_id=other.id, status="PENDING"),
        ]
    )
    db.add_all(
        [
            StoredBlob(key=f"{tenant.merchant.id}/evidence/a", body=b"abc"),
            StoredBlob(key=f"{other_tenant.merchant.id}/evidence/b", body=b"private"),
        ]
    )
    now = datetime.now(UTC)
    db.add(
        WorkerHealth(
            name="supabase_bridge",
            status="HEALTHY",
            heartbeat_at=now,
            inbox_snapshot={
                "observed_at": now.isoformat(),
                "groups": [
                    {
                        "data_origin": "SIMULATED",
                        "status": "DEAD",
                        "count": 1,
                        "oldest_received_at": now.isoformat(),
                        "last_attempt_at": None,
                        "raw_body": "never expose",
                    }
                ],
            },
        )
    )
    db.commit()
    login(app_client, tenant.users[Role.ADMIN].email)
    r = app_client.get("/api/v1/operations/webhooks")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    data = r.json()
    assert data["inbox"] is None and data["inbox_scope"] == "not_authorized"
    assert data["scoring_jobs"] == [{"data_origin": "SIMULATED", "status": "DEAD", "count": 1}]
    assert data["storage"]["stored_files"] == 1 and data["storage"]["stored_bytes"] == 3
    assert data["integrations"]["last_verified_event_at"] is None
    monkeypatch.setattr(get_settings(), "operations_inbox_merchant_id", tenant.merchant.id)
    data = app_client.get("/api/v1/operations/webhooks").json()
    assert data["inbox_fresh"] is True
    assert data["inbox"]["groups"][0]["status"] == "DEAD"
    assert "never expose" not in str(data)
    login(app_client, other_tenant.users[Role.ADMIN].email)
    assert app_client.get("/api/v1/operations/webhooks").json()["inbox"] is None


def test_idle_heartbeat_preserves_last_success_and_snapshot(db):
    heartbeat("supabase_bridge", "HEALTHY", processed=1, inbox_snapshot={"observed_at": "example"})
    w = db.get(WorkerHealth, "supabase_bridge")
    assert w.last_success_at is not None
    last = w.last_success_at
    heartbeat("supabase_bridge", "HEALTHY")
    db.refresh(w)
    assert w.last_success_at == last
    assert w.processed == 1 and w.inbox_snapshot == {"observed_at": "example"}


def test_hosted_security_configuration_rejects_insecure_defaults():
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError, match="Hosted deployment requires"):
        Settings(hosted_deployment=True)
    settings = Settings(
        hosted_deployment=True,
        environment="production",
        cookie_secure=True,
        storage_backend="database",
        require_workers_ready=True,
        cors_origins=[],
    )
    assert settings.hosted_deployment
