"""Read-only provider synchronization and grounded response preparation.

No submit/evidence-upload/refund gateway operation is reachable from this module. Provider
records are imported only by matching the seller transaction ID to a merchant-owned capture.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import Principal
from app.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ProviderUnavailableError,
)
from app.models import Case, EvidenceArtifact, Transaction, User
from app.models.disputes import Dispute, DisputeDraft
from app.models.enums import DataOrigin, Role
from app.schemas.disputes import DisputeChecklistOut
from app.services import audit, cases
from app.services.investigation.toolbox import evidence_checklist
from app.services.paypal.gateway import PayPalGateway
from app.services.paypal.types import PayPalError


def get_dispute(
    db: Session, merchant_id: uuid.UUID, identity: uuid.UUID, *, lock: bool = False
) -> Dispute:
    query = select(Dispute).where(Dispute.id == identity, Dispute.merchant_id == merchant_id)
    if lock:
        query = query.with_for_update()
    item = db.scalar(query)
    if item is None:
        raise NotFoundError("Dispute not found")
    return item


def create_demo(db: Session, principal: Principal, case_id: uuid.UUID, reason: str) -> Dispute:
    case = cases.get_case(db, principal.merchant_id, case_id, lock=True)
    if case.data_origin not in (DataOrigin.SIMULATED, DataOrigin.SYNTHETIC_DEMO):
        raise ConflictError("Demonstration disputes require a simulated or synthetic case")
    existing = db.scalar(
        select(Dispute).where(Dispute.case_id == case.id, Dispute.provider_dispute_id.is_(None))
    )
    if existing:
        return existing
    item = Dispute(
        merchant_id=principal.merchant_id,
        transaction_id=case.transaction_id,
        case_id=case.id,
        reason=reason,
        status="DEMO_OPEN",
        stage="DEMO_INQUIRY",
        response_due_at=datetime.now(UTC) + timedelta(days=7),
        data_origin=case.data_origin,
    )
    db.add(item)
    db.flush()
    audit.record_for_case(
        db,
        case,
        "dispute.demo.created",
        principal.user.id,
        entity_type="dispute",
        entity_id=item.id,
        reason=reason,
    )
    db.commit()
    return item


def checklist(db: Session, item: Dispute) -> list[DisputeChecklistOut]:
    rows = list(
        db.scalars(
            select(EvidenceArtifact).where(
                EvidenceArtifact.case_id == item.case_id,
                EvidenceArtifact.merchant_id == item.merchant_id,
            )
        )
    )
    return [DisputeChecklistOut.model_validate(row) for row in evidence_checklist(rows)]


def draft(db: Session, principal: Principal, identity: uuid.UUID) -> DisputeDraft:
    item = get_dispute(db, principal.merchant_id, identity, lock=True)
    txn = db.scalar(
        select(Transaction).where(
            Transaction.id == item.transaction_id, Transaction.merchant_id == principal.merchant_id
        )
    )
    if txn is None:
        raise NotFoundError("Linked payment not found")
    artifacts = list(
        db.scalars(
            select(EvidenceArtifact)
            .where(
                EvidenceArtifact.case_id == item.case_id,
                EvidenceArtifact.merchant_id == principal.merchant_id,
            )
            .order_by(EvidenceArtifact.created_at)
        )
    )
    missing = [row.label for row in checklist(db, item) if not row.provided]
    cites: list[dict[str, Any]] = [
        {"kind": "dispute", "id": str(item.id)},
        {"kind": "transaction", "id": str(txn.id)},
    ]
    text = [
        "DETERMINISTIC DRAFT — NOT SUBMITTED. Human review required.",
        (
            f"Recorded dispute reason: {item.reason}; stage: {item.stage}; "
            f"status: {item.status}. [dispute:{item.id}]"
        ),
        (
            f"The linked payment record is {txn.status.value}, "
            f"amount {txn.amount_minor} minor units "
            f"{txn.currency}, origin {txn.data_origin.value}. [transaction:{txn.id}]"
        ),
        "A stored payment status is not proof of delivery, customer acceptance "
        "or final settlement.",
    ]
    for artifact in artifacts:
        cites.append({"kind": "evidence", "id": str(artifact.id), "sha256": artifact.sha256})
        text.append(
            f"Attachment {artifact.id}: uploader-declared category {artifact.category.value}; "
            f"SHA-256 {artifact.sha256}. This file is unverified. [evidence:{artifact.id}]"
        )
    text.append(
        "Further merchant response requires checking the actual documents and the "
        "provider's requirements for this reason/stage."
    )
    if missing:
        text.append(
            "Missing uploader-declared categories: "
            + "; ".join(missing)
            + ". No missing proof is inferred or invented."
        )
    item_draft = DisputeDraft(
        dispute_id=item.id,
        merchant_id=principal.merchant_id,
        created_by_user_id=principal.user.id,
        body="\n\n".join(text),
        citations=cites,
        missing_information=missing,
    )
    db.add(item_draft)
    db.flush()
    case = cases.get_case(db, principal.merchant_id, item.case_id)
    audit.record_for_case(
        db,
        case,
        "dispute.draft.created",
        principal.user.id,
        entity_type="dispute_draft",
        entity_id=item_draft.id,
        dispute_id=str(item.id),
        generated_by_ai=False,
    )
    db.commit()
    return item_draft


def assign(
    db: Session, principal: Principal, identity: uuid.UUID, user_id: uuid.UUID | None
) -> Dispute:
    item = get_dispute(db, principal.merchant_id, identity, lock=True)
    if user_id is not None:
        assignee = db.scalar(
            select(User).where(
                User.id == user_id,
                User.merchant_id == principal.merchant_id,
                User.role.in_([Role.ADMIN, Role.ANALYST]),
            )
        )
        if assignee is None:
            raise NotFoundError("Authorized assignee not found")
    item.assigned_user_id = user_id
    audit.record_for_case(
        db,
        cases.get_case(db, principal.merchant_id, item.case_id),
        "dispute.assigned",
        principal.user.id,
        entity_type="dispute",
        entity_id=item.id,
        assigned_user_id=str(user_id) if user_id else None,
    )
    db.commit()
    return item


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except ValueError:
        return None


def sync(db: Session, principal: Principal, gateway: PayPalGateway) -> int:
    if gateway.data_origin is not DataOrigin.LIVE_SANDBOX:
        raise ConflictError(
            "Read-only synchronization requires the sandbox gateway; "
            "use explicit demo disputes offline"
        )
    try:
        response = gateway.list_disputes(page_size=20)
    except PayPalError as exc:
        raise ProviderUnavailableError(
            "Read-only dispute synchronization unavailable", details={"category": exc.kind.value}
        ) from None
    rows = response.get("items", [])
    if not isinstance(rows, list):
        raise ProviderUnavailableError("Provider dispute response shape is invalid")
    imported = 0
    for row in rows[:20]:
        if not isinstance(row, dict) or not isinstance(row.get("dispute_id"), str):
            continue
        provider_id = row["dispute_id"]
        if len(provider_id) > 128 or not provider_id:
            continue
        references = row.get("disputed_transactions", [])
        if not isinstance(references, list):
            continue
        capture_ids = [
            ref["seller_transaction_id"]
            for ref in references
            if isinstance(ref, dict) and isinstance(ref.get("seller_transaction_id"), str)
        ]
        if not capture_ids:
            continue
        matched = list(
            db.scalars(
                select(Transaction)
                .where(
                    Transaction.merchant_id == principal.merchant_id,
                    Transaction.data_origin == DataOrigin.LIVE_SANDBOX,
                    Transaction.paypal_capture_id.in_(capture_ids),
                )
                .limit(2)
                .with_for_update(of=Transaction)
            ).unique()
        )
        # Multi-payment disputes need a dedicated allocation model. Do not silently map
        # an arbitrary first payment or mix evidence from multiple cases.
        if len(matched) != 1:
            continue
        txn = matched[0]
        case = db.scalar(
            select(Case)
            .where(Case.transaction_id == txn.id, Case.merchant_id == principal.merchant_id)
            .order_by(Case.created_at.desc())
            .limit(1)
        )
        if case is None and str(row.get("status", "UNKNOWN")) in ("RESOLVED", "CLOSED"):
            continue
        if case is None:
            case = cases.open_manual(
                db, principal, txn.id, reason="Provider dispute linked to owned sandbox capture"
            )
        item = db.scalar(
            select(Dispute).where(
                Dispute.merchant_id == principal.merchant_id,
                Dispute.provider_dispute_id == provider_id,
            )
        )
        if item is not None and item.transaction_id != txn.id:
            raise ConflictError(
                "Provider dispute mapping conflicts with the existing owned capture"
            )
        if item is None:
            item = Dispute(
                merchant_id=principal.merchant_id,
                transaction_id=txn.id,
                case_id=case.id,
                provider_dispute_id=provider_id,
                data_origin=DataOrigin.LIVE_SANDBOX,
            )
            db.add(item)
        item.reason = str(row.get("reason", "UNKNOWN"))[:128]
        item.status = str(row.get("status", "UNKNOWN"))[:64]
        item.stage = str(row.get("dispute_life_cycle_stage", "UNKNOWN"))[:64]
        item.response_due_at = _timestamp(row.get("seller_response_due_date"))
        item.last_synced_at = datetime.now(UTC)
        db.flush()
        audit.record_for_case(
            db,
            case,
            "dispute.synchronized",
            principal.user.id,
            entity_type="dispute",
            entity_id=item.id,
        )
        imported += 1
    db.commit()
    return imported


def reject_submission() -> None:
    raise PermissionDeniedError(
        "External dispute submission is disabled; export and independent human review only"
    )
