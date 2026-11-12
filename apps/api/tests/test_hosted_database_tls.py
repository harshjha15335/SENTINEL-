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


@pytest.mark.parametrize(
    "sslmode", ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
)
def test_hosted_url_cannot_downgrade_tls_or_redirect_host(sslmode):
    from sqlalchemy.engine import make_url

    settings = hosted(
        database_url=f"postgresql://test:offline@dpg-reviewed-a.singapore-postgres.render.com/staging?sslmode={sslmode}"
    )
    args = session.database_connect_args(settings)
    assert args["sslmode"] == "verify-full"
    assert make_url(settings.database_url).host == "dpg-reviewed-a.singapore-postgres.render.com"
    assert args["sslrootcert"]


@pytest.mark.parametrize("failure", ["wrong_hostname", "wrong_ca"])
def test_real_tls_rejects_wrong_hostname_and_untrusted_ca(tmp_path, failure):
    import ssl
    from datetime import UTC, datetime, timedelta

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = tmp_path / "server.pem", tmp_path / "server.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    received = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(5)

        def serve():
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(5)
                received.append(connection.recv(8))
                connection.sendall(b"S")
                try:
                    with context.wrap_socket(connection, server_side=True) as secure:
                        secure.recv(1)
                except (ssl.SSLError, OSError):
                    pass

        thread = threading.Thread(target=serve)
        thread.start()
        # Address is loopback in both cases; DNS/SAN hostname check is real.
        host = "127.0.0.1" if failure == "wrong_hostname" else "localhost"
        ca = (
            str(cert_path) if failure == "wrong_hostname" else ssl.get_default_verify_paths().cafile
        )
        settings = hosted(
            database_url=f"postgresql+psycopg://offline:fake@{host}:{listener.getsockname()[1]}/unused_test",
            database_ssl_root_cert=ca,
        )
        engine = session.create_engine(
            settings.database_url, connect_args=session.database_connect_args(settings)
        )
        try:
            with pytest.raises(OperationalError, match=r"does not match|certificate verify failed"):
                engine.connect()
        finally:
            engine.dispose()
            thread.join(timeout=6)
    assert not thread.is_alive()
    assert received == [struct.pack("!II", 8, 80877103)]
