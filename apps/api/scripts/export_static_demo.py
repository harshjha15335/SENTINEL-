"""Export a read-only JSON snapshot of the demo for the static GitHub Pages build.

Every file is a real API response: the script signs in as the seeded VIEWER account and calls
the same endpoints the web app calls, against a database filled by `python -m app.cli demo-load`.
Nothing is hand-written, and nothing is sent to PayPal.

Usage (from apps/api, with SENTINEL_DATABASE_URL and SENTINEL_SEED_VIEWER_PASSWORD set):
    python scripts/export_static_demo.py OUT_DIR
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app

PAGE = 200


def main(out: Path) -> None:
    password = os.environ.get("SENTINEL_SEED_VIEWER_PASSWORD")
    if not password:
        sys.exit("SENTINEL_SEED_VIEWER_PASSWORD is required")
    client = TestClient(app, base_url="http://localhost")
    resp = client.post(
        "/api/v1/auth/login", json={"email": "viewer@northwind.example", "password": password}
    )
    resp.raise_for_status()

    def get(path: str) -> Any:
        r = client.get(f"/api/v1{path}")
        r.raise_for_status()
        return r.json()

    def write(name: str, data: Any) -> None:
        path = out / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, separators=(",", ":")))

    def all_pages(path: str) -> list[Any]:
        items: list[Any] = []
        while True:
            sep = "&" if "?" in path else "?"
            page = get(f"{path}{sep}limit={PAGE}&offset={len(items)}")
            items.extend(page["items"])
            if len(items) >= page["total"] or not page["items"]:
                return items

    me = get("/me")
    write("me", me)
    write("dashboard", get("/dashboard/summary"))
    write("model", get("/risk/model"))
    write("paypal-status", get("/paypal/status"))
    write("products", get("/products"))

    transactions = all_pages("/transactions")
    write("transactions", transactions)
    scored = 0
    for t in transactions:
        write(f"transactions/{t['id']}", get(f"/transactions/{t['id']}"))
        if t["risk_band"] is not None:
            write(f"risk/{t['id']}", get(f"/transactions/{t['id']}/risk"))
            scored += 1

    cases = all_pages("/cases")
    write("cases", cases)
    for c in cases:
        write(f"cases/{c['id']}", get(f"/cases/{c['id']}"))

    origins = sorted({t["data_origin"] for t in transactions})
    write(
        "snapshot",
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "commit": os.environ.get("GITHUB_SHA"),
            "persona": {"email": me["email"], "role": me["role"]},
            "data_origins": origins,
            "counts": {"transactions": len(transactions), "scored": scored, "cases": len(cases)},
        },
    )
    print(
        f"exported {len(transactions)} transactions, {scored} assessments, {len(cases)} cases"
        f" ({', '.join(origins)}) to {out}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
