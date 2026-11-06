"""Operational health without request bodies or credential-bearing exceptions."""

import logging
from datetime import UTC, datetime

from sqlalchemy import func, literal
from sqlalchemy.dialects.postgresql import JSONB, insert

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
    poll_succeeded: bool = False,
) -> None:
    try:
        with get_sessionmaker()() as db:
            now = datetime.now(UTC)
            snapshot_delta = dict(inbox_snapshot or {})
            if poll_succeeded:
                snapshot_delta["last_successful_poll_at"] = now.isoformat()
            statement = insert(WorkerHealth).values(
                name=name,
                heartbeat_at=now,
                status=status,
                processed=processed,
                failures=int(failure is not None),
                last_error=failure,
                last_success_at=now if processed else None,
                inbox_snapshot=snapshot_delta or None,
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
            if snapshot_delta:
                changes["inbox_snapshot"] = func.coalesce(
                    WorkerHealth.inbox_snapshot, literal({}, type_=JSONB)
                ).op("||")(literal(snapshot_delta, type_=JSONB))
            db.execute(
                statement.on_conflict_do_update(
                    index_elements=["name"],
                    set_=changes,
                )
            )
            db.commit()
    except Exception:
        log.warning("worker heartbeat could not be persisted")
