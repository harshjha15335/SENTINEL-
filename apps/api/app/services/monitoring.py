"""Read-only monitoring using recorded data; score drift is not a fraud verdict."""

import math
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.models import Case, RiskAssessment, Transaction
from app.models.enums import CaseResolution, DataOrigin, RiskBand
from app.schemas.monitoring import (
    CountPoint,
    FeatureComparison,
    GraphEdge,
    GraphNode,
    MonitoringOut,
    NetworkOut,
    ScoreBin,
    TimeWindow,
)
from app.services.risk.features import FEATURE_NAMES

SAMPLE_LIMIT = 10_000


def latest_assessments(
    db: Session, merchant_id: uuid.UUID, ids: list[uuid.UUID], as_of: datetime, origin: DataOrigin
) -> dict[uuid.UUID, RiskAssessment]:
    if not ids:
        return {}
    rows = db.scalars(
        select(RiskAssessment)
        .where(
            RiskAssessment.merchant_id == merchant_id,
            RiskAssessment.data_origin == origin,
            RiskAssessment.transaction_id.in_(ids),
            RiskAssessment.created_at <= as_of,
        )
        .order_by(
            RiskAssessment.transaction_id,
            RiskAssessment.created_at.desc(),
            RiskAssessment.id.desc(),
        )
        .ext(distinct_on(RiskAssessment.transaction_id))
    )
    return {row.transaction_id: row for row in rows}


def population_stability(reference: list[float], current: list[float]) -> float | None:
    """Fixed 0.1 probability bins, 0.5 pseudocount; insufficient samples yield no metric."""
    if min(len(reference), len(current)) < 30:
        return None
    old, new = score_counts(reference), score_counts(current)
    value = 0.0
    for a, b in zip(old, new, strict=True):
        p, q = (a + 0.5) / (len(reference) + 5), (b + 0.5) / (len(current) + 5)
        value += (q - p) * math.log(q / p)
    return value


def score_counts(scores: list[float]) -> list[int]:
    bins = [0] * 10
    for score in scores:
        bins[min(9, max(0, int(score * 10)))] += 1
    return bins


def summary(
    db: Session,
    merchant_id: uuid.UUID,
    origin: DataOrigin,
    *,
    days: int,
    as_of: datetime,
    capacity: float,
) -> MonitoringOut:
    start = as_of - timedelta(days=days)
    reference_start = start - timedelta(days=days)
    txns = list(
        db.scalars(
            select(Transaction)
            .where(
                Transaction.merchant_id == merchant_id,
                Transaction.data_origin == origin,
                Transaction.occurred_at >= reference_start,
                Transaction.occurred_at < as_of,
            )
            .order_by(Transaction.occurred_at.desc(), Transaction.id)
            .limit(SAMPLE_LIMIT + 1)
        ).unique()
    )
    truncated = len(txns) > SAMPLE_LIMIT
    txns = txns[:SAMPLE_LIMIT]
    assessments = latest_assessments(db, merchant_id, [t.id for t in txns], as_of, origin)
    current_txns = [t for t in txns if t.occurred_at and t.occurred_at >= start]
    reference_txns = [t for t in txns if t.occurred_at and t.occurred_at < start]
    current = [assessments[t.id] for t in current_txns if t.id in assessments]
    reference = [assessments[t.id] for t in reference_txns if t.id in assessments]
    current_scores = [r.risk_score for r in current]
    reference_scores = [r.risk_score for r in reference]
    current_bins, reference_bins = score_counts(current_scores), score_counts(reference_scores)
    cases = list(
        db.scalars(
            select(Case)
            .where(
                Case.merchant_id == merchant_id,
                Case.data_origin == origin,
                Case.created_at < as_of,
            )
            .order_by(Case.created_at.desc(), Case.id)
            .limit(SAMPLE_LIMIT + 1)
        ).unique()
    )
    truncated = truncated or len(cases) > SAMPLE_LIMIT
    cases = cases[:SAMPLE_LIMIT]
    pending = [c for c in cases if c.resolved_at is None or c.resolved_at >= as_of]
    opened_in_window = [c for c in cases if c.created_at >= start]
    resolved_in_window = [
        c for c in cases if c.resolved_at is not None and start <= c.resolved_at < as_of
    ]
    resolved_cohort = [
        c for c in opened_in_window if c.resolved_at is not None and c.resolved_at < as_of
    ]
    high = sum(r.risk_band.value == "HIGH" for r in current)
    rate = high / len(current) if current else None
    daily = Counter(t.occurred_at.date().isoformat() for t in current_txns if t.occurred_at)
    growth = Counter(c.created_at.date().isoformat() for c in opened_in_window)
    comparisons = []
    for feature in FEATURE_NAMES:
        old = [r.feature_snapshot.get(feature) for r in reference]
        new = [r.feature_snapshot.get(feature) for r in current]
        old_numbers = [float(v) for v in old if isinstance(v, (int, float)) and math.isfinite(v)]
        new_numbers = [float(v) for v in new if isinstance(v, (int, float)) and math.isfinite(v)]
        comparisons.append(
            FeatureComparison(
                feature=feature,
                reference_missing_rate=1 - len(old_numbers) / len(old) if old else None,
                current_missing_rate=1 - len(new_numbers) / len(new) if new else None,
                reference_mean=mean(old_numbers) if old_numbers else None,
                current_mean=mean(new_numbers) if new_numbers else None,
            )
        )
    return MonitoringOut(
        observed_at=datetime.now(UTC),
        data_origin=origin,
        current_window=TimeWindow(start=start, end=as_of),
        reference_window=TimeWindow(start=reference_start, end=start),
        transaction_volume=[CountPoint(date=d, count=n) for d, n in sorted(daily.items())],
        current_transactions=len(current_txns),
        reference_transactions=len(reference_txns),
        current_scored=len(current),
        reference_scored=len(reference),
        score_distribution=[
            ScoreBin(lower=i / 10, upper=(i + 1) / 10, reference_count=a, current_count=b)
            for i, (a, b) in enumerate(zip(reference_bins, current_bins, strict=True))
        ],
        risk_bands=dict(Counter(r.risk_band.value for r in current)),
        model_versions=dict(Counter(r.model_version for r in current)),
        high_flag_rate=rate,
        illustrative_capacity=capacity,
        capacity_utilization=rate / capacity if rate is not None else None,
        open_cases=len(pending),
        oldest_pending_hours=max((as_of - c.created_at).total_seconds() / 3600 for c in pending)
        if pending
        else None,
        overdue_cases=sum(c.due_at < as_of for c in pending),
        case_growth=[CountPoint(date=d, count=n) for d, n in sorted(growth.items())],
        resolved_in_window=len(resolved_in_window),
        resolution_rate=len(resolved_cohort) / len(opened_in_window) if opened_in_window else None,
        confirmed_adverse_cases=sum(
            c.resolution is CaseResolution.CONFIRMED_ADVERSE for c in resolved_in_window
        ),
        score_psi=population_stability(reference_scores, current_scores) if not truncated else None,
        psi_note=(
            "Fixed probability bins (0.1), 0.5 pseudocount, at least 30 scores in each window. "
            "No metric is issued for insufficient or truncated samples. PSI is descriptive; "
            "no arbitrary cutoff establishes fraud or model degradation."
        ),
        feature_comparison=comparisons,
        sample_limit=SAMPLE_LIMIT,
        truncated=truncated,
        calibration_status="Unavailable: no validated delayed-label cohort is linked.",
        limitations=[
            "One merchant and one selected origin only; no provider request is made.",
            "Occurrence-time windows; assessments recorded after the window end are excluded.",
            "Latest recorded assessments are historical observations, not a new fraud benchmark.",
            "Truncated counts are bounded samples; use narrower windows for complete coverage.",
            "Capacity is an illustrative share of scores, not staff hours or review throughput.",
            "Case resolutions are analyst labels, not verified fraud. Labels can arrive late.",
            "Investigation and infrastructure health are separate on administrator Operations.",
        ],
    )


def network(
    db: Session,
    merchant_id: uuid.UUID,
    origin: DataOrigin,
    *,
    days: int,
    as_of: datetime,
    limit: int,
    payer: str | None = None,
    risk_band: RiskBand | None = None,
) -> NetworkOut:
    start = as_of - timedelta(days=days)
    query = select(Transaction).where(
        Transaction.merchant_id == merchant_id,
        Transaction.data_origin == origin,
        Transaction.occurred_at >= start,
        Transaction.occurred_at < as_of,
    )
    if risk_band is not None:
        latest = (
            select(RiskAssessment.transaction_id, RiskAssessment.risk_band)
            .where(
                RiskAssessment.merchant_id == merchant_id,
                RiskAssessment.data_origin == origin,
                RiskAssessment.created_at <= as_of,
            )
            .order_by(
                RiskAssessment.transaction_id,
                RiskAssessment.created_at.desc(),
                RiskAssessment.id.desc(),
            )
            .ext(distinct_on(RiskAssessment.transaction_id))
            .subquery()
        )
        query = query.join(latest, latest.c.transaction_id == Transaction.id).where(
            latest.c.risk_band == risk_band
        )
    if payer:
        query = query.where(Transaction.payer_reference == payer)
    txns = list(
        db.scalars(
            query.order_by(Transaction.occurred_at.desc(), Transaction.id).limit(limit + 1)
        ).unique()
    )
    truncated = len(txns) > limit
    txns = txns[:limit]
    assessments = latest_assessments(db, merchant_id, [t.id for t in txns], as_of, origin)
    nodes = [
        GraphNode(
            id="merchant",
            kind="merchant",
            label="Your merchant",
            source="Authenticated merchant scope",
        )
    ]
    edges = []
    payer_counts = Counter(t.payer_reference for t in txns if t.payer_reference)
    for value in sorted(payer_counts):
        nodes.append(
            GraphNode(
                id="payer:" + value,
                kind="payer",
                label=value[:32],
                source="Recorded payer_reference; not a verified identity",
            )
        )
    for txn in txns:
        txid = "transaction:" + str(txn.id)
        assessment = assessments.get(txn.id)
        nodes.append(
            GraphNode(
                id=txid,
                kind="transaction",
                label=str(txn.id)[:8],
                record_id=txn.id,
                risk_band=assessment.risk_band.value if assessment else None,
                source="Merchant-owned transaction record",
            )
        )
        edges.append(
            GraphEdge(
                source="merchant",
                target=txid,
                relationship="owns",
                explanation="Transaction merchant_id matches the authenticated merchant.",
                transaction_id=txn.id,
                data_origin=origin,
            )
        )
        if txn.payer_reference:
            edges.append(
                GraphEdge(
                    source="payer:" + txn.payer_reference,
                    target=txid,
                    relationship="recorded_payer",
                    transaction_id=txn.id,
                    data_origin=origin,
                    explanation=(
                        "Recorded opaque payer reference; not proof of identity or fraud."
                    ),
                )
            )
    if txns:
        cases = (
            db.scalars(
                select(Case)
                .where(
                    Case.merchant_id == merchant_id,
                    Case.data_origin == origin,
                    Case.transaction_id.in_([t.id for t in txns]),
                    Case.created_at < as_of,
                )
                .order_by(Case.created_at.desc(), Case.id)
                .limit(limit + 1)
            )
            .unique()
            .all()
        )
        truncated = truncated or len(cases) > limit
        for case in cases[:limit]:
            cid = "case:" + str(case.id)
            nodes.append(
                GraphNode(
                    id=cid,
                    kind="case",
                    label=case.title[:40],
                    record_id=case.id,
                    source="Stored review case transaction_id",
                )
            )
            edges.append(
                GraphEdge(
                    source="transaction:" + str(case.transaction_id),
                    target=cid,
                    relationship="review_case",
                    explanation="Case references this exact transaction.",
                    transaction_id=case.transaction_id,
                    data_origin=origin,
                )
            )
    return NetworkOut(
        data_origin=origin,
        window=TimeWindow(start=start, end=as_of),
        nodes=nodes,
        edges=edges,
        repeated_payer_groups=sum(n >= 3 for n in payer_counts.values()),
        transaction_count=len(txns),
        limit=limit,
        truncated=truncated,
        limitations=[
            "Bounded view. Repeated references are not proof of coordinated fraud.",
            "Only recorded payer references, payments and cases; no invented device/IP/card data.",
            "Single origin and window; future transactions, cases and assessments are excluded.",
            "Graph exploration never blocks, captures, refunds or contacts a provider.",
        ],
    )
