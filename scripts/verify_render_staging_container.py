#!/usr/bin/env python3
"""Fresh-image synthetic staging acceptance. Never creates Render resources or pushes images.

Requires an adequately sized LOCAL Docker engine. Every resource name is unique and
cleanup touches only resources created by this invocation. No provider secrets needed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import uuid
from http.cookies import SimpleCookie
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "dpg-offline-ci-staging-a"


def _execute(args, **kwargs):
    # Never follow an inherited remote Docker endpoint/context during acceptance.
    if args[0] == "docker":
        args = ["docker", "--host=unix:///var/run/docker.sock", *args[1:]]
    environment = dict(os.environ)
    for key in (
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_TLS",
        "DOCKER_TLS_VERIFY",
        "DOCKER_CERT_PATH",
    ):
        environment.pop(key, None)
    return subprocess.run(args, env=environment, **kwargs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    options.output.mkdir(parents=True, exist_ok=True)
    summary = {
        "expectedSha": options.expected_sha,
        "renderDeployment": False,
        "imagePublication": False,
        "scope": "isolated Docker fixture; no Render endpoint or account validation",
    }
    prefix = "sentinel-acceptance-" + uuid.uuid4().hex[:10]
    owned_containers: list[str] = []
    network = volume = built = False
    image = "sentinel-local:" + prefix

    def command(label: str, args: list[str], *, capture: bool = False) -> str:
        result = _execute(args, cwd=ROOT, capture_output=True, text=True, check=False)
        # Logs never contain environment files or credential-bearing command arguments.
        (options.output / (label + ".log")).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(label + " failed; inspect its retained log")
        return result.stdout.strip() if capture else ""

    def envfile(path: Path, values: dict[str, str]) -> None:
        path.write_text("\n".join(k + "=" + v for k, v in values.items()) + "\n")
        path.chmod(0o600)

    try:
        if re.fullmatch(r"[a-f0-9]{40}", options.expected_sha) is None:
            raise RuntimeError("expected-sha must be a full Git SHA")
        head = command("source-sha", ["git", "rev-parse", "HEAD"], capture=True)
        if head != options.expected_sha:
            raise RuntimeError("checkout does not match the exact expected source SHA")
        dirty = command(
            "checkout-status", ["git", "status", "--porcelain"], capture=True
        )
        if dirty:
            raise RuntimeError("acceptance requires a clean committed checkout")
        free = shutil.disk_usage(ROOT).free
        summary["freeWorkspaceBytes"] = free
        if free < 8 * 1024**3:
            raise RuntimeError(
                "fresh Docker acceptance requires at least 8 GiB free workspace storage"
            )
        command("docker-info", ["docker", "info"])
        if (
            _execute(
                ["docker", "image", "inspect", image], capture_output=True
            ).returncode
            == 0
        ):
            raise RuntimeError("refusing to replace a pre-existing image tag")
        command(
            "build",
            [
                "docker",
                "build",
                "--label",
                "org.opencontainers.image.revision=" + head,
                "-t",
                image,
                ".",
            ],
        )
        built = True
        summary["imageId"] = command(
            "image-id",
            ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
            capture=True,
        )
        label = command(
            "image-source",
            [
                "docker",
                "image",
                "inspect",
                image,
                "--format",
                '{{index .Config.Labels "org.opencontainers.image.revision"}}',
            ],
            capture=True,
        )
        if label != head:
            raise RuntimeError("image revision label mismatch")
        command("network", ["docker", "network", "create", "--internal", prefix])
        network = True
        if (
            _execute(
                ["docker", "volume", "inspect", prefix], capture_output=True
            ).returncode
            == 0
        ):
            raise RuntimeError("refusing to reuse a pre-existing volume")
        command(
            "volume",
            [
                "docker",
                "volume",
                "create",
                "--label",
                "sentinel.acceptance.owner=" + prefix,
                prefix,
            ],
        )
        volume = True
        with tempfile.TemporaryDirectory(prefix="sentinel-private-") as temporary:
            private = Path(temporary)
            password = secrets.token_urlsafe(32)
            admin_password = secrets.token_urlsafe(32)
            pg_file = private / "postgres.env"
            envfile(
                pg_file,
                {
                    "POSTGRES_USER": "sentinel_staging",
                    "POSTGRES_PASSWORD": password,
                    "POSTGRES_DB": "sentinel_staging",
                },
            )
            pg = prefix + "-db"
            command(
                "database",
                [
                    "docker",
                    "create",
                    "--name",
                    pg,
                    "--network",
                    prefix,
                    "--network-alias",
                    HOST,
                    "--env-file",
                    str(pg_file),
                    "--mount",
                    "type=volume,src=" + prefix + ",dst=/var/lib/postgresql/data",
                    "postgres:16",
                ],
            )
            owned_containers.append(pg)
            command("database-start", ["docker", "start", pg])
            for _ in range(60):
                result = _execute(
                    ["docker", "exec", pg, "pg_isready", "-U", "sentinel_staging"],
                    capture_output=True,
                )
                if result.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("disposable PostgreSQL did not start")
            command(
                "disable-fixture-tls",
                [
                    "docker",
                    "exec",
                    "-u",
                    "postgres",
                    pg,
                    "psql",
                    "-U",
                    "sentinel_staging",
                    "-d",
                    "sentinel_staging",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    "ALTER SYSTEM SET ssl='off'",
                    "-c",
                    "SELECT pg_reload_conf()",
                ],
            )
            time.sleep(1)
            values = {
                "SENTINEL_DATABASE_URL": f"postgresql://sentinel_staging:{password}@{HOST}/sentinel_staging",
                "SENTINEL_DATABASE_TLS_POLICY": "render_internal_staging",
                "SENTINEL_RENDER_INTERNAL_TLS_REVIEWED_HOST": HOST,
                "SENTINEL_RENDER_PROJECT_ID": "prj-dbq48lon74is739m7nl0",
                "SENTINEL_RENDER_WORKSPACE_ID": "tea-d8gorhflk1mc73f4pmr0",
                "SENTINEL_DEPLOYMENT_STAGE": "staging",
                "SENTINEL_ENVIRONMENT": "production",
                "SENTINEL_HOSTED_DEPLOYMENT": "true",
                "SENTINEL_COOKIE_SECURE": "true",
                "SENTINEL_STORAGE_BACKEND": "database",
                "SENTINEL_CORS_ORIGINS": "[]",
                "SENTINEL_REQUIRE_WORKERS_READY": "true",
                "SENTINEL_FORWARDED_ALLOW_IPS": "127.0.0.1",
                "SENTINEL_PAYPAL_MODE": "fixture",
                "SENTINEL_AI_PROVIDER": "none",
                "SENTINEL_REFUND_EXECUTION_ENABLED": "false",
                "SENTINEL_ALLOW_WEBHOOK_FIXTURES": "false",
                "SENTINEL_AUTO_MIGRATE": "false",
                "SENTINEL_DEMO_AUTOLOAD": "false",
                "PORT": "8000",
            }
            app_file = private / "application.env"
            envfile(app_file, values)
            negative = "from app.db.session import get_engine\nfrom sqlalchemy.exc import OperationalError\ntry:\n get_engine().connect()\nexcept OperationalError as exc:\n if 'does not support SSL' not in str(exc): raise RuntimeError('unexpected negative TLS result') from None\nelse: raise RuntimeError('plaintext fallback accepted')"
            command(
                "reject-no-tls",
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    prefix,
                    "--env-file",
                    str(app_file),
                    image,
                    "python",
                    "-c",
                    negative,
                ],
            )
            # Self-signed server certificate is intentionally NOT a trusted CA.
            command(
                "test-certificate",
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-keyout",
                    str(private / "server.key"),
                    "-out",
                    str(private / "server.crt"),
                    "-days",
                    "1",
                    "-subj",
                    "/CN=untrusted-offline-fixture",
                ],
            )
            for suffix in ["key", "crt"]:
                command(
                    "copy-certificate-" + suffix,
                    [
                        "docker",
                        "cp",
                        str(private / ("server." + suffix)),
                        pg + ":/tmp/server." + suffix,
                    ],
                )
            command(
                "certificate-permissions",
                [
                    "docker",
                    "exec",
                    "-u",
                    "0",
                    pg,
                    "sh",
                    "-c",
                    "chown postgres:postgres /tmp/server.key /tmp/server.crt && chmod 600 /tmp/server.key",
                ],
            )
            psql = [
                "docker",
                "exec",
                "-u",
                "postgres",
                pg,
                "psql",
                "-U",
                "sentinel_staging",
                "-d",
                "sentinel_staging",
                "-v",
                "ON_ERROR_STOP=1",
            ]
            command(
                "enable-test-tls",
                psql
                + [
                    "-c",
                    "ALTER SYSTEM SET ssl='on'",
                    "-c",
                    "ALTER SYSTEM SET ssl_cert_file='/tmp/server.crt'",
                    "-c",
                    "ALTER SYSTEM SET ssl_key_file='/tmp/server.key'",
                    "-c",
                    "SELECT pg_reload_conf()",
                ],
            )
            time.sleep(1)
            strict_file = private / "strict.env"
            envfile(
                strict_file,
                values
                | {
                    "SENTINEL_DATABASE_TLS_POLICY": "verify_full",
                    "SENTINEL_DEPLOYMENT_STAGE": "production",
                },
            )
            strict_negative = negative.replace(
                "does not support SSL", "certificate verify failed"
            )
            command(
                "strict-default-rejects-self-signed",
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    prefix,
                    "--env-file",
                    str(strict_file),
                    image,
                    "python",
                    "-c",
                    strict_negative,
                ],
            )
            seed_file = private / "bootstrap.env"
            envfile(
                seed_file,
                values
                | {
                    "SENTINEL_SEED_ADMIN_PASSWORD": admin_password,
                    "SENTINEL_SEED_ANALYST_PASSWORD": secrets.token_urlsafe(32),
                    "SENTINEL_SEED_VIEWER_PASSWORD": secrets.token_urlsafe(32),
                },
            )
            command(
                "reviewed-migration-and-fixtures",
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    prefix,
                    "--env-file",
                    str(seed_file),
                    image,
                    "sh",
                    "-c",
                    "alembic upgrade d105a4143283 && python -m app.cli check-schema && python -m app.cli seed && python -m app.cli demo-load --if-empty",
                ],
            )
            app = prefix + "-app"
            command(
                "application",
                [
                    "docker",
                    "create",
                    "--name",
                    app,
                    "--network",
                    prefix,
                    "--memory",
                    "2g",
                    "--cpus",
                    "1",
                    "--env-file",
                    str(app_file),
                    "-p",
                    "127.0.0.1::8000",
                    image,
                ],
            )
            owned_containers.append(app)
            command("application-start", ["docker", "start", app])
            port = int(
                command(
                    "application-port",
                    [
                        "docker",
                        "inspect",
                        app,
                        "--format",
                        '{{(index (index .NetworkSettings.Ports "8000/tcp") 0).HostPort}}',
                    ],
                    capture=True,
                )
            )

            def http(path: str, payload: dict | None = None, cookie: str | None = None):
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                headers = {"Content-Type": "application/json"}
                if cookie:
                    headers["Cookie"] = cookie
                connection.request(
                    "POST" if payload else "GET",
                    path,
                    body=json.dumps(payload) if payload else None,
                    headers=headers,
                )
                response = connection.getresponse()
                data = response.read()
                result = (response.status, response.getheaders(), data)
                connection.close()
                return result

            def ready():
                for _ in range(120):
                    try:
                        status, _, data = http("/api/v1/ready")
                        if status == 200:
                            checks = json.loads(data)["checks"]
                            if (
                                checks["pipeline"] != "ok"
                                or checks["supabase_bridge"]
                                != "not_required_fixture_mode"
                                or checks["migration"] != "d105a4143283"
                            ):
                                raise RuntimeError("unexpected readiness contract")
                            return checks
                    except (OSError, http.client.HTTPException):
                        pass
                    time.sleep(1)
                raise RuntimeError("fixture readiness timed out")

            summary["readyChecks"] = ready()
            if b'<div id="root">' not in http("/")[2]:
                raise RuntimeError("compiled React shell not served")
            status, headers, _ = http(
                "/api/v1/auth/login",
                {"email": "admin@northwind.example", "password": admin_password},
            )
            if status != 200:
                raise RuntimeError("fixture login failed")
            cookies = SimpleCookie()
            for key, value in headers:
                if key.lower() == "set-cookie":
                    if "Secure" not in value:
                        raise RuntimeError("hosted secure cookie flag missing")
                    cookies.load(value)
            # Explicit cookie header ONLY over isolated CI loopback; not a public HTTPS claim.
            cookie = "; ".join(
                key + "=" + value.value for key, value in cookies.items()
            )
            status, _, data = http("/api/v1/cases?status=OPEN&limit=1", cookie=cookie)
            if status != 200 or json.loads(data)["total"] != 170:
                raise RuntimeError("fixture review queue mismatch")
            tls = command(
                "database-tls-sessions",
                psql
                + [
                    "-Atc",
                    "SELECT count(*) >= 2 AND bool_and(s.ssl) FROM pg_stat_ssl s JOIN pg_stat_activity a USING(pid) WHERE a.datname=current_database() AND a.client_addr IS NOT NULL",
                ],
                capture=True,
            )
            if tls != "t":
                raise RuntimeError(
                    "required application/worker TLS sessions not observed"
                )
            kill = "import os,signal,pathlib; pids=[]\nfor path in pathlib.Path('/proc').iterdir():\n try:\n  if path.name.isdigit() and b'app.workers.pipeline' in (path/'cmdline').read_bytes().split(b'\\0'): pids.append(int(path.name))\n except (OSError,PermissionError): pass\nassert len(pids)==1; os.kill(pids[0],signal.SIGKILL)"
            command("pipeline-crash", ["docker", "exec", app, "python", "-c", kill])
            seen_failure = False
            for _ in range(100):
                status, _, _ = http("/api/v1/ready")
                seen_failure |= status == 503
                if seen_failure and status == 200:
                    break
                time.sleep(0.1)
            if not seen_failure:
                raise RuntimeError("pipeline crash did not invalidate readiness")
            ready()
            command("graceful-stop", ["docker", "stop", "-t", "25", app])
            stopped = command(
                "worker-stopped",
                psql
                + ["-Atc", "SELECT status FROM worker_health WHERE name='pipeline'"],
                capture=True,
            )
            if stopped != "STOPPED":
                raise RuntimeError("graceful worker status mismatch")
            command("restart", ["docker", "start", app])
            ready()
            source_hash = command(
                "built-source-fingerprint",
                [
                    "docker",
                    "exec",
                    app,
                    "python",
                    "-c",
                    "import hashlib;print(hashlib.sha256(open('/app/app/core/config.py','rb').read()).hexdigest())",
                ],
                capture=True,
            )
            if (
                source_hash
                != hashlib.sha256(
                    (ROOT / "apps/api/app/core/config.py").read_bytes()
                ).hexdigest()
            ):
                raise RuntimeError("built source fingerprint mismatch")
            summary.update(
                passed=True,
                tlsRequired=True,
                plaintextRejected=True,
                strictDefaultPreserved=True,
                migrationAndWorkersVerified=True,
                crashRecovery=True,
                restart=True,
            )
    except Exception as error:
        summary.update(
            passed=False, failureType=type(error).__name__, failure=str(error)
        )
    finally:
        for name in reversed(owned_containers):
            logs = _execute(["docker", "logs", name], capture_output=True, text=True)
            (options.output / (name + ".log")).write_text(logs.stdout + logs.stderr)
            _execute(["docker", "rm", "-f", name], capture_output=True)
        if volume:
            _execute(["docker", "volume", "rm", prefix], capture_output=True)
        if network:
            _execute(["docker", "network", "rm", prefix], capture_output=True)
        if built:
            _execute(["docker", "image", "rm", image], capture_output=True)
        (options.output / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n"
        )
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
