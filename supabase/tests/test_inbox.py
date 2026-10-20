"""Run against the dedicated local sentinel_supabase_check database, never the app database."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict

URL = os.environ.get("SENTINEL_SUPABASE_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not URL, reason="Set the dedicated Supabase SQL test database URL"
)


@pytest.fixture(scope="module", autouse=True)
def migrated():
    params = conninfo_to_dict(URL)
    assert params.get("dbname") == "sentinel_supabase_check"
    assert params.get("host") in ("127.0.0.1", "localhost")
    with psycopg.connect(URL, autocommit=True) as db:
        for role in ["anon", "authenticated", "service_role"]:
            if not db.execute(
                "select 1 from pg_roles where rolname=%s", (role,)
            ).fetchone():
                db.execute(
                    f"create role {role} nologin"
                    + (" bypassrls" if role == "service_role" else "")
                )
        db.execute(
            Path(__file__)
            .parents[1]
            .joinpath("migrations/202610200001_webhook_inbox.sql")
            .read_text()
        )
    yield


@pytest.fixture
def db(migrated):
    with psycopg.connect(URL, autocommit=True) as connection:
        connection.execute("truncate public.sentinel_webhook_inbox")
        yield connection


def enqueue(db, event_id="WH-1", extra=None):
    raw = json.dumps(
        {
            "id": event_id,
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": extra or {},
        }
    )
    return db.execute(
        "select public.sentinel_enqueue_webhook(%s,%s,%s,%s)",
        (event_id, "PAYMENT.CAPTURE.COMPLETED", raw, "{}"),
    ).fetchone()[0]


def test_idempotent_insert_and_changed_body_conflict(db):
    db.execute("set role service_role")
    assert enqueue(db) is True
    assert enqueue(db) is False
    with pytest.raises(psycopg.errors.UniqueViolation):
        enqueue(db, extra={"changed": True})
    assert (
        db.execute("select count(*) from public.sentinel_webhook_inbox").fetchone()[0]
        == 1
    )


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_clients_cannot_read_or_enqueue(db, role):
    db.execute(f"set role {role}")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute("select * from public.sentinel_webhook_inbox")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        enqueue(db)


def test_leases_retry_and_stale_acknowledgement(db):
    assert enqueue(db)
    row = db.execute(
        "select id, lease_token from public.sentinel_claim_webhooks(1)"
    ).fetchone()
    assert row
    assert not db.execute("select * from public.sentinel_claim_webhooks(1)").fetchall()
    db.execute(
        "update public.sentinel_webhook_inbox set available_at=now()-interval '1 second'"
    )
    next_row = db.execute(
        "select id, lease_token from public.sentinel_claim_webhooks(1)"
    ).fetchone()
    assert row[1] != next_row[1]
    assert (
        db.execute("select public.sentinel_finish_webhook(%s,%s,true)", row).fetchone()[
            0
        ]
        is False
    )
    assert (
        db.execute(
            "select public.sentinel_finish_webhook(%s,%s,true)", next_row
        ).fetchone()[0]
        is True
    )
    assert not db.execute("select * from public.sentinel_claim_webhooks(1)").fetchall()


def test_concurrent_claims_are_disjoint(db):
    enqueue(db, "WH-1")
    enqueue(db, "WH-2")

    def claim(_):
        with psycopg.connect(URL) as connection:
            return connection.execute(
                "select id from public.sentinel_claim_webhooks(1)"
            ).fetchone()[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(claim, range(2)))
    assert len(set(ids)) == 2


def test_exhausted_deliveries_remain_stored_for_operator_review(db):
    enqueue(db)
    db.execute("update public.sentinel_webhook_inbox set attempts=10")
    assert not db.execute("select * from public.sentinel_claim_webhooks(25)").fetchall()
    assert (
        db.execute(
            "select count(*) from public.sentinel_webhook_inbox where processed_at is null"
        ).fetchone()[0]
        == 1
    )
