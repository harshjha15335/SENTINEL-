import ssl
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def database_connect_args(settings: Settings, database_url: str | None = None) -> dict[str, str]:
    """Default hosted policy verifies PostgreSQL encryption and server identity.

    Explicit connect arguments override any weaker sslmode in a provider-issued URL.
    Explicit, separately approved Render internal staging profiles may use
    encrypted-only TLS. No server-identity claim is made. Development loopback
    databases retain their existing configuration.
    """
    if settings.database_tls_policy in (
        "render_internal_staging",
        "render_internal_integrated_staging",
    ):
        return settings.render_internal_database_args(database_url)
    if not settings.hosted_deployment:
        return {}
    root = settings.database_ssl_root_cert or ssl.get_default_verify_paths().cafile
    if root is None:
        try:
            import certifi

            root = certifi.where()
        except ImportError:
            pass
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
