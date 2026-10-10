"""Operational commands.

  python -m app.cli seed        Create the demo merchant, users and catalogue (idempotent).
  python -m app.cli demo-load   Load the synthetic scenario (SYNTHETIC_DEMO) for the demo
                                merchant and score its held-out window. Replaces earlier
                                SYNTHETIC_DEMO rows only.

Passwords come from the environment, never from source:
  SENTINEL_SEED_ADMIN_PASSWORD, SENTINEL_SEED_ANALYST_PASSWORD, SENTINEL_SEED_VIEWER_PASSWORD
"""

import argparse
import os
import sys

from sqlalchemy import select

from app.auth.passwords import hash_password
from app.db.session import get_sessionmaker
from app.models import Merchant, Product, User
from app.models.enums import MerchantEnvironment, Role

DEMO_MERCHANT = "Northwind Supply Co. (sandbox)"
DEMO_PRODUCTS = [
    (
        "NW-API-STARTER",
        "API Starter Plan",
        "Monthly developer plan, digital delivery.",
        1900,
        "USD",
    ),
    ("NW-TEAM", "Team Workspace", "Annual seat bundle for five users.", 24900, "USD"),
    ("NW-HW-KIT", "Field Sensor Kit", "Hardware starter kit (sandbox demo item).", 8950, "USD"),
    ("NW-ENT-AUDIT", "Compliance Audit Pack", "One-off audit engagement deposit.", 120000, "USD"),
]


def seed() -> None:
    users = {
        Role.ADMIN: ("admin@northwind.example", os.environ.get("SENTINEL_SEED_ADMIN_PASSWORD")),
        Role.ANALYST: (
            "analyst@northwind.example",
            os.environ.get("SENTINEL_SEED_ANALYST_PASSWORD"),
        ),
        Role.VIEWER: ("viewer@northwind.example", os.environ.get("SENTINEL_SEED_VIEWER_PASSWORD")),
    }
    if not users[Role.ADMIN][1]:
        sys.exit("SENTINEL_SEED_ADMIN_PASSWORD is required")
    with get_sessionmaker()() as db:
        merchant = db.scalar(select(Merchant).where(Merchant.name == DEMO_MERCHANT))
        if merchant is None:
            merchant = Merchant(name=DEMO_MERCHANT, environment=MerchantEnvironment.SANDBOX)
            db.add(merchant)
            db.flush()
        for role, (email, password) in users.items():
            if not password:
                continue
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                db.add(
                    User(
                        merchant_id=merchant.id,
                        email=email,
                        password_hash=hash_password(password),
                        role=role,
                    )
                )
            else:
                user.password_hash = hash_password(password)
        for sku, name, desc, price, cur in DEMO_PRODUCTS:
            exists = db.scalar(
                select(Product).where(Product.merchant_id == merchant.id, Product.sku == sku)
            )
            if exists is None:
                db.add(
                    Product(
                        merchant_id=merchant.id,
                        sku=sku,
                        name=name,
                        description=desc,
                        price_minor=price,
                        currency=cur,
                    )
                )
        db.commit()
    print(f"Seeded merchant {DEMO_MERCHANT!r}")


def demo_load(seed_value: int) -> None:
    from app.services.demo.loader import load_scenario

    with get_sessionmaker()() as db:
        merchant = db.scalar(select(Merchant).where(Merchant.name == DEMO_MERCHANT))
        if merchant is None:
            sys.exit("Run `python -m app.cli seed` first")
        result = load_scenario(db, merchant.id, seed=seed_value)
    print(
        f"Loaded {result.transactions} SYNTHETIC_DEMO payments; scored {result.scored} "
        f"(bands {result.bands}); opened {result.cases_opened} review cases"
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="sentinel")
    parser.add_argument("command", choices=["seed", "demo-load"])
    parser.add_argument("--seed", type=int, default=2026, help="scenario seed for demo-load")
    args = parser.parse_args()
    if args.command == "seed":
        seed()
    elif args.command == "demo-load":
        demo_load(args.seed)


if __name__ == "__main__":
    main()
