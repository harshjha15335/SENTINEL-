"""Validation-only simulation and shadow proposal governance; no activation endpoint."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import Principal, admin_only, any_member, operator
from app.db.session import get_db
from app.models.policy import PolicyDraft
from app.schemas.policy import (
    CreatePolicyRequest,
    DecidePolicyRequest,
    PolicyDraftOut,
    PolicyParameters,
    PolicySimulationOut,
)
from app.services import policy

router = APIRouter(prefix="/policy-lab", tags=["policy-lab"])


@router.get("/simulate", response_model=PolicySimulationOut)
def simulate(
    params: Annotated[PolicyParameters, Query()], principal: Principal = Depends(any_member)
) -> PolicySimulationOut:
    return policy.simulate(params)


@router.get("/drafts", response_model=list[PolicyDraftOut])
def drafts(
    principal: Principal = Depends(any_member), db: Session = Depends(get_db)
) -> list[PolicyDraft]:
    return list(
        db.scalars(
            select(PolicyDraft)
            .where(PolicyDraft.merchant_id == principal.merchant_id)
            .order_by(PolicyDraft.created_at.desc())
            .limit(100)
        )
    )


@router.post("/drafts", response_model=PolicyDraftOut, status_code=201)
def create(
    body: CreatePolicyRequest,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> PolicyDraft:
    return policy.create(
        db, principal, name=body.name, rationale=body.rationale, params=body.parameters
    )


@router.post("/drafts/{ident}/submit", response_model=PolicyDraftOut)
def submit(
    ident: uuid.UUID, principal: Principal = Depends(operator), db: Session = Depends(get_db)
) -> PolicyDraft:
    return policy.submit(db, principal, ident)


@router.post("/drafts/{ident}/decide", response_model=PolicyDraftOut)
def decide(
    ident: uuid.UUID,
    body: DecidePolicyRequest,
    principal: Principal = Depends(admin_only),
    db: Session = Depends(get_db),
) -> PolicyDraft:
    return policy.decide(db, principal, ident, body.decision)
