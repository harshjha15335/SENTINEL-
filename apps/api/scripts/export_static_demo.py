"""Export approved loopback fixture data through the VIEWER API using one database snapshot.

Usage: SENTINEL_STATIC_FIXTURE_APPROVED=true python scripts/export_static_demo.py NEW_OUT_DIR
Requires a disposable loopback database ending in _test, fixture PayPal and AI provider none.
The destination must not exist. No database credentials are serialized.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from validate_static_demo import read_snapshot, validate

from app.db.session import get_db, get_engine
from app.main import app

PAGE = 200


@contextmanager
def consistent_reads(application, engine):
    """One MVCC snapshot, independent read-only connections for concurrent API requests."""
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as keeper:
        keeper.execute(text("SET TRANSACTION READ ONLY"))
        snapshot_id = keeper.scalar(text("SELECT pg_export_snapshot()"))
        if not re.fullmatch(r"[0-9A-Fa-f]+-[0-9A-Fa-f]+-[0-9]+", snapshot_id):
            raise ValueError("Unexpected PostgreSQL snapshot identifier")
        captured = keeper.scalar(text("SELECT transaction_timestamp()")).isoformat()

        def consistent_db():
            with engine.connect().execution_options(
                isolation_level="REPEATABLE READ"
            ) as connection:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                # Only a validated, database-generated snapshot identifier is interpolated.
                connection.execute(text(f"SET TRANSACTION SNAPSHOT '{snapshot_id}'"))
                with Session(bind=connection) as session:
                    yield session

        previous = application.dependency_overrides.copy()
        application.dependency_overrides[get_db] = consistent_db
        try:
            yield captured
        finally:
            application.dependency_overrides.clear()
            application.dependency_overrides.update(previous)


def main(out: Path) -> None:
    url = make_url(os.environ["SENTINEL_DATABASE_URL"])
    if not (
        os.environ.get("SENTINEL_STATIC_FIXTURE_APPROVED") == "true"
        and url.host in {"localhost", "127.0.0.1", "::1"}
        and (url.database or "").endswith("_test")
        and os.environ.get("SENTINEL_PAYPAL_MODE") == "fixture"
        and os.environ.get("SENTINEL_AI_PROVIDER") == "none"
    ):
        raise ValueError(
            "Export requires an approved disposable loopback _test database, "
            "fixture gateway and AI none"
        )
    if out.exists():
        raise ValueError("Refusing to overwrite an existing export")
    password = os.environ["SENTINEL_SEED_VIEWER_PASSWORD"]
    revision = subprocess.check_output(  # noqa: S603 - fixed git arguments, no shell
        [shutil.which("git") or "/usr/bin/git", "rev-parse", "HEAD"], text=True
    ).strip()
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".static-export-", dir=out.parent))
    client = TestClient(app, base_url="http://localhost")
    try:
        response = client.post(
            "/api/v1/auth/login", json={"email": "viewer@northwind.example", "password": password}
        )
        response.raise_for_status()
        engine = get_engine()
        with consistent_reads(app, engine) as captured:

            def get(path: str) -> Any:
                r = client.get(f"/api/v1{path}")
                r.raise_for_status()
                return r.json()

            def write(name: str, data: Any) -> None:
                (stage / f"{name}.json").write_text(
                    json.dumps(data, separators=(",", ":"), sort_keys=True, allow_nan=False)
                )

            def all_pages(path: str) -> list[Any]:
                items: list[Any] = []
                total = None
                while total is None or len(items) < total:
                    page = get(f"{path}?limit={PAGE}&offset={len(items)}")
                    if total is None:
                        total = page["total"]
                    if total != page["total"] or (not page["items"] and len(items) != total):
                        raise ValueError("Inconsistent pagination")
                    items.extend(page["items"])
                if len(items) != total or len({r["id"] for r in items}) != total:
                    raise ValueError("Duplicate or missing paginated records")
                return items

            me = get("/me")
            write("me", me)
            for name, endpoint in [
                ("dashboard", "/dashboard/summary"),
                ("model", "/risk/model"),
                ("paypal-status", "/paypal/status"),
                ("products", "/products"),
            ]:
                write(name, get(endpoint))
            transactions = all_pages("/transactions")
            cases = all_pages("/cases")
            write("transactions", transactions)
            write("cases", cases)

            def record(t):
                detail = get(f"/transactions/{t['id']}")
                if any(detail[k] != v for k, v in t.items()):
                    raise ValueError("List/detail transaction mismatch")
                assessment = (
                    get(f"/transactions/{t['id']}/risk") if t["risk_band"] is not None else None
                )
                return t["id"], {k: v for k, v in detail.items() if k not in t}, assessment

            extras, risk = {}, {}
            with ThreadPoolExecutor(max_workers=4) as workers:
                for identifier, detail, assessment in workers.map(record, transactions):
                    extras[identifier] = detail
                    if assessment is not None:
                        risk[identifier] = assessment
                details = dict(
                    zip(
                        (c["id"] for c in cases),
                        workers.map(lambda c: get(f"/cases/{c['id']}"), cases),
                        strict=True,
                    )
                )
            write("transaction-extras", extras)
            write("risk", risk)
            write("case-details", details)
            write(
                "snapshot",
                {
                    "generated_at": datetime.now(UTC).isoformat(),
                    "commit": revision,
                    "persona": {"email": me["email"], "role": me["role"]},
                    "data_origins": sorted({t["data_origin"] for t in transactions}),
                    "counts": {
                        "transactions": len(transactions),
                        "scored": len(risk),
                        "cases": len(cases),
                    },
                    "provenance": {
                        "source": "approved disposable synthetic fixture database",
                        "consistency": "PostgreSQL exported REPEATABLE READ / READ ONLY snapshot",
                        "captured_at": captured,
                        "gateway": "fixture",
                        "ai_provider": "none",
                    },
                },
            )
            result = validate(read_snapshot(stage))
        stage.rename(out)
        print(json.dumps(result, sort_keys=True))
    finally:
        client.close()
        if stage.exists():
            shutil.rmtree(stage)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]).resolve())
