"""Shared helpers for the Phase 4 tests: cases, PDFs, clients and scripted (mock) models.

Scripted models are pydantic-ai ``FunctionModel``s. They exercise our tools, validation and
persistence; they say nothing about how a real provider behaves (see tests/integration/).
"""

import io
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models import Case, Transaction
from app.models.enums import DataOrigin, Role, TransactionStatus
from app.services.cases import open_from_assessment
from app.services.investigation.provider import ProviderSpec
from app.services.risk.scoring import score_transaction
from tests.conftest import PASSWORD, Tenant

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def make_txn(
    db: Session,
    tenant: Tenant,
    *,
    at: datetime = T0,
    payer: str | None = "SYN-PAYER-0001",
    origin: DataOrigin = DataOrigin.SYNTHETIC_DEMO,
    status: TransactionStatus = TransactionStatus.CAPTURED,
    amount: int = 4200,
    refunded: bool = False,
) -> Transaction:
    txn = Transaction(
        merchant_id=tenant.merchant.id,
        product_id=tenant.product.id,
        quantity=1,
        amount_minor=amount,
        currency="USD",
        status=status,
        payer_reference=payer,
        create_idempotency_key=f"test-{uuid.uuid4()}",
        paypal_request_id=f"test-{uuid.uuid4()}",
        provider_summary={},
        data_origin=origin,
        occurred_at=at,
        refunded_at=at + timedelta(days=2) if refunded else None,
    )
    db.add(txn)
    db.flush()
    return txn


def make_case(db: Session, tenant: Tenant, **kw: Any) -> Case:
    """A scored payment with an open review case, plus one earlier payment from the same payer."""
    make_txn(
        db,
        tenant,
        at=T0 - timedelta(days=10),
        refunded=True,
        payer=kw.get("payer", "SYN-PAYER-0001"),
    )
    txn = make_txn(db, tenant, **kw)
    db.commit()
    assessment = score_transaction(db, txn, trigger="test", actor_id=None)
    db.flush()
    case = db.query(Case).filter(Case.transaction_id == txn.id).one_or_none()
    if case is None:
        case = open_from_assessment(db, txn, assessment)
    db.commit()
    assert case is not None
    return case


def make_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for line in text.splitlines():
        c.drawString(40, y, line)
        y -= 14
    c.save()
    return buf.getvalue()


PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


def client_for(tenant: Tenant, role: Role) -> tuple[TestClient, dict[str, str]]:
    from app.main import app

    c = TestClient(app)
    resp = c.post(
        "/api/v1/auth/login", json={"email": tenant.users[role].email, "password": PASSWORD}
    )
    assert resp.status_code == 200, resp.text
    return c, {"X-CSRF-Token": resp.json()["csrf_token"]}


def upload(
    client: TestClient,
    headers: dict[str, str],
    case_id: uuid.UUID | str,
    data: bytes,
    *,
    name: str = "invoice.pdf",
    content_type: str = "application/pdf",
    category: str = "INVOICE",
    description: str = "",
) -> Any:
    return client.post(
        f"/api/v1/cases/{case_id}/evidence",
        files={"file": (name, data, content_type)},
        data={"category": category, "description": description},
        headers=headers,
    )


# -- scripted models --------------------------------------------------------------------------

Step = Callable[[list[ModelMessage], AgentInfo], ModelResponse]


def tool_returns(messages: list[ModelMessage]) -> dict[str, Any]:
    """Latest return value of each tool so far."""
    out: dict[str, Any] = {}
    for m in messages:
        if isinstance(m, ModelRequest):
            for p in m.parts:
                if isinstance(p, ToolReturnPart):
                    out[p.tool_name] = p.content
    return out


def call(*calls: tuple[str, dict[str, Any]]) -> Step:
    def step(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(name, args) for name, args in calls])

    return step


def answer(build: Callable[[dict[str, Any]], dict[str, Any]]) -> Step:
    def step(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, build(tool_returns(messages)))]
        )

    return step


def scripted(*steps: Step, log: list[list[ModelMessage]] | None = None) -> ProviderSpec:
    """A model that plays ``steps`` in order, repeating the last one."""
    state = {"n": 0}

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if log is not None:
            log.append(list(messages))
        step = steps[min(state["n"], len(steps) - 1)]
        state["n"] += 1
        return step(messages, info)

    return ProviderSpec(
        "test", "function:scripted", lambda: FunctionModel(fn, model_name="scripted")
    )


STANDARD_TOOLS = call(
    ("get_case_information", {}),
    ("get_transaction_details", {}),
    ("get_latest_risk_assessment", {}),
    ("get_payer_history", {"limit": 10}),
    ("get_capture_information", {}),
    ("get_case_notes", {}),
    ("list_case_evidence", {}),
    ("get_related_disputes", {}),
)


def grounded_findings(r: dict[str, Any], **override: Any) -> dict[str, Any]:
    """Findings that cite only what the tools returned."""
    txn = r["get_transaction_details"]
    risk = r["get_latest_risk_assessment"]
    evidence = r.get("list_case_evidence", {}).get("evidence", [])
    out: dict[str, Any] = {
        "summary": "Captured payment from a payer with an earlier refund; model rates it high.",
        "verified_facts": [
            {
                "statement": f"Payment of {txn['amount_minor']} minor units, {txn['data_origin']}.",
                "sources": [{"kind": "transaction", "id": txn["id"]}],
            }
        ],
        "risk_indicators": [
            {
                "description": "Model-generated score in the high band (shadow policy).",
                "sources": [{"kind": "risk_assessment", "id": risk["id"]}],
            }
        ],
        "counter_indicators": [],
        "evidence_references": [
            {"evidence_id": e["id"], "relevance": "Merchant-provided invoice."} for e in evidence
        ],
        "missing_information": ["Proof of delivery"],
        "limitations": ["Synthetic data; disputes tool unavailable until Phase 5."],
        "recommended_action": "REQUEST_MORE_EVIDENCE",
        "recommendation_rationale": "Delivery evidence is missing.",
        "human_approval_required": True,
    }
    out.update(override)
    return out
