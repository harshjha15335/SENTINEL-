"""Durable webhook worker: re-drives RECEIVED/FAILED events from the database.

Run: python -m app.workers.events [--once]
The API also processes each event right after acknowledging it; this loop is the safety net
for crashes and transient failures. No Redis or broker is needed at current volume.
"""

import argparse
import logging
import time

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_sessionmaker
from app.services.webhooks import pending_event_ids, process_event

log = logging.getLogger("sentinel.worker")


def run_once() -> int:
    maker = get_sessionmaker()
    with maker() as db:
        ids = pending_event_ids(db)
    for event_id in ids:
        with maker() as db:
            process_event(db, event_id)
    return len(ids)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()
    configure_logging(get_settings().log_level)
    while True:
        n = run_once()
        if n:
            log.info("processed events", extra={"data": {"count": n}})
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
