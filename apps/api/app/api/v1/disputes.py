"""Dispute preparation routes. External submission is intentionally unavailable."""

import io
import uuid
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Query, Response
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import paypal_gateway
from app.auth.deps import Principal, admin_only, any_member, operator
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.disputes import Dispute, DisputeDraft
from app.models.enums import DataOrigin
from app.schemas.disputes import (
    AssignDispute,
    CreateDemoDispute,
    DisputeDetailOut,
    DisputeDraftOut,
    DisputeOut,
    DisputeSyncOut,
)
from app.services import audit, cases, disputes
from app.services.paypal.gateway import PayPalGateway

router = APIRouter(prefix="/disputes", tags=["disputes"])


@router.get("", response_model=list[DisputeOut])
def list_disputes(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    data_origin: DataOrigin | None = None,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> list[DisputeOut]:
    statement = select(Dispute).where(Dispute.merchant_id == principal.merchant_id)
    if data_origin is not None:
        statement = statement.where(Dispute.data_origin == data_origin)
    rows = db.scalars(
        statement.order_by(Dispute.created_at.desc(), Dispute.id).limit(limit).offset(offset)
    )
    return [DisputeOut.model_validate(row) for row in rows]


@router.post("/demo", response_model=DisputeOut, status_code=201)
def create_demo(
    body: CreateDemoDispute,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> DisputeOut:
    return DisputeOut.model_validate(disputes.create_demo(db, principal, body.case_id, body.reason))


@router.post("/sync", response_model=DisputeSyncOut)
def synchronize(
    principal: Principal = Depends(admin_only),
    gateway: PayPalGateway = Depends(paypal_gateway),
    db: Session = Depends(get_db),
) -> DisputeSyncOut:
    return DisputeSyncOut(synchronized=disputes.sync(db, principal, gateway))


@router.get("/{identity}", response_model=DisputeDetailOut)
def detail(
    identity: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> DisputeDetailOut:
    item = disputes.get_dispute(db, principal.merchant_id, identity)
    drafts = db.scalars(
        select(DisputeDraft)
        .where(
            DisputeDraft.dispute_id == item.id, DisputeDraft.merchant_id == principal.merchant_id
        )
        .order_by(DisputeDraft.created_at.desc())
    )
    return DisputeDetailOut(
        dispute=DisputeOut.model_validate(item),
        checklist=disputes.checklist(db, item),
        drafts=[DisputeDraftOut.model_validate(row) for row in drafts],
        limitations=[
            "Checklist reflects uploader categories, not verified proof.",
            "Response drafts are deterministic preparation, not real LLM analysis.",
            "Only the first provider page is synchronized; account permissions remain unverified.",
            "External evidence submission and dispute responses are disabled.",
            "Generate a case packet and request independent approval in the linked workbench.",
        ],
    )


@router.post("/{identity}/drafts", response_model=DisputeDraftOut, status_code=201)
def create_draft(
    identity: uuid.UUID,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> DisputeDraftOut:
    return DisputeDraftOut.model_validate(disputes.draft(db, principal, identity))


@router.post("/{identity}/assign", response_model=DisputeOut)
def assign(
    identity: uuid.UUID,
    body: AssignDispute,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> DisputeOut:
    return DisputeOut.model_validate(disputes.assign(db, principal, identity, body.user_id))


@router.get("/{identity}/drafts/{draft_id}/download")
def download_draft(
    identity: uuid.UUID,
    draft_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> Response:
    item = disputes.get_dispute(db, principal.merchant_id, identity)
    draft = db.scalar(
        select(DisputeDraft).where(
            DisputeDraft.id == draft_id,
            DisputeDraft.dispute_id == item.id,
            DisputeDraft.merchant_id == principal.merchant_id,
        )
    )
    if draft is None:
        raise NotFoundError("Response draft not found")
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    contents = [Paragraph("SENTINEL dispute preparation draft", styles["Title"]), Spacer(1, 16)]
    contents += [Paragraph(escape(line), styles["BodyText"]) for line in draft.body.split("\n\n")]
    SimpleDocTemplate(buf).build(contents)
    audit.record_for_case(
        db,
        cases.get_case(db, principal.merchant_id, item.case_id),
        "dispute.draft.downloaded",
        principal.user.id,
        entity_type="dispute_draft",
        entity_id=draft.id,
    )
    db.commit()
    return Response(
        buf.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="dispute-response-draft.pdf"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )


@router.post("/{identity}/submit")
def disabled_submission(
    identity: uuid.UUID,
    principal: Principal = Depends(admin_only),
    db: Session = Depends(get_db),
) -> None:
    disputes.get_dispute(db, principal.merchant_id, identity)
    disputes.reject_submission()
