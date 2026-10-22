"""Operational health without request bodies or credential-bearing exceptions."""

import logging
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert

from app.db.session import get_sessionmaker
from app.models import WorkerHealth

log = logging.getLogger("sentinel.worker_health")


def heartbeat(
    name: str,
    status: str,
    *,
    processed: int = 0,
    failure: str | None = None,
    inbox_snapshot: dict[str, object] | None = None,
) -> None:
    try:
        with get_sessionmaker()() as db:
            now = datetime.now(UTC)
            statement = insert(WorkerHealth).values(
                name=name,
                heartbeat_at=now,
                status=status,
                processed=processed,
                failures=int(failure is not None),
                last_error=failure,
                last_success_at=now if processed else None,
                inbox_snapshot=inbox_snapshot,
            )
            changes: dict[str, object] = {
                "heartbeat_at": statement.excluded.heartbeat_at,
                "status": status,
                "processed": WorkerHealth.processed + processed,
                "failures": WorkerHealth.failures + int(failure is not None),
                "last_error": failure,
            }
            if processed:
                changes["last_success_at"] = now
            if inbox_snapshot is not None:
                changes["inbox_snapshot"] = inbox_snapshot
            db.execute(
                statement.on_conflict_do_update(
                    index_elements=["name"],
                    set_=changes,
                )
            )
            db.commit()
    except Exception:
        log.warning("worker heartbeat could not be persisted")
