"""Separate intent, independent approval, and explicitly enabled sandbox execution."""

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import paypal_gateway
from app.auth.deps import Principal, admin_only, any_member, operator
from app.db.session import get_db
from app.models.refunds import RefundRequest
from app.schemas.refunds import (
    RefundCreate,
    RefundDecision,
    RefundExecute,
    RefundHistoryOut,
    RefundOut,
)
from app.services import refunds
from app.services.paypal.gateway import PayPalGateway

router = APIRouter(tags=["refunds"])


def out(row: RefundRequest) -> RefundOut:
    return RefundOut.model_validate(row)


@router.get("/refunds", response_model=list[RefundOut])
def list_refunds(
    response: Response, principal: Principal = Depends(any_member), db: Session = Depends(get_db)
) -> list[RefundOut]:
    response.headers["Cache-Control"] = "no-store"
    rows = db.scalars(
        select(RefundRequest)
        .where(RefundRequest.merchant_id == principal.merchant_id)
        .order_by(RefundRequest.created_at.desc())
        .limit(100)
    ).all()
    return [out(row) for row in rows]


@router.get("/transactions/{transaction_id}/refunds", response_model=RefundHistoryOut)
def history(
    transaction_id: uuid.UUID,
    response: Response,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> RefundHistoryOut:
    response.headers["Cache-Control"] = "no-store"
    txn = refunds.transaction(db, principal.merchant_id, transaction_id)
    rows = db.scalars(
        select(RefundRequest)
        .where(RefundRequest.transaction_id == txn.id)
        .order_by(RefundRequest.created_at.desc())
        .limit(100)
    ).all()
    reserved = refunds.reserved_amount(db, txn)
    return RefundHistoryOut(
        items=[out(row) for row in rows],
        captured_amount_minor=txn.amount_minor,
        reserved_amount_minor=reserved,
        available_amount_minor=max(0, txn.amount_minor - reserved)
        if refunds.balance_known(db, txn)
        else 0,
        balance_known=refunds.balance_known(db, txn),
        currency=txn.currency,
        execution_enabled=refunds.enabled(),
        limitation=refunds.LIMITATION,
    )


@router.post("/cases/{case_id}/refunds", response_model=RefundOut, status_code=201)
def request_refund(
    case_id: uuid.UUID,
    body: RefundCreate,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> RefundOut:
    return out(refunds.create(db, principal, case_id, amount_minor=body.amount_minor))


@router.get("/refunds/{refund_id}", response_model=RefundOut)
def get_refund(
    refund_id: uuid.UUID,
    response: Response,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> RefundOut:
    response.headers["Cache-Control"] = "no-store"
    return out(refunds.get(db, principal.merchant_id, refund_id))


@router.post("/refunds/{refund_id}/decision", response_model=RefundOut)
def decide_refund(
    refund_id: uuid.UUID,
    body: RefundDecision,
    principal: Principal = Depends(admin_only),
    db: Session = Depends(get_db),
) -> RefundOut:
    return out(
        refunds.decide(
            db, principal, refund_id, decision=body.decision, digest=body.snapshot_sha256
        )
    )


@router.post("/refunds/{refund_id}/execute", response_model=RefundOut)
def execute_refund(
    refund_id: uuid.UUID,
    body: RefundExecute,
    principal: Principal = Depends(admin_only),
    gateway: PayPalGateway = Depends(paypal_gateway),
    db: Session = Depends(get_db),
) -> RefundOut:
    # Schema requires confirm=true and the exact approved immutable snapshot digest.
    return out(
        refunds.execute(db, principal, refund_id, digest=body.snapshot_sha256, gateway=gateway)
    )


@router.post("/refunds/{refund_id}/reconcile", response_model=RefundOut)
def reconcile_refund(
    refund_id: uuid.UUID,
    principal: Principal = Depends(admin_only),
    gateway: PayPalGateway = Depends(paypal_gateway),
    db: Session = Depends(get_db),
) -> RefundOut:
    return out(refunds.reconcile(db, principal, refund_id, gateway=gateway))
