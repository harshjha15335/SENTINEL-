"""Authenticated navigation to the prebuilt isolated judge scenario; no guest mutation."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.auth.deps import Principal, any_member
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import Case, EvidencePacket, InvestigationRun, Merchant, Transaction
from app.models.enums import DataOrigin, InvestigationStatus, MerchantEnvironment
from app.services.demo.judge import FRESH_VERSION, MERCHANT

router = APIRouter(tags=["demo"])


class JudgeScenarioOut(BaseModel):
    case_id: uuid.UUID
    transaction_id: uuid.UUID
    data_origin: DataOrigin
    investigation_mode: str
    scenario_version: str
    created_at: datetime
    due_at: datetime | None


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
        .join(Transaction, Transaction.id == Case.transaction_id)
        .where(
            Case.merchant_id == principal.merchant_id,
            or_(
                Case.data_origin == DataOrigin.SYNTHETIC_DEMO,
                and_(
                    Case.data_origin == DataOrigin.SIMULATED,
                    Transaction.provider_summary["judge_scenario_version"].as_string()
                    == FRESH_VERSION,
                ),
            ),
        )
        .order_by(Case.created_at.desc(), Case.id.desc())
        .limit(1)
    )
    if case is None:
        raise NotFoundError("Judge scenario has not been prepared")
    run = db.scalar(
        select(InvestigationRun)
        .where(
            InvestigationRun.case_id == case.id,
            InvestigationRun.merchant_id == principal.merchant_id,
            InvestigationRun.status == InvestigationStatus.COMPLETED,
        )
        .order_by(InvestigationRun.completed_at.desc())
        .limit(1)
    )
    if run is None:
        raise NotFoundError("Prepared investigation is not available")
    return JudgeScenarioOut(
        case_id=case.id,
        transaction_id=case.transaction_id,
        data_origin=case.data_origin,
        investigation_mode=run.mode.value,
        scenario_version=FRESH_VERSION
        if case.data_origin is DataOrigin.SIMULATED
        else "historical-synthetic-v1",
        created_at=case.created_at,
        due_at=case.due_at,
    )
