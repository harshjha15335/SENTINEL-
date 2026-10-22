"""Recover durable webhook events and scoring jobs; one process per database."""

import argparse
import time

from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_engine
from app.services.risk.jobs import run_once as score_once
from app.services.worker_health import heartbeat
from app.workers.events import run_once as events_once


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    configure_logging(get_settings().log_level)
    with get_engine().connect() as lock:
        if not lock.scalar(text("select pg_try_advisory_lock(7682346)")):
            raise SystemExit("Pipeline worker already owns the database lock")
        lock.commit()
        try:
            while True:
                lock.execute(text("select 1"))
                lock.commit()
                try:
                    count = events_once()
                    for _ in range(25):
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
                time.sleep(2)
        finally:
            lock.execute(text("select pg_advisory_unlock(7682346)"))
            lock.commit()


if __name__ == "__main__":
    main()
