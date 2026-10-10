"""Investigation cases and the review queue.

A case is a unit of analyst work on one transaction. Opening, claiming, noting and resolving
are audited. Resolving records the analyst's conclusion only; it never moves money. Financial
actions (refunds) will go through a separate approval workflow (docs/AGENT_DESIGN.md).
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import case as sql_case
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import Principal
from app.core.errors import ConflictError, NotFoundError
from app.models import Case, CaseNote, RiskAssessment, Transaction
from app.models.enums import (
    CasePriority,
    CaseResolution,
    CaseSource,
    CaseStatus,
    DataOrigin,
    RiskBand,
)
from app.services import audit

SLA = {
    CasePriority.HIGH: timedelta(hours=24),
    CasePriority.MEDIUM: timedelta(hours=72),
    CasePriority.LOW: timedelta(days=7),
}
_BAND_PRIORITY = {
    RiskBand.HIGH: CasePriority.HIGH,
    RiskBand.MEDIUM: CasePriority.MEDIUM,
    RiskBand.LOW: CasePriority.LOW,
}


def _open_case_for(db: Session, txn_id: uuid.UUID) -> Case | None:
    return db.scalar(
        select(Case).where(Case.transaction_id == txn_id, Case.status != CaseStatus.RESOLVED)
    )


def _audit(
    db: Session, case: Case, action: str, actor_id: uuid.UUID | None, **meta: object
) -> None:
    audit.record(
        db,
        action=action,
        entity_type="case",
        entity_id=case.id,
        merchant_id=case.merchant_id,
        actor_id=actor_id,
        actor_type="USER" if actor_id else "SYSTEM",
        metadata={"transaction_id": str(case.transaction_id), **meta},
    )


def open_from_assessment(
    db: Session, txn: Transaction, assessment: RiskAssessment, *, now: datetime | None = None
) -> Case | None:
    """Open a review case for a HIGH assessment unless one is already open."""
    if _open_case_for(db, txn.id) is not None:
        return None
    priority = _BAND_PRIORITY[assessment.risk_band]
    opened = now or datetime.now(UTC)
    case = Case(
        merchant_id=txn.merchant_id,
        transaction_id=txn.id,
        risk_assessment_id=assessment.id,
        source=CaseSource.RISK_MODEL,
        status=CaseStatus.OPEN,
        priority=priority,
        title=f"{assessment.risk_band.value.title()} risk payment needs review",
        due_at=opened + SLA[priority],
        data_origin=txn.data_origin,
    )
    db.add(case)
    db.flush()
    _audit(
        db,
        case,
        "case.opened",
        None,
        source=CaseSource.RISK_MODEL.value,
        assessment_id=str(assessment.id),
    )
    return case


def open_manual(db: Session, principal: Principal, txn_id: uuid.UUID, *, reason: str) -> Case:
    txn = db.scalar(
        select(Transaction).where(
            Transaction.id == txn_id, Transaction.merchant_id == principal.merchant_id
        )
    )
    if txn is None:
        raise NotFoundError("Transaction not found")
    if _open_case_for(db, txn.id) is not None:
        raise ConflictError("This payment already has an open case")
    case = Case(
        merchant_id=txn.merchant_id,
        transaction_id=txn.id,
        source=CaseSource.MANUAL,
        status=CaseStatus.IN_REVIEW,
        priority=CasePriority.MEDIUM,
        title="Manual review",
        assignee_id=principal.user.id,
        opened_by_user_id=principal.user.id,
        due_at=datetime.now(UTC) + SLA[CasePriority.MEDIUM],
        data_origin=txn.data_origin,
    )
    db.add(case)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("This payment already has an open case") from exc
    db.add(CaseNote(case_id=case.id, author_id=principal.user.id, body=reason))
    _audit(db, case, "case.opened", principal.user.id, source=CaseSource.MANUAL.value)
    db.commit()
    return case


def list_cases(
    db: Session,
    merchant_id: uuid.UUID,
    *,
    status: CaseStatus | None,
    priority: CasePriority | None,
    data_origin: DataOrigin | None,
    assignee_id: uuid.UUID | None,
    transaction_id: uuid.UUID | None = None,
    limit: int,
    offset: int,
) -> tuple[list[Case], int]:
    stmt = select(Case).where(Case.merchant_id == merchant_id)
    if status:
        stmt = stmt.where(Case.status == status)
    if priority:
        stmt = stmt.where(Case.priority == priority)
    if data_origin:
        stmt = stmt.where(Case.data_origin == data_origin)
    if assignee_id:
        stmt = stmt.where(Case.assignee_id == assignee_id)
    if transaction_id:
        stmt = stmt.where(Case.transaction_id == transaction_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    unresolved_first = sql_case((Case.status == CaseStatus.RESOLVED, 1), else_=0)
    # Within a priority, the higher model score first; manual cases (no score) after.
    score = (
        select(RiskAssessment.risk_score)
        .where(RiskAssessment.id == Case.risk_assessment_id)
        .scalar_subquery()
    )
    rows = db.scalars(
        stmt.order_by(
            unresolved_first,
            Case.priority.desc(),
            Case.due_at.asc(),
            score.desc().nulls_last(),
            Case.created_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return list(rows.unique()), total


def get_case(
    db: Session, merchant_id: uuid.UUID, case_id: uuid.UUID, *, lock: bool = False
) -> Case:
    stmt = select(Case).where(Case.id == case_id, Case.merchant_id == merchant_id)
    if lock:
        stmt = stmt.with_for_update(of=Case)
    case = db.scalar(stmt)
    if case is None:
        raise NotFoundError("Case not found")
    return case


def notes_for(db: Session, case_id: uuid.UUID) -> list[CaseNote]:
    return list(
        db.scalars(
            select(CaseNote).where(CaseNote.case_id == case_id).order_by(CaseNote.created_at)
        ).unique()
    )


def claim(db: Session, principal: Principal, case_id: uuid.UUID) -> Case:
    case = get_case(db, principal.merchant_id, case_id, lock=True)
    if case.status is CaseStatus.RESOLVED:
        raise ConflictError("Case is already resolved")
    if case.assignee_id not in (None, principal.user.id):
        raise ConflictError("Case is assigned to another analyst")
    if case.assignee_id == principal.user.id and case.status is CaseStatus.IN_REVIEW:
        db.rollback()
        return get_case(db, principal.merchant_id, case_id)
    case.assignee_id = principal.user.id
    case.status = CaseStatus.IN_REVIEW
    _audit(db, case, "case.claimed", principal.user.id)
    db.commit()
    db.expire(case)  # reload relationships (assignee) changed above
    return get_case(db, principal.merchant_id, case_id)


def add_note(db: Session, principal: Principal, case_id: uuid.UUID, body: str) -> CaseNote:
    case = get_case(db, principal.merchant_id, case_id)
    note = CaseNote(case_id=case.id, author_id=principal.user.id, body=body)
    db.add(note)
    db.flush()
    # The note text is not copied into the audit log; it may contain customer details.
    _audit(db, case, "case.note_added", principal.user.id, note_id=str(note.id))
    db.commit()
    return note


def resolve(
    db: Session,
    principal: Principal,
    case_id: uuid.UUID,
    *,
    resolution: CaseResolution,
    note: str,
) -> Case:
    case = get_case(db, principal.merchant_id, case_id, lock=True)
    if case.status is CaseStatus.RESOLVED:
        raise ConflictError("Case is already resolved")
    if case.assignee_id not in (None, principal.user.id):
        raise ConflictError("Case is assigned to another analyst")
    now = datetime.now(UTC)
    case.status = CaseStatus.RESOLVED
    case.resolution = resolution
    case.resolution_note = note
    case.resolved_at = now
    case.resolved_by_user_id = principal.user.id
    case.assignee_id = case.assignee_id or principal.user.id
    _audit(db, case, "case.resolved", principal.user.id, resolution=resolution.value)
    db.commit()
    db.expire(case)  # reload relationships (assignee) changed above
    return get_case(db, principal.merchant_id, case_id)


def open_counts(db: Session, merchant_id: uuid.UUID) -> dict[tuple[DataOrigin, CasePriority], int]:
    rows = db.execute(
        select(Case.data_origin, Case.priority, func.count())
        .where(Case.merchant_id == merchant_id, Case.status != CaseStatus.RESOLVED)
        .group_by(Case.data_origin, Case.priority)
    ).all()
    return {(o, p): n for o, p, n in rows}
