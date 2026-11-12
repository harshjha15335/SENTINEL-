"""Lease recovery, atomic side effects and bounded failure for webhook scoring jobs."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.models import Case, RiskAssessment, RiskScoringJob
from app.services.risk.jobs import enqueue, run_once
from tests.test_supabase_inbox import high_candidate


def captured(db, tenant):
    txn = high_candidate(db, tenant)
    txn.occurred_at = datetime(2026, 9, 1, 12, tzinfo=UTC)
    enqueue(db, txn.id)
    db.commit()
    return txn


def test_expired_scoring_claim_is_recovered_atomically(db, tenant):
    captured(db, tenant)
    job = db.scalar(select(RiskScoringJob))
    job.status, job.attempts, job.lease_token = "RUNNING", 1, uuid.uuid4()
    job.available_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert run_once() == 1
    db.expire_all()
    assert db.scalar(select(RiskScoringJob)).status == "COMPLETED"
    assert db.scalar(select(func.count()).select_from(RiskAssessment)) == 1
    assert db.scalar(select(func.count()).select_from(Case)) == 1


def test_concurrent_scoring_workers_have_one_effect(db, tenant):
    captured(db, tenant)
    job = db.scalar(select(RiskScoringJob))
    job.available_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run_once(), range(2)))
    assert sum(results) == 1
    assert db.scalar(select(func.count()).select_from(RiskAssessment)) == 1
    assert db.scalar(select(func.count()).select_from(Case)) == 1


def test_failed_scoring_backoff_and_terminal_state_have_no_partial_assessment(
    db, tenant, monkeypatch
):
    from app.services.risk import jobs

    captured(db, tenant)
    job = db.scalar(select(RiskScoringJob))
    job.available_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    def fail(*args, **kwargs):
        raise RuntimeError("sensitive upstream detail must not enter operational state")

    monkeypatch.setattr(jobs, "score_transaction", fail)
    for attempt in range(1, 6):
        assert run_once() == 0
        db.expire_all()
        job = db.scalar(select(RiskScoringJob))
        assert job.attempts == attempt
        assert job.status == ("DEAD" if attempt == 5 else "PENDING")
        assert job.available_at > datetime.now(UTC)
        assert job.last_error == "RuntimeError"
        assert db.scalar(select(func.count()).select_from(RiskAssessment)) == 0
        assert db.scalar(select(func.count()).select_from(Case)) == 0
        if attempt < 5:
            job.available_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()
    assert run_once() == 0


def test_scoring_job_reuses_existing_capture_assessment(db, tenant):
    """When scored upon capture, the webhook job links it without duplicate scoring."""
    from app.services.risk.scoring import score_after_capture

    txn = high_candidate(db, tenant)
    txn.occurred_at = datetime(2026, 9, 1, 12, tzinfo=UTC)
    score_after_capture(db, txn.id)
    initial_assessment = db.scalar(
        select(RiskAssessment).where(RiskAssessment.transaction_id == txn.id)
    )
    assert initial_assessment is not None
    assert initial_assessment.trigger == "capture"

    enqueue(db, txn.id)
    job = db.scalar(select(RiskScoringJob).where(RiskScoringJob.transaction_id == txn.id))
    job.available_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    assert run_once() == 1
    db.expire_all()
    updated_job = db.scalar(select(RiskScoringJob).where(RiskScoringJob.transaction_id == txn.id))
    assert updated_job.status == "COMPLETED"
    assert updated_job.assessment_id == initial_assessment.id

    assessments = db.scalars(
        select(RiskAssessment).where(RiskAssessment.transaction_id == txn.id)
    ).all()
    assert len(assessments) == 1
