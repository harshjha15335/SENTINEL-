"""Approval workflow: request → one decision (approve/reject) → recorded execution.

Rules enforced here and in the database:
- the requested action is snapshotted by the server at request time and cannot change
  (``snapshot_sha256`` is re-checked on decision; a trigger blocks updates);
- the decider must hold a required role, belong to the merchant and not be the requester;
- only PENDING requests can be decided, once (row lock + unique decision per request);
- approval and execution are separate records. A PREPARE_REFUND approval records the approved
  intent only: no PayPal call is made in Phase 4 (``provider_called`` is constrained to false).
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import Principal
from app.core.errors import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from app.models import (
    ActionExecution,
    ApprovalDecision,
    ApprovalRequest,
    Case,
)
from app.models.enums import (
    ApprovalActionType,
    ApprovalDecisionValue,
    ApprovalStatus,
    CasePriority,
    CaseStatus,
    DataOrigin,
    ExecutionStatus,
    Role,
    TransactionStatus,
)
from app.services import audit
from app.services.cases import get_case
from app.services.investigation.runner import latest_completed
from app.services.packets import get_packet

REQUIRED_ROLES: dict[ApprovalActionType, list[str]] = {
    ApprovalActionType.MANUAL_REVIEW: [Role.ADMIN.value, Role.ANALYST.value],
    ApprovalActionType.EVIDENCE_PACKET_INTERNAL: [Role.ADMIN.value, Role.ANALYST.value],
    ApprovalActionType.PREPARE_REFUND: [Role.ADMIN.value],
}
REFUND_NOT_EXECUTED = (
    "Approved refund intent recorded. Financial execution is a separate, protected Phase 5 "
    "capability; no PayPal request was made."
)


class InvalidActionError(DomainError):
    status_code = 422
    code = "invalid_action"


def snapshot_digest(snapshot: dict[str, Any]) -> str:
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _snapshot(
    db: Session,
    case: Case,
    action: ApprovalActionType,
    packet_id: uuid.UUID | None,
) -> dict[str, Any]:
    t = case.transaction
    base: dict[str, Any] = {
        "action_type": action.value,
        "case_id": str(case.id),
        "transaction_id": str(t.id),
        "data_origin": t.data_origin.value,
    }
    if action is not ApprovalActionType.EVIDENCE_PACKET_INTERNAL and packet_id is not None:
        raise InvalidActionError("packet_id applies only to evidence packet approvals")
    if action is ApprovalActionType.MANUAL_REVIEW:
        if case.status is CaseStatus.RESOLVED:
            raise ConflictError("Case is already resolved")
        return base | {
            "case_status": case.status.value,
            "case_priority": case.priority.value,
            "effect": "Keep the case in review and raise it to high priority.",
        }
    if action is ApprovalActionType.EVIDENCE_PACKET_INTERNAL:
        if packet_id is None:
            raise InvalidActionError("Choose the evidence packet to approve")
        packet = get_packet(db, case.merchant_id, case.id, packet_id)
        return base | {
            "packet_id": str(packet.id),
            "packet_sha256": packet.sha256,
            "packet_generated_at": packet.created_at.isoformat(),
            "evidence_ids": packet.contents.get("evidence_ids", []),
            "investigation_run_id": packet.contents.get("investigation_run_id"),
            "effect": "Approve this exact packet for internal use. It is not submitted to PayPal.",
        }
    # PREPARE_REFUND: amounts come from the server's own record, never from the client.
    if case.status is CaseStatus.RESOLVED:
        raise ConflictError("Case is already resolved")
    if t.status is not TransactionStatus.CAPTURED:
        raise ConflictError(
            "Only a captured payment can have a refund prepared",
            details={"status": t.status.value},
        )
    executable = t.data_origin is DataOrigin.LIVE_SANDBOX and bool(t.paypal_capture_id)
    return base | {
        "amount_minor": t.amount_minor,
        "currency": t.currency,
        "refund_type": "FULL",
        "paypal_capture_id": t.paypal_capture_id,
        "paypal_executable": executable,
        "paypal_executable_reason": (
            "Live sandbox capture; eligible for execution once Phase 5 enables it."
            if executable
            else f"{t.data_origin.value} payment: there is no PayPal capture to refund."
        ),
        "effect": "Record approved refund intent only. No money moves in this release.",
    }


def create(
    db: Session,
    principal: Principal,
    case_id: uuid.UUID,
    *,
    action: ApprovalActionType,
    justification: str,
    packet_id: uuid.UUID | None = None,
) -> ApprovalRequest:
    case = get_case(db, principal.merchant_id, case_id, lock=True)
    snapshot = _snapshot(db, case, action, packet_id)
    run = latest_completed(db, case.merchant_id, case.id)
    req = ApprovalRequest(
        merchant_id=case.merchant_id,
        case_id=case.id,
        transaction_id=case.transaction_id,
        action_type=action,
        action_snapshot=snapshot,
        snapshot_sha256=snapshot_digest(snapshot),
        required_roles=REQUIRED_ROLES[action],
        justification=justification,
        status=ApprovalStatus.PENDING,
        requested_by_user_id=principal.user.id,
        investigation_run_id=run.id if run else None,
        data_origin=case.data_origin,
    )
    db.add(req)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("A request for this action is already pending on this case") from exc
    audit.record_for_case(
        db,
        case,
        "approval.requested",
        principal.user.id,
        entity_type="approval_request",
        entity_id=req.id,
        action_type=action.value,
        snapshot_sha256=req.snapshot_sha256,
        required_roles=req.required_roles,
    )
    db.commit()
    return get_request(db, principal.merchant_id, case.id, req.id)


def get_request(
    db: Session,
    merchant_id: uuid.UUID,
    case_id: uuid.UUID,
    request_id: uuid.UUID,
    *,
    lock: bool = False,
) -> ApprovalRequest:
    stmt = select(ApprovalRequest).where(
        ApprovalRequest.id == request_id,
        ApprovalRequest.case_id == case_id,
        ApprovalRequest.merchant_id == merchant_id,
    )
    if lock:
        stmt = stmt.with_for_update(of=ApprovalRequest)
    req = db.scalar(stmt)
    if req is None:
        raise NotFoundError("Approval request not found")
    return req


def list_for_case(db: Session, merchant_id: uuid.UUID, case_id: uuid.UUID) -> list[ApprovalRequest]:
    case = get_case(db, merchant_id, case_id)
    return list(
        db.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.case_id == case.id, ApprovalRequest.merchant_id == merchant_id)
            .order_by(ApprovalRequest.created_at.desc())
        ).unique()
    )


def decide(
    db: Session,
    principal: Principal,
    case_id: uuid.UUID,
    request_id: uuid.UUID,
    *,
    decision: ApprovalDecisionValue,
    comment: str,
) -> ApprovalRequest:
    case = get_case(db, principal.merchant_id, case_id, lock=True)
    req = get_request(db, principal.merchant_id, case.id, request_id, lock=True)
    if req.status is not ApprovalStatus.PENDING:
        db.rollback()
        raise ConflictError(
            "This request has already been decided", details={"status": req.status.value}
        )
    if principal.role.value not in req.required_roles:
        db.rollback()
        raise PermissionDeniedError(
            "Your role cannot decide this request", details={"required": req.required_roles}
        )
    if req.requested_by_user_id == principal.user.id:
        db.rollback()
        raise PermissionDeniedError("You cannot decide a request you made yourself")
    if snapshot_digest(req.action_snapshot) != req.snapshot_sha256:
        db.rollback()
        raise ConflictError("The requested action no longer matches its snapshot")

    now = datetime.now(UTC)
    execution: ActionExecution | None = None
    if decision is ApprovalDecisionValue.APPROVED:
        execution = _execute(db, case, req)
    db.add(
        ApprovalDecision(
            approval_request_id=req.id,
            merchant_id=req.merchant_id,
            decision=decision,
            decided_by_user_id=principal.user.id,
            decided_by_role=principal.role,
            comment=comment,
            snapshot_sha256=req.snapshot_sha256,
        )
    )
    req.status = (
        ApprovalStatus.APPROVED
        if decision is ApprovalDecisionValue.APPROVED
        else ApprovalStatus.REJECTED
    )
    req.decided_at = now
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("This request has already been decided") from exc
    audit.record_for_case(
        db,
        case,
        f"approval.{req.status.value.lower()}",
        principal.user.id,
        entity_type="approval_request",
        entity_id=req.id,
        action_type=req.action_type.value,
        snapshot_sha256=req.snapshot_sha256,
        decided_by_role=principal.role.value,
    )
    if execution is not None:
        audit.record_for_case(
            db,
            case,
            "action.execution_recorded",
            principal.user.id,
            entity_type="action_execution",
            entity_id=execution.id,
            action_type=req.action_type.value,
            status=execution.status.value,
            provider_called=False,
        )
    db.commit()
    db.expire_all()
    return get_request(db, principal.merchant_id, case.id, req.id)


def _execute(db: Session, case: Case, req: ApprovalRequest) -> ActionExecution:
    """Backend-side effect of an approval. Never calls a payment provider in Phase 4."""
    snap = req.action_snapshot
    if req.action_type is ApprovalActionType.MANUAL_REVIEW:
        if case.status is CaseStatus.RESOLVED:
            raise ConflictError("Case was resolved after this request was made")
        case.priority = CasePriority.HIGH
        if case.status is CaseStatus.OPEN:
            case.status = CaseStatus.IN_REVIEW
        status, detail = (
            ExecutionStatus.COMPLETED_INTERNAL,
            {"effect": "Case kept in review at high priority."},
        )
    elif req.action_type is ApprovalActionType.EVIDENCE_PACKET_INTERNAL:
        packet = get_packet(db, case.merchant_id, case.id, uuid.UUID(snap["packet_id"]))
        if packet.sha256 != snap["packet_sha256"]:
            raise ConflictError("The evidence packet changed after this request was made")
        status, detail = (
            ExecutionStatus.COMPLETED_INTERNAL,
            {
                "effect": "Packet approved for internal use. Not submitted to PayPal.",
                "packet_id": snap["packet_id"],
                "packet_sha256": snap["packet_sha256"],
            },
        )
    else:
        t = case.transaction
        if t.status is not TransactionStatus.CAPTURED or t.amount_minor != snap["amount_minor"]:
            raise ConflictError("The payment changed after this refund was requested")
        status, detail = (
            ExecutionStatus.NOT_EXECUTED,
            {
                "effect": REFUND_NOT_EXECUTED,
                "amount_minor": snap["amount_minor"],
                "currency": snap["currency"],
                "paypal_executable": snap["paypal_executable"],
            },
        )
    execution = ActionExecution(
        approval_request_id=req.id,
        merchant_id=req.merchant_id,
        action_type=req.action_type,
        status=status,
        provider_called=False,
        detail=detail,
    )
    db.add(execution)
    db.flush()
    return execution
