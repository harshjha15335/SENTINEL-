#!/usr/bin/env python3
"""Bounded local capacity drill; isolated databases and an explicitly mocked inbox bridge.

Never uses the real Supabase URL/key, payment provider or paid AI. Browser processes
run outside the measured application cgroup, as they would on users' devices.
"""

import argparse
import json
import os
import secrets
import statistics
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import psycopg
from psycopg.conninfo import conninfo_to_dict

ROOT = Path(__file__).resolve().parents[1]
HOOK = """import sys
if 'app.workers.supabase_inbox' in sys.orig_argv:
    import httpx
    Original = httpx.Client
    def fixture(request):
        if request.url.host != 'profile-fixture.supabase.co':
            raise AssertionError('Profile bridge may not contact any real service')
        if request.url.path not in ('/rest/v1/rpc/sentinel_claim_webhooks', '/rest/v1/rpc/sentinel_webhook_metrics'):
            raise AssertionError('Unexpected profile fixture RPC')
        return httpx.Response(200, json=[])
    class ProfileClient(Original):
        def __init__(self, *args, **kwargs):
            kwargs['transport'] = httpx.MockTransport(fixture)
            super().__init__(*args, **kwargs)
    httpx.Client = ProfileClient
"""
BROWSER = """const {chromium}=require(process.env.PROFILE_PLAYWRIGHT);
(async()=>{const b=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_PATH||'/usr/bin/chromium',headless:true});
try { const results=await Promise.all(Array.from({length:4},async()=>{const c=await b.newContext({baseURL:process.env.PROFILE_BASE,viewport:{width:1440,height:900}}); const p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));await p.goto('/login');await p.getByLabel('Work email').fill('judge@sentinel-demo.example');await p.getByLabel('Password').fill(process.env.PROFILE_PASSWORD);await p.getByRole('button',{name:'Sign in',exact:true}).click();await p.getByRole('heading',{name:'Command Center'}).waitFor();const times=[];for(const route of ['/transactions','/policy','/network','/monitoring','/demo']){const t=Date.now();await p.goto(route);await p.locator('main').waitFor();await p.waitForFunction(()=>document.querySelectorAll('.animate-pulse').length===0);times.push({route,ms:Date.now()-t});}await c.close();return {times,errors};}));console.log(JSON.stringify(results));if(results.some(r=>r.errors.length))process.exitCode=1;}finally{await b.close();}})().catch(e=>{console.error(e.name);process.exit(1)});
"""
SCORE = """from datetime import UTC, datetime
import uuid
from sqlalchemy import select
from app.db.session import get_sessionmaker
from app.models import Merchant, Transaction
from app.models.enums import DataOrigin, TransactionStatus
from app.services.risk.jobs import enqueue
with get_sessionmaker()() as db:
    merchant=db.scalar(select(Merchant).where(Merchant.name=='SENTINEL isolated judge demo'))
    for i in range(24):
        row=Transaction(merchant_id=merchant.id,quantity=1,amount_minor=5000+i,currency='USD',status=TransactionStatus.CAPTURED,payer_reference='PROFILE-PAYER',data_origin=DataOrigin.SIMULATED,occurred_at=datetime.now(UTC),create_idempotency_key=str(uuid.uuid4()),paypal_request_id=str(uuid.uuid4()),provider_summary={})
        db.add(row);db.flush();enqueue(db,row.id)
    db.commit()
"""


def run(command, **kwargs):
    return subprocess.run(command, check=True, capture_output=True, text=True, **kwargs)


def percentile(values, fraction):
    return (
        sorted(values)[max(0, int(len(values) * fraction + 0.999) - 1)]
        if values
        else None
    )


def profile(image, memory, output):
    suffix = secrets.token_hex(4)
    database, name = f"sentinel_profile_{suffix}_test", f"sentinel-profile-{suffix}"
    admin, judge = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    private = output / ("private-" + suffix)
    private.mkdir(mode=0o700)
    hooks = private / "hooks"
    hooks.mkdir(mode=0o755)
    hooks.chmod(
        0o755
    )  # umask077 must not make the read-only fixture mount inaccessible to UID10001
    (hooks / "sitecustomize.py").write_text(HOOK)
    (hooks / "sitecustomize.py").chmod(0o644)
    (private / "browser.cjs").write_text(BROWSER)
    profile_pg = os.environ.get(
        "SENTINEL_PROFILE_POSTGRES_URL",
        "postgresql://sentinel:sentinel@127.0.0.1:5432/postgres",
    )
    params = conninfo_to_dict(profile_pg)
    if params.get("host") not in ("127.0.0.1", "localhost"):
        raise SystemExit("Profiling requires an existing loopback PostgreSQL server")
    with psycopg.connect(profile_pg, autocommit=True) as db:
        db.execute(
            psycopg.sql.SQL("create database {}").format(
                psycopg.sql.Identifier(database)
            )
        )
    params["dbname"] = database
    db_url = psycopg.conninfo.make_conninfo(**params)
    # SQLAlchemy expects a URL. This local fixture follows the existing loopback compose setup.
    from sqlalchemy.engine import URL

    app_url = URL.create(
        "postgresql+psycopg",
        username=params.get("user"),
        password=params.get("password"),
        host=params["host"],
        port=int(params.get("port", 5432)),
        database=database,
        query={
            k: v
            for k, v in params.items()
            if k not in {"dbname", "user", "password", "host", "port"}
        },
    ).render_as_string(hide_password=False)
    config = private / "runtime.env"
    config.write_text(
        "\n".join(
            [
                "SENTINEL_DATABASE_URL=" + app_url,
                "SENTINEL_ENVIRONMENT=test",
                "SENTINEL_PAYPAL_MODE=fixture",
                "SENTINEL_AI_PROVIDER=none",
                "SENTINEL_STORAGE_BACKEND=database",
                "SENTINEL_AUTO_MIGRATE=true",
                "SENTINEL_MIGRATION_TARGET=d105a4143283",
                "SENTINEL_DEMO_AUTOLOAD=true",
                "SENTINEL_REQUIRE_WORKERS_READY=true",
                "SENTINEL_SEED_ADMIN_PASSWORD=" + admin,
                "SENTINEL_SEED_ANALYST_PASSWORD=" + secrets.token_urlsafe(32),
                "SENTINEL_SEED_VIEWER_PASSWORD=" + secrets.token_urlsafe(32),
                "SENTINEL_JUDGE_PASSWORD=" + judge,
                "SENTINEL_SUPABASE_URL=https://profile-fixture.supabase.co",
                "SENTINEL_SUPABASE_SERVICE_ROLE_KEY=LOCAL_PROFILE_DUMMY_NOT_A_REAL_KEY",
                "PYTHONPATH=/profile-hooks:/app",
                "HOST=127.0.0.1",
                "PORT=8050",
            ]
        )
        + "\n"
    )
    config.chmod(0o600)
    samples, sampling_errors = [], []
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            try:
                result = run(
                    [
                        "docker",
                        "exec",
                        name,
                        "sh",
                        "-c",
                        "cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.peak /sys/fs/cgroup/memory.max; cat /sys/fs/cgroup/cpu.stat",
                    ]
                )
                lines = result.stdout.splitlines()
                stats = dict(line.split() for line in lines[3:])
                with psycopg.connect(db_url) as db:
                    connections = db.execute(
                        "select count(*) from pg_stat_activity where datname=current_database()"
                    ).fetchone()[0]
                    workers = db.execute(
                        "select name,status,extract(epoch from now()-heartbeat_at) from worker_health"
                    ).fetchall()
                samples.append(
                    {
                        "t": time.monotonic(),
                        "memory_current": int(lines[0]),
                        "memory_peak": int(lines[1]),
                        "memory_limit": lines[2],
                        "cpu_usage_usec": int(stats["usage_usec"]),
                        "connections_including_probe": connections,
                        "workers": [
                            {"name": a, "status": b, "age_seconds": float(c)}
                            for a, b, c in workers
                        ],
                    }
                )
            except Exception as exc:
                sampling_errors.append(type(exc).__name__)
            stop.wait(0.5)

    started = time.monotonic()
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--network",
            "host",
            "--memory",
            f"{memory}g",
            "--memory-swap",
            f"{memory}g",
            "--cpus",
            "1",
            "--env-file",
            str(config),
            "--mount",
            f"type=bind,src={hooks},dst=/profile-hooks,readonly",
            image,
            "sh",
            "-c",
            "python -c \"import sys,sitecustomize,importlib; sys.orig_argv=['python','-m','app.workers.supabase_inbox']; importlib.reload(sitecustomize); import httpx; assert httpx.Client.__module__=='sitecustomize'\" && exec ./start.sh",
        ]
    )
    monitor = threading.Thread(target=sample)
    monitor.start()
    try:
        client = httpx.Client(base_url="http://127.0.0.1:8050", timeout=60)
        for _ in range(180):
            try:
                if client.get("/api/v1/ready").status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Profile startup did not become ready")
        startup_seconds = time.monotonic() - started
        startup_peak = max(s["memory_peak"] for s in samples) if samples else None
        run(
            ["docker", "exec", name, "python", "-m", "app.cli", "judge-demo", "--fresh"]
        )
        auth = client.post(
            "/api/v1/auth/login",
            json={"email": "judge@sentinel-demo.example", "password": judge},
        )
        assert auth.status_code == 200
        scenario = client.get("/api/v1/demo/scenario").json()
        case_id = scenario["case_id"]
        ev = client.get(f"/api/v1/cases/{case_id}/evidence").json()["items"][0]["id"]
        packet = client.get(f"/api/v1/cases/{case_id}/packets").json()[0]["id"]
        steady = client.get("/api/v1/ready")
        assert steady.status_code == 200
        time.sleep(2)
        steady_memory = statistics.median(s["memory_current"] for s in samples[-4:])
        load_start = time.monotonic()
        run(["docker", "exec", name, "python", "-c", SCORE])
        routes = [
            "/",
            "/assets/",
            "/api/v1/dashboard/summary",
            "/api/v1/transactions",
            "/api/v1/policy-lab/simulate",
            "/api/v1/network?data_origin=SYNTHETIC_DEMO",
            "/api/v1/monitoring/risk?data_origin=SYNTHETIC_DEMO",
            f"/api/v1/cases/{case_id}",
            f"/api/v1/cases/{case_id}/evidence/{ev}/download",
            f"/api/v1/cases/{case_id}/packets/{packet}/download",
        ]
        # Discover a real built asset rather than measuring a nonexistent directory.
        import re

        asset = re.search(r'src="([^"]+\.js)"', client.get("/").text)
        assert asset
        routes[1] = asset.group(1)
        results = []

        def request(path):
            t = time.monotonic()
            response = client.get(path)
            return {
                "path": path,
                "status": response.status_code,
                "ms": (time.monotonic() - t) * 1000,
            }

        with ThreadPoolExecutor(max_workers=4) as pool:
            results.extend(pool.map(request, ["/api/v1/policy-lab/simulate"] * 4))
        with ThreadPoolExecutor(max_workers=8) as pool:
            results.extend(pool.map(request, routes * 8))
        env = os.environ.copy()
        env.update(
            PROFILE_BASE="http://127.0.0.1:8050",
            PROFILE_PASSWORD=judge,
            PROFILE_PLAYWRIGHT=str(ROOT / "apps/web/node_modules/@playwright/test"),
        )
        browser = run(["node", str(private / "browser.cjs")], env=env, timeout=180)
        browser_results = json.loads(browser.stdout)
        load_seconds = time.monotonic() - load_start
        for _ in range(60):
            with psycopg.connect(db_url) as db:
                jobs = db.execute(
                    "select status,count(*) from risk_scoring_jobs group by status"
                ).fetchall()
            if sum(count for status, count in jobs if status == "COMPLETED") == 24:
                break
            time.sleep(0.5)
        assert sum(count for status, count in jobs if status == "COMPLETED") == 24
        final = client.get("/api/v1/ready")
        assert final.status_code == 200
        events = run(
            ["docker", "exec", name, "cat", "/sys/fs/cgroup/memory.events"]
        ).stdout
        event_counts = {
            k: int(v) for k, v in (line.split() for line in events.splitlines())
        }
        assert event_counts.get("oom_kill", 0) == 0
        assert all(row["status"] == 200 for row in results), [
            (x["path"], x["status"]) for x in results if x["status"] != 200
        ]
        assert samples and all(
            s["memory_limit"] == str(memory * 1024**3) for s in samples
        )
        with psycopg.connect(db_url) as db:
            sizing = db.execute(
                "select pg_database_size(current_database()),(select count(*) from transactions),(select coalesce(sum(octet_length(body)),0) from stored_blobs)"
            ).fetchone()
        durations = [x["ms"] for x in results]
        elapsed = samples[-1]["t"] - samples[0]["t"]
        load_samples = [s for s in samples if s["t"] >= load_start]
        stable_workers = all(
            {w["name"] for w in s["workers"]} >= {"pipeline", "supabase_bridge"}
            and all(
                w["status"] == "HEALTHY" and -1 <= w["age_seconds"] < 45
                for w in s["workers"]
            )
            for s in load_samples
        )
        assert load_samples and stable_workers
        cpu_peak = max(
            (b["cpu_usage_usec"] - a["cpu_usage_usec"]) / 1e6 / (b["t"] - a["t"])
            for a, b in zip(samples, samples[1:])
        )
        report = {
            "image": image,
            "candidate_memory_gib": memory,
            "cpu_limit_cores": 1,
            "startup_seconds": startup_seconds,
            "startup_peak_bytes": startup_peak,
            "steady_sample_bytes": steady_memory,
            "load_peak_sample_bytes": max(s["memory_current"] for s in load_samples),
            "worker_heartbeats_stable_during_load": stable_workers,
            "cpu_peak_cores_approx": cpu_peak,
            "peak_bytes": max(s["memory_peak"] for s in samples),
            "samples": len(samples),
            "sampling_error_categories": sorted(set(sampling_errors)),
            "cpu_average_cores": (
                samples[-1]["cpu_usage_usec"] - samples[0]["cpu_usage_usec"]
            )
            / 1e6
            / elapsed,
            "database_max_connections_including_probe": max(
                s["connections_including_probe"] for s in samples
            ),
            "database_size_bytes": sizing[0],
            "transaction_rows": sizing[1],
            "evidence_bytes": sizing[2],
            "http_requests": len(results),
            "http_failures": 0,
            "http_p50_ms": percentile(durations, 0.5),
            "http_p95_ms": percentile(durations, 0.95),
            "http_max_ms": max(durations),
            "load_seconds": load_seconds,
            "browser_contexts": 4,
            "browser_routes_per_context": 5,
            "browser_errors": sum(len(r["errors"]) for r in browser_results),
            "scoring_jobs_completed": 24,
            "memory_events": event_counts,
            "final_readiness": final.json(),
            "bridge": "mock RPC transport in isolated child; no real Supabase key or remote inbox traffic",
            "scope": "bounded local synthetic workload, not a production capacity guarantee or a Render plan quote",
        }
        (output / f"profile-{memory}g.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        (private / "samples.json").write_text(json.dumps(samples))
        (private / "http-results.json").write_text(json.dumps(results))
        (private / "browser-results.json").write_text(json.dumps(browser_results))
        return report
    finally:
        stop.set()
        monitor.join(timeout=10)
        (private / "samples.json").write_text(json.dumps(samples))
        log = subprocess.run(["docker", "logs", name], capture_output=True)
        (private / "container.log").write_bytes(log.stdout + log.stderr)
        subprocess.run(["docker", "stop", "--time", "20", name], capture_output=True)
        subprocess.run(["docker", "rm", name], capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-local-profile", action="store_true")
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--memory-gib", nargs="+", type=int, choices=[2, 4], default=[2, 4]
    )
    args = parser.parse_args()
    if not args.allow_local_profile:
        parser.error("Explicit --allow-local-profile required")
    args.output.mkdir(parents=True, mode=0o700, exist_ok=True)
    failures = []
    for memory in args.memory_gib:
        try:
            print(json.dumps(profile(args.image, memory, args.output)), flush=True)
        except Exception as exc:
            failures.append(
                {
                    "memory_gib": memory,
                    "error_type": type(exc).__name__,
                    "status": "FAILED; inspect private container logs and samples",
                }
            )
            (args.output / "failed-candidates.json").write_text(
                json.dumps(failures, indent=2)
            )
            print(json.dumps(failures[-1]), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
