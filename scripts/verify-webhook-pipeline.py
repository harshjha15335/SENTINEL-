#!/usr/bin/env python3
"""Explicit deterministic fixture exercise against the hosted private SIMULATED inbox.

Never sends a PayPal request. Uses an isolated local database and receiver with
injected fixture verification; production receiver and genuine inbox rows are untouched.
"""

import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))


def fixture_database_url():
    from sqlalchemy.engine import make_url

    value = os.environ.get("SENTINEL_FIXTURE_DATABASE_URL", "")
    if not value:
        raise SystemExit(
            "Set SENTINEL_FIXTURE_DATABASE_URL to a dedicated loopback _test database"
        )
    parsed = make_url(value)
    if parsed.host not in ("localhost", "127.0.0.1") or not (
        parsed.database or ""
    ).endswith("_test"):
        raise SystemExit("Hosted fixtures require a dedicated loopback _test database")
    return value


def inbox_snapshot(rpc, project):
    response = rpc.get(
        project + "/rest/v1/sentinel_webhook_inbox",
        params={"select": "*", "limit": 1000},
    )
    response.raise_for_status()
    rows = response.json()
    if len(rows) >= 1000 or any(
        row["status"] in ("PENDING", "RUNNING") for row in rows
    ):
        raise RuntimeError(
            "Fixture verification requires a bounded inbox without active receipts"
        )
    return {
        row["id"]: hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        for row in rows
    }


def main():
    if "--allow-hosted-fixtures" not in sys.argv:
        raise SystemExit(
            "Pass --allow-hosted-fixtures to write explicitly SIMULATED test receipts"
        )
    project = os.environ["SENTINEL_SUPABASE_URL"]
    key = os.environ["SENTINEL_SUPABASE_SERVICE_ROLE_KEY"]
    database = fixture_database_url()
    fixture_key = secrets.token_urlsafe(32)
    os.environ.update(
        SENTINEL_DATABASE_URL=database,
        SENTINEL_ENVIRONMENT="test",
        SENTINEL_ALLOW_WEBHOOK_FIXTURES="true",
        SENTINEL_WEBHOOK_FIXTURE_KEY=fixture_key,
        SENTINEL_REQUIRE_WORKERS_READY="false",
        SENTINEL_PAYPAL_MODE="fixture",
        SENTINEL_AI_PROVIDER="none",
    )
    import httpx
    from sqlalchemy import func, select
    from app.db.session import get_sessionmaker
    from app.models import (
        Case,
        Merchant,
        PaymentEvent,
        RiskAssessment,
        RiskScoringJob,
        Transaction,
    )
    from app.models.enums import DataOrigin, MerchantEnvironment, TransactionStatus
    from app.services.inbox_bridge import DeliveryDeferred, poll_once

    output = Path(
        os.environ.get(
            "SENTINEL_FIXTURE_OUTPUT",
            "/workspace/sentinel-recovery-audit/hosted-fixture",
        )
    )
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    children, logs = [], []
    python = str(ROOT / "apps/api/.venv/bin/python")
    env = os.environ.copy()
    env.update(
        SENTINEL_FIXTURE_RECEIVER="true",
        DENO_DIR="/workspace/.cache/deno",
        DENO_TLS_CA_STORE="system",
    )

    def start(name, command):
        fd = os.open(
            output / (name + ".log"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
        )
        log = os.fdopen(fd, "a")
        logs.append(log)
        process = subprocess.Popen(
            command,
            cwd=ROOT / "apps/api",
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        children.append(process)
        return process

    def wait_api(url):
        for _ in range(40):
            try:
                with httpx.Client(timeout=2) as client:
                    if client.get(url).status_code == 200:
                        return
            except httpx.HTTPError:
                pass
            time.sleep(0.3)
        raise RuntimeError("Fixture service did not become ready")

    def expire(row):
        # Advance only this fixture's lease clock; never alter genuine receipts.
        identity = str(uuid.UUID(row["id"]))
        query = f"update public.sentinel_webhook_inbox set available_at=now()-interval '1 second' where id='{identity}' and data_origin='SIMULATED'"
        req = urllib.request.Request(
            "https://api.supabase.com/v1/projects/cfslzvvdjxstpupkqbpw/database/query",
            data=json.dumps({"query": query}).encode(),
            headers={
                "Authorization": "Bearer " + os.environ["SUPABASE_ACCESS_TOKEN"],
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            response.read()

    def stop(process):
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=15)

    api_command = [
        python,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8042",
    ]
    try:
        subprocess.run(
            [str(ROOT / "apps/api/.venv/bin/alembic"), "upgrade", "head"],
            cwd=ROOT / "apps/api",
            env=env,
            check=True,
        )
        now = datetime(2026, 9, 1, 12, tzinfo=UTC)
        run = str(uuid.uuid4())
        with get_sessionmaker()() as db:
            merchant = Merchant(
                name="SIMULATED webhook fixture " + run,
                environment=MerchantEnvironment.DEMO,
            )
            db.add(merchant)
            db.flush()
            for i in range(20):
                db.add(
                    Transaction(
                        merchant_id=merchant.id,
                        quantity=1,
                        amount_minor=1000,
                        currency="USD",
                        status=TransactionStatus.CAPTURED,
                        payer_reference="FIXTURE-PAYER",
                        data_origin=DataOrigin.SIMULATED,
                        occurred_at=now - timedelta(minutes=i + 1),
                        refunded_at=now - timedelta(minutes=i),
                        create_idempotency_key=str(uuid.uuid4()),
                        paypal_request_id=str(uuid.uuid4()),
                        provider_summary={},
                    )
                )
            txn = Transaction(
                merchant_id=merchant.id,
                quantity=1,
                amount_minor=500000,
                currency="USD",
                status=TransactionStatus.ORDER_CREATED,
                payer_reference="FIXTURE-PAYER",
                data_origin=DataOrigin.SIMULATED,
                paypal_order_id="SIM-FIXTURE-" + run,
                create_idempotency_key=str(uuid.uuid4()),
                paypal_request_id=str(uuid.uuid4()),
                provider_summary={},
            )
            db.add(txn)
            db.commit()
            txn_id = txn.id
            order_id = txn.paypal_order_id
        api = start("api", api_command)
        receiver = start(
            "receiver",
            [
                "/workspace/sentinel-tools/node_modules/.bin/deno",
                "run",
                "--allow-env",
                "--allow-net",
                str(ROOT / "scripts/fixture-webhook-receiver.ts"),
            ],
        )
        wait_api("http://127.0.0.1:8042/api/v1/ready")
        wait_api("http://127.0.0.1:8043/")
        with (
            httpx.Client(
                base_url=project + "/rest/v1/rpc/",
                headers={"apikey": key, "Authorization": "Bearer " + key},
                timeout=30,
            ) as rpc,
            httpx.Client(base_url="http://127.0.0.1:8042", timeout=30) as local,
        ):
            historical = inbox_snapshot(rpc, project)

            def receipt(event_type):
                body = json.dumps(
                    {
                        "id": "FIXTURE-" + str(uuid.uuid4()),
                        "event_type": event_type,
                        "create_time": now.isoformat(),
                        "resource": {
                            "id": "SIM-CAPTURE-" + run,
                            "amount": {"value": "5000.00", "currency_code": "USD"},
                            "supplementary_data": {
                                "related_ids": {"order_id": order_id}
                            },
                        },
                    },
                    separators=(",", ":"),
                )
                headers = {
                    "paypal-transmission-id": "FIXTURE-TRANSMISSION",
                    "paypal-transmission-time": now.isoformat(),
                    "paypal-cert-url": "https://api.sandbox.paypal.com/v1/notifications/certs/FIXTURE",
                    "paypal-auth-algo": "SHA256withRSA",
                    "paypal-transmission-sig": "FIXTURE_ONLY",
                }
                response = local.post(
                    "http://127.0.0.1:8043/", content=body, headers=headers
                )
                assert response.status_code == 200, (
                    response.status_code,
                    response.text,
                )
                return body, headers

            def cloud_row(body):
                response = rpc.get(
                    project + "/rest/v1/sentinel_webhook_inbox",
                    params={
                        "provider_event_id": "eq." + json.loads(body)["id"],
                        "select": "id,lease_token,status,data_origin,attempts,processed_at,last_error",
                    },
                )
                response.raise_for_status()
                return response.json()[0]

            body, headers = receipt("PAYMENT.CAPTURE.COMPLETED")
            duplicate = local.post(
                "http://127.0.0.1:8043/", content=body, headers=headers
            )
            assert duplicate.json()["duplicate"] is True
            row = cloud_row(body)
            assert row["data_origin"] == "SIMULATED" and row["status"] == "PENDING"
            claimed = rpc.post(
                "sentinel_claim_webhooks", json={"p_limit": 1, "p_origin": "SIMULATED"}
            )
            claimed.raise_for_status()
            old = claimed.json()[0]
            assert old["provider_event_id"] == json.loads(body)["id"]
            expire(old)  # A worker died after claiming; another worker must reclaim.
            stop(api)
            try:
                poll_once(rpc, local, fixtures=True, fixture_key=fixture_key)
            except DeliveryDeferred:
                pass
            else:
                raise AssertionError("API unavailability was incorrectly acknowledged")
            row = cloud_row(body)
            assert row["status"] == "PENDING" and row["processed_at"] is None
            expire(row)
            api = start("api", api_command)
            wait_api("http://127.0.0.1:8042/api/v1/ready")
            assert poll_once(rpc, local, fixtures=True, fixture_key=fixture_key) == 1
            with get_sessionmaker()() as db:
                job = db.scalar(
                    select(RiskScoringJob).where(
                        RiskScoringJob.transaction_id == txn_id
                    )
                )
                assert job.status == "PENDING"  # Durable acceptance precedes scoring.
            worker = start("pipeline", [python, "-m", "app.workers.pipeline"])
            for _ in range(40):
                with get_sessionmaker()() as db:
                    assessment = db.scalar(
                        select(RiskAssessment).where(
                            RiskAssessment.transaction_id == txn_id
                        )
                    )
                    if assessment is not None:
                        assert (
                            assessment.risk_band.value == "HIGH"
                            and assessment.data_origin is DataOrigin.SIMULATED
                        )
                        assert (
                            db.scalar(
                                select(func.count())
                                .select_from(Case)
                                .where(Case.transaction_id == txn_id)
                            )
                            == 1
                        )
                        score = assessment.risk_score
                        break
                time.sleep(0.25)
            else:
                raise AssertionError("Durable scoring job did not complete")
            stale = rpc.post(
                "sentinel_finish_webhook",
                json={
                    "p_id": old["id"],
                    "p_lease_token": old["lease_token"],
                    "p_success": True,
                },
            )
            assert stale.json() is False
            pending, _ = receipt("PAYMENT.CAPTURE.PENDING")
            assert poll_once(rpc, local, fixtures=True, fixture_key=fixture_key) == 1
            invalid, _ = receipt("PAYMENT.CAPTURE.COMPLETED")
            assert (
                poll_once(rpc, local, fixtures=True, fixture_key="wrong-fixture-key")
                == 0
            )
            assert cloud_row(invalid)["status"] == "DEAD"
            with get_sessionmaker()() as db:
                assert db.get(Transaction, txn_id).status is TransactionStatus.CAPTURED
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(RiskAssessment)
                        .where(RiskAssessment.transaction_id == txn_id)
                    )
                    == 1
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(Case)
                        .where(Case.transaction_id == txn_id)
                    )
                    == 1
                )
                stored = db.scalar(
                    select(PaymentEvent).where(
                        PaymentEvent.provider_event_id == json.loads(body)["id"]
                    )
                )
                assert (
                    stored.payload_sha256 == hashlib.sha256(body.encode()).hexdigest()
                )
                case = db.scalar(select(Case).where(Case.transaction_id == txn_id))
                job = db.scalar(
                    select(RiskScoringJob).where(
                        RiskScoringJob.transaction_id == txn_id
                    )
                )
                workflow = complete_case_workflow(db, merchant.id, case)
                trace = {
                    "event_id": stored.provider_event_id,
                    "event_trace_id": hashlib.sha256(
                        stored.provider_event_id.encode()
                    ).hexdigest()[:32],
                    "payment_event_id": str(stored.id),
                    "scoring_job_id": str(job.id),
                    "case_id": str(case.id),
                    "payload_sha256": stored.payload_sha256,
                    **workflow,
                }
            after = inbox_snapshot(rpc, project)
            assert all(
                after.get(identity) == digest for identity, digest in historical.items()
            )
            result = {
                "fixture_origin": "SIMULATED",
                "provider_calls": 0,
                "transaction_id": str(txn_id),
                "score": score,
                "risk_band": "HIGH",
                "case_count": 1,
                "receiver_duplicate": True,
                "worker_crash_reclaimed": True,
                "api_unavailability_retried": True,
                "stale_ack_rejected": True,
                "out_of_order_preserved": True,
                "invalid_fixture_signature_terminal": True,
                "capture_inbox": cloud_row(body),
                "invalid_inbox": cloud_row(invalid),
                "historical_inbox_rows_preserved": len(historical),
                "historical_row_hashes_unchanged": True,
                "trace": trace,
                "application_database": "dedicated loopback _test database",
                "scope": "local fixture receiver -> real remote SIMULATED inbox -> local HTTP API/worker -> service-layer evidence/investigation/approval; not genuine PayPal or a public Python deployment",
            }
            (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result, indent=2))
    finally:
        for process in children:
            if process.poll() is None:
                process.terminate()
        for process in children:
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for log in logs:
            log.close()


def complete_case_workflow(db, merchant_id, case):
    """Complete only this isolated synthetic case, without an AI or financial provider."""
    import io
    from reportlab.pdfgen import canvas
    from app.auth.deps import Principal
    from app.auth.passwords import hash_password
    from app.models import InvestigationRun, User, UserSession
    from app.models.enums import (
        ApprovalActionType,
        ApprovalDecisionValue,
        EvidenceCategory,
        Role,
    )
    from app.services import approvals, packets
    from app.services.evidence import service as evidence
    from app.services.investigation import runner

    actors = {}
    for role in (Role.ANALYST, Role.ADMIN):
        user = User(
            merchant_id=merchant_id,
            email=f"fixture-{role.value.lower()}-{uuid.uuid4()}@example.invalid",
            role=role,
            password_hash=hash_password(secrets.token_urlsafe(32)),
        )
        db.add(user)
        db.flush()
        actors[role] = Principal(user=user, session=UserSession())
    db.commit()
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream)
    pdf.drawString(
        40, 780, "SIMULATED integration fixture; not proof of actual delivery."
    )
    pdf.save()
    artifact = evidence.upload(
        db,
        actors[Role.ANALYST],
        case.id,
        data=stream.getvalue(),
        declared_type="application/pdf",
        filename="fixture-evidence.pdf",
        category=EvidenceCategory.OTHER,
        description="Authorized fixture attachment, not provider evidence.",
    )
    run = runner.start(db, actors[Role.ANALYST], case.id, deterministic=True)
    runner.execute(run.id)
    db.expire_all()
    assert db.get(InvestigationRun, run.id).status.value == "COMPLETED"
    packet = packets.generate(db, actors[Role.ANALYST], case.id)
    request = approvals.create(
        db,
        actors[Role.ANALYST],
        case.id,
        action=ApprovalActionType.EVIDENCE_PACKET_INTERNAL,
        packet_id=packet.id,
        justification="Fixture internal packet review; no provider submission.",
    )
    decided = approvals.decide(
        db,
        actors[Role.ADMIN],
        case.id,
        request.id,
        decision=ApprovalDecisionValue.APPROVED,
        comment="Independent fixture review; no financial action.",
    )
    assert (
        decided.status.value == "APPROVED"
        and decided.execution.provider_called is False
    )
    assert decided.requested_by_user_id != decided.decision.decided_by_user_id
    return {
        "evidence_id": str(artifact.id),
        "investigation_id": str(run.id),
        "investigation_status": "COMPLETED",
        "packet_id": str(packet.id),
        "approval_id": str(decided.id),
        "approval_status": "APPROVED",
        "provider_called": False,
    }


if __name__ == "__main__":
    main()
