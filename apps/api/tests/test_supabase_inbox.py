"""Full local lifecycle: real PostgreSQL inbox RPCs, FastAPI, jobs and unchanged model."""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import psycopg
import pytest
from psycopg.rows import dict_row
from pydantic import SecretStr
from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models import Case, PaymentEvent, RawPayload, RiskAssessment, RiskScoringJob, Transaction
from app.models.enums import DataOrigin, TransactionStatus
from app.services.inbox_bridge import DeliveryDeferred, poll_once
from app.services.risk.jobs import run_once as score_once
from tests.test_risk_cases import T0, _txn

FIXTURE_KEY = "isolated-fixture-test-key"
HEADERS = {
    "paypal-transmission-id": "FIXTURE-TRANSMISSION",
    "paypal-transmission-sig": "FIXTURE_ONLY",
}


@pytest.fixture(scope="module")
def inbox_url():
    import pathlib

    from psycopg.conninfo import conninfo_to_dict

    args = conninfo_to_dict(get_settings().database_url.replace("+psycopg", ""))
    assert args["dbname"].endswith("_test")
    with psycopg.connect(**args, autocommit=True) as admin:
        if not admin.execute(
            "select 1 from pg_database where datname='sentinel_inbox_test'"
        ).fetchone():
            admin.execute("create database sentinel_inbox_test")
        for role in ["anon", "authenticated", "service_role"]:
            if not admin.execute("select 1 from pg_roles where rolname=%s", (role,)).fetchone():
                admin.execute(
                    "create role " + role + (" bypassrls" if role == "service_role" else "")
                )
    args["dbname"] = "sentinel_inbox_test"
    with psycopg.connect(**args, autocommit=True) as conn:
        for path in sorted(
            pathlib.Path(__file__).parents[3].joinpath("supabase/migrations").glob("*.sql")
        ):
            conn.execute(path.read_text())
    return args


@pytest.fixture
def inbox(inbox_url):
    with psycopg.connect(**inbox_url, autocommit=True, row_factory=dict_row) as conn:
        conn.execute("truncate public.sentinel_webhook_inbox")
        yield conn


@pytest.fixture
def fixture_api(app_client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(settings, "allow_webhook_fixtures", True)
    monkeypatch.setattr(settings, "webhook_fixture_key", SecretStr(FIXTURE_KEY))
    return app_client


def enqueue(inbox, body, event_type="PAYMENT.CAPTURE.COMPLETED"):
    return inbox.execute(
        "select public.sentinel_enqueue_fixture(%s,%s,%s,%s) as inserted",
        (json.loads(body)["id"], event_type, body, json.dumps(HEADERS)),
    ).fetchone()["inserted"]


def event(txn, event_type="PAYMENT.CAPTURE.COMPLETED"):
    return json.dumps(
        {
            "id": "FIXTURE-" + str(uuid.uuid4()),
            "event_type": event_type,
            "create_time": T0.isoformat(),
            "resource": {
                "id": "SIM-CAPTURE-" + str(txn.id),
                "amount": {"value": "5000.00", "currency_code": "USD"},
                "supplementary_data": {"related_ids": {"order_id": txn.paypal_order_id}},
            },
        },
        separators=(",", ":"),
    )


def high_candidate(db, tenant):
    for i in range(20):
        history = _txn(
            db,
            tenant,
            at=T0 - timedelta(minutes=i + 1),
            amount=1000,
            payer="FIXTURE-PAYER",
            origin=DataOrigin.SIMULATED,
        )
        history.refunded_at = T0 - timedelta(minutes=i)
    txn = _txn(db, tenant, at=T0, amount=500000, payer="FIXTURE-PAYER", origin=DataOrigin.SIMULATED)
    txn.status, txn.occurred_at = TransactionStatus.ORDER_CREATED, None
    txn.paypal_order_id = "SIM-FIXTURE-ORDER-" + str(txn.id)
    db.commit()
    return txn


class Rpc:
    def __init__(self, inbox):
        self.inbox, self.fail_ack, self.expire_renew = inbox, False, False

    def __call__(self, request):
        name = request.url.path.rsplit("/", 1)[-1]
        data = json.loads(request.content)
        if name == "sentinel_claim_webhooks":
            rows = self.inbox.execute(
                "select * from public.sentinel_claim_webhooks(%s,%s)",
                (data["p_limit"], data["p_origin"]),
            ).fetchall()
            return httpx.Response(200, json=json.loads(json.dumps(rows, default=str)))
        if name == "sentinel_renew_webhook":
            if self.expire_renew:
                self.inbox.execute(
                    "update public.sentinel_webhook_inbox "
                    "set available_at=now()-interval '1 second'"
                )
            result = self.inbox.execute(
                "select public.sentinel_renew_webhook(%s,%s) as done",
                (data["p_id"], data["p_lease_token"]),
            ).fetchone()["done"]
        else:
            assert name == "sentinel_finish_webhook"
            if self.fail_ack:
                self.fail_ack = False
                raise httpx.ReadTimeout("acknowledgement lost before commit")
            result = self.inbox.execute(
                "select public.sentinel_finish_webhook(%s,%s,%s,%s) as done",
                (data["p_id"], data["p_lease_token"], data["p_success"], data["p_error"]),
            ).fetchone()["done"]
        return httpx.Response(200, json=result)

    def client(self):
        return httpx.Client(
            base_url="https://example.supabase.co/rest/v1/rpc/", transport=httpx.MockTransport(self)
        )


def forward(inbox, api, rpc=None, key=FIXTURE_KEY):
    rpc = rpc or Rpc(inbox)
    with rpc.client() as client:
        return poll_once(client, api, fixtures=True, fixture_key=key)


def test_complete_pipeline_and_duplicates_use_unchanged_model(db, tenant, inbox, fixture_api):
    txn = high_candidate(db, tenant)
    body = event(txn)
    assert enqueue(inbox, body) is True
    assert enqueue(inbox, body) is False
    assert forward(inbox, fixture_api) == 1
    # A separate connection sees durable acceptance before Supabase acknowledgement.
    with get_sessionmaker()() as check:
        stored = check.scalar(select(PaymentEvent))
        assert stored.data_origin is DataOrigin.SIMULATED
        assert stored.verification_status.value == "FIXTURE"
        assert stored.payload_sha256 == hashlib.sha256(body.encode()).hexdigest()
        assert stored.signature_headers == HEADERS
        assert check.get(RawPayload, stored.payload_reference).body == body.encode()
        assert check.scalar(select(func.count()).select_from(RiskScoringJob)) == 1
    assert score_once() == 1
    assert score_once() == 0
    db.expire_all()
    assert db.get(Transaction, txn.id).status is TransactionStatus.CAPTURED
    assessment = db.scalar(select(RiskAssessment))
    assert assessment.risk_band.value == "HIGH"
    assert assessment.risk_score == pytest.approx(0.28208108438987056)
    assert assessment.data_origin is DataOrigin.SIMULATED
    assert db.scalar(select(func.count()).select_from(Case)) == 1
    assert enqueue(inbox, body) is False
    assert forward(inbox, fixture_api) == 0
    row = inbox.execute("select * from public.sentinel_webhook_inbox").fetchone()
    assert row["status"] == "PROCESSED" and row["processed_at"] is not None


def test_lost_ack_and_crashed_claim_recover_without_duplicate_effects(
    db, tenant, inbox, fixture_api
):
    txn = high_candidate(db, tenant)
    body = event(txn)
    enqueue(inbox, body)
    rpc = Rpc(inbox)
    rpc.fail_ack = True
    with pytest.raises(httpx.ReadTimeout):
        forward(inbox, fixture_api, rpc)
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 1
    stale = inbox.execute("select id,lease_token from public.sentinel_webhook_inbox").fetchone()
    inbox.execute("update public.sentinel_webhook_inbox set available_at=now()-interval '1 second'")
    assert forward(inbox, fixture_api) == 1
    assert (
        inbox.execute(
            "select public.sentinel_finish_webhook(%s,%s,true) as done",
            (stale["id"], stale["lease_token"]),
        ).fetchone()["done"]
        is False
    )
    assert score_once() == 1
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 1
    assert db.scalar(select(func.count()).select_from(RiskScoringJob)) == 1
    assert db.scalar(select(func.count()).select_from(Case)) == 1


def test_api_unavailable_retries_without_processed_ack(db, tenant, inbox, fixture_api):
    enqueue(inbox, event(high_candidate(db, tenant)))

    def unavailable(request):
        raise httpx.ConnectError("API unavailable")

    with (
        httpx.Client(
            base_url="http://localhost", transport=httpx.MockTransport(unavailable)
        ) as api,
        pytest.raises(DeliveryDeferred),
    ):
        forward(inbox, api)
    row = inbox.execute("select * from public.sentinel_webhook_inbox").fetchone()
    assert row["status"] == "PENDING" and row["processed_at"] is None
    assert row["available_at"] > datetime.now(UTC)
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0
    inbox.execute("update public.sentinel_webhook_inbox set available_at=now()-interval '1 second'")
    assert forward(inbox, fixture_api) == 1


def test_invalid_fixture_signature_is_terminal_and_never_persists(db, tenant, inbox, fixture_api):
    enqueue(inbox, event(high_candidate(db, tenant)))
    assert forward(inbox, fixture_api, key="wrong-fixture-key") == 0
    row = inbox.execute("select * from public.sentinel_webhook_inbox").fetchone()
    assert row["status"] == "DEAD" and row["processed_at"] is None
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0


def test_expired_lease_prevents_forwarding(db, tenant, inbox, fixture_api):
    enqueue(inbox, event(high_candidate(db, tenant)))
    rpc = Rpc(inbox)
    rpc.expire_renew = True
    assert forward(inbox, fixture_api, rpc) == 0
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0
    assert forward(inbox, fixture_api) == 1


def test_out_of_order_pending_does_not_regress_or_rescore(db, tenant, inbox, fixture_api):
    txn = high_candidate(db, tenant)
    enqueue(inbox, event(txn))
    forward(inbox, fixture_api)
    score_once()
    enqueue(inbox, event(txn, "PAYMENT.CAPTURE.PENDING"), "PAYMENT.CAPTURE.PENDING")
    forward(inbox, fixture_api)
    db.expire_all()
    assert db.get(Transaction, txn.id).status is TransactionStatus.CAPTURED
    assert score_once() == 0
    assert db.scalar(select(func.count()).select_from(RiskAssessment)) == 1
    assert db.scalar(select(func.count()).select_from(Case)) == 1


def test_attempted_http_200_without_durable_receipt_is_not_acknowledged(db, tenant, inbox):
    enqueue(inbox, event(high_candidate(db, tenant)))
    with (
        httpx.Client(
            base_url="http://localhost",
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"received": True})),
        ) as api,
        pytest.raises(DeliveryDeferred),
    ):
        forward(inbox, api)
    row = inbox.execute("select * from public.sentinel_webhook_inbox").fetchone()
    assert row["processed_at"] is None and row["status"] == "PENDING"


def test_fixture_ingress_is_disabled_by_default(app_client, db, tenant, monkeypatch):
    monkeypatch.setattr(get_settings(), "allow_webhook_fixtures", False)
    assert (
        app_client.post(
            "/api/v1/webhooks/fixtures/paypal", content=event(high_candidate(db, tenant))
        ).status_code
        == 404
    )


def test_lost_http_response_after_api_commit_replays_safely(db, tenant, inbox, fixture_api):
    enqueue(inbox, event(high_candidate(db, tenant)))

    def accept_then_lose_response(request):
        response = fixture_api.post(
            request.url.path, content=request.content, headers=dict(request.headers)
        )
        assert response.status_code == 200 and response.json()["durable"] is True
        raise httpx.ReadTimeout("API committed; response lost in transport")

    with (
        httpx.Client(
            base_url="http://localhost", transport=httpx.MockTransport(accept_then_lose_response)
        ) as api,
        pytest.raises(DeliveryDeferred),
    ):
        forward(inbox, api)
    row = inbox.execute("select * from public.sentinel_webhook_inbox").fetchone()
    assert row["status"] == "PENDING" and row["processed_at"] is None
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 1
    inbox.execute("update public.sentinel_webhook_inbox set available_at=now()-interval '1 second'")
    assert forward(inbox, fixture_api) == 1
    assert score_once() == 1
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 1
    assert db.scalar(select(func.count()).select_from(RiskScoringJob)) == 1
    assert db.scalar(select(func.count()).select_from(Case)) == 1
