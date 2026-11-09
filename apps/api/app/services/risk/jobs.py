"""At-least-once jobs with atomic assessment/case/completion commits."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.session import get_sessionmaker
from app.models import RiskScoringJob, Transaction
from app.services.risk.scoring import latest_for, score_transaction

log = logging.getLogger("sentinel.scoring_jobs")
MAX_ATTEMPTS = 5


def enqueue(db: Session, transaction_id: uuid.UUID) -> None:
    db.execute(
        insert(RiskScoringJob)
        .values(transaction_id=transaction_id)
        .on_conflict_do_nothing(index_elements=["transaction_id"])
    )


def run_once() -> int:
    maker = get_sessionmaker()
    now = datetime.now(UTC)
    with maker() as db:
        job = db.scalar(
            select(RiskScoringJob)
            .where(
                RiskScoringJob.status.in_(["PENDING", "RUNNING"]),
                RiskScoringJob.available_at <= now,
            )
            .order_by(RiskScoringJob.available_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return 0
        if job.attempts >= MAX_ATTEMPTS:
            job.status, job.last_error = "DEAD", "LeaseExhausted"
            job.lease_token = None
            db.commit()
            return 0
        job.status, job.lease_token = "RUNNING", uuid.uuid4()
        job.attempts += 1
        job.available_at = now + timedelta(minutes=2)
        identity, token = job.id, job.lease_token
        db.commit()
    try:
        with maker() as db:
            job = db.scalar(
                select(RiskScoringJob).where(RiskScoringJob.id == identity).with_for_update()
            )
            if (
                job is None
                or job.status != "RUNNING"
                or job.lease_token != token
                or job.available_at <= datetime.now(UTC)
            ):
                return 0
            txn = db.scalar(
                select(Transaction)
                .where(Transaction.id == job.transaction_id)
                .with_for_update(of=Transaction)
            )
            if txn is None:
                raise LookupError("Transaction missing")
            assessment = latest_for(db, txn.merchant_id, txn.id)
            if assessment is None:
                assessment = score_transaction(db, txn, trigger="webhook_capture", actor_id=None)
            job.assessment_id = assessment.id
            job.status, job.completed_at, job.lease_token = "COMPLETED", datetime.now(UTC), None
            job.last_error = None
            db.commit()
        return 1
    except Exception as exc:
        with maker() as db:
            job = db.scalar(
                select(RiskScoringJob)
                .where(RiskScoringJob.id == identity, RiskScoringJob.lease_token == token)
                .with_for_update()
            )
            if job is not None:
                job.status = "DEAD" if job.attempts >= MAX_ATTEMPTS else "PENDING"
                job.available_at = datetime.now(UTC) + timedelta(
                    seconds=min(300, 5 * 2**job.attempts)
                )
                job.lease_token, job.last_error = None, type(exc).__name__
                db.commit()
        log.warning("scoring failed", extra={"data": {"category": type(exc).__name__}})
        return 0
