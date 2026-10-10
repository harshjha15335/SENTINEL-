import os

os.environ.setdefault(
    "SENTINEL_DATABASE_URL",
    "postgresql+psycopg://sentinel:sentinel@127.0.0.1:5432/sentinel_test",
)
os.environ["SENTINEL_PAYPAL_MODE"] = "fixture"
os.environ.pop("SENTINEL_PAYPAL_CLIENT_ID", None)
os.environ.pop("SENTINEL_PAYPAL_CLIENT_SECRET", None)
os.environ["SENTINEL_LOGIN_RATE_LIMIT_ATTEMPTS"] = "5"

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


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> Iterator[None]:
    cfg = Config(os.path.join(API_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(API_DIR, "alembic"))
    cfg.attributes["database_url"] = get_settings().database_url
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    from app.api.v1.auth import _limiter

    _limiter.clear()
    yield
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "TRUNCATE case_notes, cases, risk_assessments, audit_events, payment_events, "
                "raw_payloads, transactions, products, user_sessions, users, merchants "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def db() -> Iterator[Session]:
    with get_sessionmaker()() as session:
        yield session


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
    from app.main import app
    from app.services.paypal.factory import get_gateway

    get_gateway.cache_clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client: TestClient, email: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    csrf: str = resp.json()["csrf_token"]
    return csrf
