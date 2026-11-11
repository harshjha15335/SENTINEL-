"""Recover durable jobs with one active worker and interruptible rollout standby."""

import argparse
import signal
from threading import Event

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_engine
from app.services.risk.jobs import run_once as score_once
from app.services.worker_health import heartbeat
from app.workers.events import run_once as events_once

LOCK_ID = 7682346


def acquire_lock(lock: Connection, stopping: Event, *, once: bool) -> bool:
    """A healthy old process may own the lock throughout an overlapping rollout.

    Standby must not consume supervisor crash retries or overwrite the active
    worker heartbeat. Disconnect/death of the owner releases its session lock.
    """
    while not stopping.is_set():
        acquired = bool(lock.scalar(text("select pg_try_advisory_lock(:id)"), {"id": LOCK_ID}))
        lock.commit()
        if acquired:
            return True
        if once:
            raise SystemExit("Pipeline worker already owns the database lock")
        stopping.wait(1)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    configure_logging(get_settings().log_level)
    stopping = Event()
    previous = {
        sig: signal.signal(sig, lambda _sig, _frame: stopping.set())
        for sig in (signal.SIGTERM, signal.SIGINT)
    }
    try:
        with get_engine().connect() as lock:
            lock.execute(text("set application_name = 'sentinel-pipeline'"))
            lock.commit()
            if not acquire_lock(lock, stopping, once=args.once):
                return
            try:
                while not stopping.is_set():
                    lock.execute(text("select 1"))
                    lock.commit()
                    try:
                        count = events_once()
                        for _ in range(25):
                            if stopping.is_set():
                                break
                            done = score_once()
                            count += done
                            if not done:
                                break
                        heartbeat("pipeline", "HEALTHY", processed=count)
                    except Exception as exc:
                        heartbeat("pipeline", "DEGRADED", failure=type(exc).__name__)
                        if args.once:
                            raise SystemExit(1) from None
                    if args.once:
                        return
                    stopping.wait(2)
            finally:
                # No in-flight job is abandoned voluntarily; normal transaction
                # and idempotency boundaries remain in events_once/score_once.
                lock.execute(text("select pg_advisory_unlock(:id)"), {"id": LOCK_ID})
                lock.commit()
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    main()
