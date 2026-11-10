"""Dependency-free static snapshot gate, shared by the API exporter and Vite build."""

import json
import re
import sys
from collections import Counter
from pathlib import Path

FILES = (
    "me",
    "dashboard",
    "model",
    "paypal-status",
    "products",
    "transactions",
    "transaction-extras",
    "risk",
    "cases",
    "case-details",
    "snapshot",
)
ORIGINS = {"SIMULATED", "SYNTHETIC_DEMO"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate(data):
    txs, cases = data["transactions"], data["cases"]
    tx = {r["id"]: r for r in txs}
    cs = {r["id"]: r for r in cases}
    risk, extras, details = (data[n] for n in ("risk", "transaction-extras", "case-details"))
    require(len(tx) == len(txs) and len(cs) == len(cases), "Duplicate record identifiers")
    for identifier in [*tx, *cs, *risk, *extras, *details]:
        require(
            bool(re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", identifier)),
            "Invalid identifier",
        )
    require(
        set(extras) == set(tx), "Transaction extras must cover exactly the exported transactions"
    )
    require(set(details) == set(cs), "Case details must cover exactly the exported cases")
    require(
        set(risk) == {r["id"] for r in txs if r["risk_band"] is not None},
        "Recorded risk coverage mismatch",
    )
    for identifier, assessment in risk.items():
        row = tx[identifier]
        require(assessment["transaction_id"] == identifier, "Assessment transaction mismatch")
        for field in ("risk_band", "risk_score", "data_origin"):
            require(assessment[field] == row[field], f"Assessment {field} mismatch")
    require(len({r["id"] for r in risk.values()}) == len(risk), "Duplicate assessment identifiers")
    for identifier, extra in extras.items():
        require(not (set(extra) & set(tx[identifier])), "Extras override transaction fields")
        for event in extra.get("events", []):
            if "transaction_id" in event:
                require(event["transaction_id"] == identifier, "Payment event transaction mismatch")
        for audit in extra.get("audit", []):
            require(
                audit["entity_type"] == "transaction" and audit["entity_id"] == identifier,
                "Transaction audit mismatch",
            )
    for identifier, case in cs.items():
        tid = case["transaction_id"]
        require(tid in tx, f"Case {identifier} references missing transaction {tid}")
        require(case["transaction"] == tx[tid], "Case embedded transaction mismatch")
        require(case["data_origin"] == tx[tid]["data_origin"], "Case origin mismatch")
        detail = details[identifier]
        require(
            all(detail.get(k) == v for k, v in case.items()),
            "Case detail identity/content mismatch",
        )
        assessment = detail.get("assessment")
        if case["risk_assessment_id"] is not None:
            require(
                assessment is not None
                and assessment["id"] == case["risk_assessment_id"]
                and assessment["transaction_id"] == tid,
                "Case recorded assessment reference mismatch",
            )
            # A case may refer to an earlier assessment than the latest transaction score.
            require(
                assessment["data_origin"] == tx[tid]["data_origin"],
                "Case assessment origin mismatch",
            )
        else:
            require(assessment is None, "Unexpected case assessment")
        for note in detail.get("notes", []):
            if "case_id" in note:
                require(note["case_id"] == identifier, "Case note reference mismatch")
        for audit in detail.get("audit", []):
            require(
                (audit["entity_type"] == "case" and audit["entity_id"] == identifier)
                or audit.get("metadata", {}).get("case_id") == identifier,
                "Case audit mismatch",
            )
            if audit.get("metadata", {}).get("transaction_id") is not None:
                require(
                    audit["metadata"]["transaction_id"] == tid, "Case audit transaction mismatch"
                )
    dash = data["dashboard"]
    require(dash["transactions_total"] == len(tx), "Dashboard transaction count mismatch")
    require(
        dash["by_status"] == dict(Counter(r["status"] for r in txs)),
        "Dashboard status totals mismatch",
    )
    for row in dash["recent"]:
        require(row["id"] in tx and row == tx[row["id"]], "Dashboard recent reference mismatch")
    for group in dash["captured_by_origin"]:
        rows = [
            r
            for r in txs
            if r["status"] == "CAPTURED"
            and r["data_origin"] == group["data_origin"]
            and r["currency"] == group["currency"]
        ]
        require(
            group["captured_count"] == len(rows)
            and group["captured_amount_minor"] == sum(r["amount_minor"] for r in rows),
            "Dashboard captured totals mismatch",
        )
    for groups, rows, key_field in [
        (dash["open_cases_by_origin"], [c for c in cases if c["status"] != "RESOLVED"], "priority"),
        (dash["risk_bands_by_origin"], list(risk.values()), "risk_band"),
    ]:
        actual = Counter((r["data_origin"], r[key_field]) for r in rows)
        exported = {(g["data_origin"], g["key"]): g["count"] for g in groups}
        require(dict(actual) == exported, "Dashboard case/risk groups mismatch")
    counts = {"transactions": len(tx), "scored": len(risk), "cases": len(cs)}
    require(data["snapshot"]["counts"] == counts, "Serialized snapshot count mismatch")
    origins = sorted({r["data_origin"] for r in txs})
    require(
        set(origins) <= ORIGINS and bool(origins),
        "Only synthetic/simulated records may be exported",
    )
    require(data["snapshot"]["data_origins"] == origins, "Snapshot origin summary mismatch")
    require(
        data["me"]["role"] == "VIEWER" and data["me"]["email"] == "viewer@northwind.example",
        "Export requires the seeded fixture viewer",
    )
    require(
        data["paypal-status"]["mode"] == "fixture" and data["paypal-status"]["client_id"] is None,
        "Provider configuration is not public-safe",
    )

    def privacy(value):
        if isinstance(value, dict):
            for key, child in value.items():
                require(
                    key.lower()
                    not in {
                        "password",
                        "password_hash",
                        "access_token",
                        "refresh_token",
                        "client_secret",
                        "authorization",
                        "cookie",
                        "database_url",
                        "api_key",
                    },
                    "Sensitive field in export",
                )
                if key == "data_origin":
                    require(child in ORIGINS, "Non-demo origin in nested export")
                if key == "email" and child:
                    require(child.endswith("@northwind.example"), "Non-fixture email in export")
                privacy(child)
        elif isinstance(value, list):
            for child in value:
                privacy(child)
        elif isinstance(value, str):
            require(
                not re.search(
                    r"(?:postgres(?:ql)?(?:\+psycopg)?://|-----BEGIN .*PRIVATE KEY|"
                    r"\beyJ[A-Za-z0-9_-]+\.eyJ)",
                    value,
                ),
                "Credential material in export",
            )

    privacy(data)
    return {"valid": True, "counts": counts, "data_origins": origins, "unresolved_references": 0}


def read_snapshot(directory):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    require(
        {p.name for p in directory.iterdir()} == {f"{n}.json" for n in FILES},
        "Unexpected or missing snapshot files",
    )
    return {
        n: json.loads((directory / f"{n}.json").read_text(), object_pairs_hook=unique)
        for n in FILES
    }


if __name__ == "__main__":
    print(json.dumps(validate(read_snapshot(Path(sys.argv[1]))), sort_keys=True))
