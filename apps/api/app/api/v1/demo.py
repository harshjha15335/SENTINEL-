"""Authenticated navigation to the prebuilt isolated judge scenario; no guest mutation."""

import uuid

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import Principal, any_member
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import Case, EvidencePacket, Merchant
from app.models.enums import DataOrigin, MerchantEnvironment
from app.services.demo.judge import MERCHANT

router = APIRouter(tags=["demo"])


class JudgeScenarioOut(BaseModel):
    case_id: uuid.UUID
    transaction_id: uuid.UUID
    data_origin: DataOrigin
    investigation_mode: str


@router.get("/demo/scenario", response_model=JudgeScenarioOut)
def scenario(
    response: Response, principal: Principal = Depends(any_member), db: Session = Depends(get_db)
) -> JudgeScenarioOut:
    response.headers["Cache-Control"] = "no-store"
    merchant = db.get(Merchant, principal.merchant_id)
    if (
        merchant is None
        or merchant.name != MERCHANT
        or merchant.environment is not MerchantEnvironment.DEMO
    ):
        raise NotFoundError("No isolated judge scenario in this workspace")
    case = db.scalar(
        select(Case)
        .join(EvidencePacket, EvidencePacket.case_id == Case.id)
        .where(
            Case.merchant_id == principal.merchant_id,
            Case.data_origin == DataOrigin.SYNTHETIC_DEMO,
        )
        .order_by(Case.created_at, Case.id)
        .limit(1)
    )
    if case is None:
        raise NotFoundError("Judge scenario has not been prepared")
    return JudgeScenarioOut(
        case_id=case.id,
        transaction_id=case.transaction_id,
        data_origin=case.data_origin,
        investigation_mode="DETERMINISTIC",
    )
