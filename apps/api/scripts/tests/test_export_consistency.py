"""Exercise the exporter's actual DB override across concurrent committed changes."""
# ruff: noqa: S608 - SQL identifiers are generated exclusively from UUID hex, never input.

import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parents[1]))
from export_static_demo import consistent_reads

from app.db.session import get_db


def test_shared_snapshot_and_read_only_enforcement():
    url = os.environ.get("SENTINEL_EXPORT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires a dedicated loopback _test DB for a temporary probe table")
    parsed = make_url(url)
    assert parsed.host in {"127.0.0.1", "localhost"} and parsed.database.endswith("_test")
    engine = create_engine(url)
    table = "export_probe_" + uuid.uuid4().hex
    application = FastAPI()

    @application.get("/count")
    def count(db: Session = Depends(get_db)):
        return db.scalar(text(f"SELECT count(*) FROM {table}"))

    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE TABLE {table} (id integer)"))
        with TestClient(application) as client, consistent_reads(application, engine):
            assert client.get("/count").json() == 0
            with engine.begin() as writer:
                writer.execute(text(f"INSERT INTO {table} VALUES (1)"))
            assert client.get("/count").json() == 0
            with engine.connect() as live:
                assert live.scalar(text(f"SELECT count(*) FROM {table}")) == 1
            generator = application.dependency_overrides[get_db]()
            session = next(generator)
            with pytest.raises(DBAPIError, match="read-only"):
                session.execute(text(f"INSERT INTO {table} VALUES (2)"))
            generator.close()
        assert not application.dependency_overrides
    finally:
        with engine.begin() as cleanup:
            cleanup.execute(text(f"DROP TABLE IF EXISTS {table}"))
        engine.dispose()


@pytest.mark.parametrize(
    "setting,value",
    [
        ("SENTINEL_STATIC_FIXTURE_APPROVED", "false"),
        ("SENTINEL_DATABASE_URL", "postgresql+psycopg://localhost/production"),
        ("SENTINEL_DATABASE_URL", "postgresql+psycopg://database.example/fixture_test"),
        ("SENTINEL_PAYPAL_MODE", "sandbox"),
        ("SENTINEL_AI_PROVIDER", "google"),
    ],
)
def test_export_refuses_unapproved_sources(monkeypatch, tmp_path, setting, value):
    import export_static_demo

    for key, default in {
        "SENTINEL_STATIC_FIXTURE_APPROVED": "true",
        "SENTINEL_DATABASE_URL": "postgresql+psycopg://localhost/fixture_test",
        "SENTINEL_PAYPAL_MODE": "fixture",
        "SENTINEL_AI_PROVIDER": "none",
    }.items():
        monkeypatch.setenv(key, default)
    monkeypatch.setenv(setting, value)
    with pytest.raises(ValueError, match="approved disposable"):
        export_static_demo.main(tmp_path / "new-export")
    assert not (tmp_path / "new-export").exists()
