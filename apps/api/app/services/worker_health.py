"""Operational health without request bodies or credential-bearing exceptions."""

import logging
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert

from app.db.session import get_sessionmaker
from app.models import WorkerHealth

log = logging.getLogger("sentinel.worker_health")


def heartbeat(name: str, status: str, *, processed: int = 0, failure: str | None = None) -> None:
    try:
        with get_sessionmaker()() as db:
            statement = insert(WorkerHealth).values(
                name=name,
                heartbeat_at=datetime.now(UTC),
                status=status,
                processed=processed,
                failures=int(failure is not None),
                last_error=failure,
            )
            db.execute(
                statement.on_conflict_do_update(
                    index_elements=["name"],
                    set_={
                        "heartbeat_at": statement.excluded.heartbeat_at,
                        "status": status,
                        "processed": WorkerHealth.processed + processed,
                        "failures": WorkerHealth.failures + int(failure is not None),
                        "last_error": failure,
                    },
                )
            )
            db.commit()
    except Exception:
        log.warning("worker heartbeat could not be persisted")
