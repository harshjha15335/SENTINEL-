import ssl
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def database_connect_args(settings: Settings) -> dict[str, str]:
    """Hosted connections must verify PostgreSQL encryption and server identity.

    Explicit connect arguments override any weaker sslmode in a provider-issued URL.
    Development loopback databases retain their existing configuration.
    """
    if not settings.hosted_deployment:
        return {}
    root = settings.database_ssl_root_cert or ssl.get_default_verify_paths().cafile
    if root is None or not Path(root).is_file():
        raise RuntimeError("Hosted database requires an available trusted CA bundle")
    return {"sslmode": "verify-full", "sslrootcert": root}


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url, pool_pre_ping=True, connect_args=database_connect_args(settings)
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
