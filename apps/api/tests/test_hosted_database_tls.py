import socket
import struct
import threading

import pytest
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.db import session


def hosted(**values):
    return Settings(
        _env_file=None,
        hosted_deployment=True,
        environment="production",
        cookie_secure=True,
        storage_backend="database",
        require_workers_ready=True,
        cors_origins=[],
        **values,
    )


def test_hosted_engine_overrides_weaker_url_and_fails_before_password_auth(monkeypatch):
    received = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(5)

        def refuse_tls():
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(5)
                received.append(connection.recv(8))
                connection.sendall(b"N")

        server = threading.Thread(target=refuse_tls)
        server.start()
        settings = hosted(
            database_url=f"postgresql+psycopg://fixture:private-test-password@127.0.0.1:{listener.getsockname()[1]}/unused_test?sslmode=disable"
        )
        monkeypatch.setattr(session, "get_settings", lambda: settings)
        engine = session.get_engine.__wrapped__()
        try:
            with pytest.raises(OperationalError, match="does not support SSL"):
                engine.connect()
        finally:
            engine.dispose()
            server.join(timeout=6)
    assert received == [struct.pack("!II", 8, 80877103)]


def test_hosted_ca_must_exist_and_explicit_bundle_is_selected(tmp_path):
    missing = tmp_path / "missing.pem"
    with pytest.raises(RuntimeError, match="trusted CA bundle"):
        session.database_connect_args(hosted(database_ssl_root_cert=str(missing)))
    cert = tmp_path / "operator-ca.pem"
    cert.write_text("test placeholder; TLS library will validate actual certificate contents")
    assert session.database_connect_args(hosted(database_ssl_root_cert=str(cert))) == {
        "sslmode": "verify-full",
        "sslrootcert": str(cert),
    }


def test_development_database_behavior_unchanged():
    assert session.database_connect_args(Settings(_env_file=None, hosted_deployment=False)) == {}
