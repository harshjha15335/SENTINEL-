import os
import tempfile

os.environ.setdefault(
    "SENTINEL_DATABASE_URL",
    "postgresql+psycopg://sentinel:sentinel@127.0.0.1:5432/sentinel_test",
)
os.environ["SENTINEL_PAYPAL_MODE"] = "fixture"
os.environ.pop("SENTINEL_PAYPAL_CLIENT_ID", None)
os.environ.pop("SENTINEL_PAYPAL_CLIENT_SECRET", None)
os.environ["SENTINEL_LOGIN_RATE_LIMIT_ATTEMPTS"] = "5"
# Investigations: never reach a real AI provider from unit tests; store files in a temp dir.
os.environ.pop("SENTINEL_AI_PROVIDER", None)
os.environ.pop("SENTINEL_AI_API_KEY", None)
os.environ.pop("SENTINEL_AI_MODEL", None)
os.environ["SENTINEL_STORAGE_BACKEND"] = "local"
os.environ["SENTINEL_STORAGE_DIR"] = tempfile.mkdtemp(prefix="sentinel-test-")

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import command
from app.auth.passwords import hash_password
from app.core.config import get_settings
from app.db.session import get_engine, get_sessionmaker
from app.models import Merchant, Product, User
from app.models.enums import MerchantEnvironment, Role

PASSWORD = "correct horse battery staple"
API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def require_disposable_database(url: str) -> None:
    """Reject user/hosted databases before destructive test migrations or truncation."""
    from sqlalchemy.engine import make_url

    parsed = make_url(url)
    if (
        parsed.host not in ("127.0.0.1", "localhost")
        or not parsed.database
        or not parsed.database.endswith("_test")
    ):
        raise RuntimeError("Destructive API tests require a loopback database ending in _test")


def emergency_terminate_test_backends(url: str) -> int:
    """Explicitly enabled emergency recovery for isolated test runs only.

    Strict safety invariants:
    - Loopback only (127.0.0.1 / localhost)
    - Database name strictly ending in '_test'
    - Explicit opt-in via SENTINEL_ALLOW_EMERGENCY_BACKEND_TERMINATION=1
    - Scoped strictly to current_database() and owned test usename
    - Never touches unrelated databases, user sessions or hosted instances
    """
    if os.environ.get("SENTINEL_ALLOW_EMERGENCY_BACKEND_TERMINATION") != "1":
        raise RuntimeError("Emergency backend termination is not explicitly enabled.")
    require_disposable_database(url)

    with get_engine().connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("SET lock_timeout = '5s'"))
        res = conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = current_database() "
                "AND usename = current_user "
                "AND pid <> pg_backend_pid()"
            )
        ).fetchall()
        return len(res)


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> Iterator[None]:
    require_disposable_database(get_settings().database_url)
    cfg = Config(os.path.join(API_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(API_DIR, "alembic"))
    cfg.attributes["database_url"] = get_settings().database_url
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    from sqlalchemy.orm import close_all_sessions

    from app.api.v1.auth import _limiter

    _limiter.clear()
    yield
    # Proper lifecycle cleanup: release all sessions and checked-in connections.
    close_all_sessions()
    get_engine().dispose(close=True)
    with get_engine().begin() as conn:
        conn.execute(text("SET lock_timeout = '5s'"))
        conn.execute(
            text(
                "TRUNCATE refund_requests, dispute_drafts, disputes, policy_drafts, "
                "worker_health, risk_scoring_jobs, stored_blobs, "
                "approval_decisions, action_executions, "
                "approval_requests, evidence_packets, evidence_artifacts, investigation_runs, "
                "case_notes, cases, risk_assessments, audit_events, payment_events, "
                "raw_payloads, transactions, products, user_sessions, users, merchants "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def db() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@dataclass
class Tenant:
    merchant: Merchant
    users: dict[Role, User]
    product: Product


def make_tenant(db: Session, name: str) -> Tenant:
    merchant = Merchant(name=name, environment=MerchantEnvironment.SANDBOX)
    db.add(merchant)
    db.flush()
    users = {}
    for role in Role:
        u = User(
            merchant_id=merchant.id,
            email=f"{role.value.lower()}@{name.lower().replace(' ', '')}.example",
            password_hash=hash_password(PASSWORD),
            role=role,
        )
        db.add(u)
        users[role] = u
    product = Product(
        merchant_id=merchant.id, sku="SKU-1", name="Widget", price_minor=2500, currency="USD"
    )
    db.add(product)
    db.commit()
    return Tenant(merchant, users, product)


@pytest.fixture
def tenant(db: Session) -> Tenant:
    return make_tenant(db, "Acme")


@pytest.fixture
def other_tenant(db: Session) -> Tenant:
    return make_tenant(db, "Globex")


@pytest.fixture
def app_client() -> Iterator[TestClient]:
    from sqlalchemy.orm import close_all_sessions

    from app.main import app
    from app.services.paypal.factory import get_gateway

    get_gateway.cache_clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    close_all_sessions()


def login(client: TestClient, email: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    csrf: str = resp.json()["csrf_token"]
    return csrf
