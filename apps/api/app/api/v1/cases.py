import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import Principal, any_member, operator
from app.db.session import get_db
from app.models import AuditEvent, Case, RiskAssessment
from app.models.enums import CasePriority, CaseStatus, DataOrigin
from app.schemas.api import (
    AuditOut,
    CaseDetailOut,
    CaseNoteOut,
    CaseNoteRequest,
    CaseOut,
    OpenCaseRequest,
    ResolveCaseRequest,
    RiskAssessmentOut,
)
from app.schemas.common import Page
from app.services import cases as svc
from app.services.risk.scoring import latest_for
from app.services.transactions import to_out

router = APIRouter(prefix="/cases", tags=["cases"])


def _out(db: Session, case: Case) -> CaseOut:
    out = CaseOut.model_validate(case)
    assessment = latest_for(db, case.merchant_id, case.transaction_id)
    out.transaction = to_out(case.transaction, assessment)
    return out


def _detail(db: Session, case: Case) -> CaseDetailOut:
    assessment = (
        db.get(RiskAssessment, case.risk_assessment_id)
        if case.risk_assessment_id
        else latest_for(db, case.merchant_id, case.transaction_id)
    )
    audit_rows = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.merchant_id == case.merchant_id,
            AuditEvent.entity_type == "case",
            AuditEvent.entity_id == str(case.id),
        )
        .order_by(AuditEvent.created_at)
    )
    return CaseDetailOut(
        **_out(db, case).model_dump(),
        notes=[CaseNoteOut.model_validate(n) for n in svc.notes_for(db, case.id)],
        assessment=RiskAssessmentOut.model_validate(assessment) if assessment else None,
        audit=[AuditOut.model_validate(a) for a in audit_rows],
    )


@router.get("", response_model=Page[CaseOut])
def list_(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: CaseStatus | None = None,
    priority: CasePriority | None = None,
    data_origin: DataOrigin | None = None,
    mine: bool = False,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> Page[CaseOut]:
    rows, total = svc.list_cases(
        db,
        principal.merchant_id,
        status=status,
        priority=priority,
        data_origin=data_origin,
        assignee_id=principal.user.id if mine else None,
        limit=limit,
        offset=offset,
    )
    return Page(items=[_out(db, r) for r in rows], total=total, limit=limit, offset=offset)


@router.post("", response_model=CaseDetailOut, status_code=201)
def open_(
    body: OpenCaseRequest,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = svc.open_manual(db, principal, body.transaction_id, reason=body.reason)
    return _detail(db, svc.get_case(db, principal.merchant_id, case.id))


@router.get("/{case_id}", response_model=CaseDetailOut)
def detail(
    case_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    return _detail(db, svc.get_case(db, principal.merchant_id, case_id))


@router.post("/{case_id}/claim", response_model=CaseDetailOut)
def claim(
    case_id: uuid.UUID,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    return _detail(db, svc.claim(db, principal, case_id))


@router.post("/{case_id}/notes", response_model=CaseNoteOut, status_code=201)
def note(
    case_id: uuid.UUID,
    body: CaseNoteRequest,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> CaseNoteOut:
    return CaseNoteOut.model_validate(svc.add_note(db, principal, case_id, body.body))


@router.post("/{case_id}/resolve", response_model=CaseDetailOut)
def resolve(
    case_id: uuid.UUID,
    body: ResolveCaseRequest,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> CaseDetailOut:
    case = svc.resolve(db, principal, case_id, resolution=body.resolution, note=body.note)
    return _detail(db, case)
