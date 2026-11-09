import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import correlation_id_var, redact
from app.models import AuditEvent


def record(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | uuid.UUID | None,
    merchant_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
    actor_type: str = "USER",
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        merchant_id=merchant_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        correlation_id=correlation_id_var.get(),
        metadata_=redact(metadata or {}),
    )
    db.add(event)
    return event


def record_for_case(
    db: Session,
    case: Any,
    action: str,
    actor_id: uuid.UUID | None,
    *,
    entity_type: str,
    entity_id: str | uuid.UUID,
    **meta: object,
) -> AuditEvent:
    """Audit an action on a record that belongs to a case, so the case timeline can show it.

    Callers pass identifiers, hashes, sizes and enum values only: never free text written by a
    user, uploaded content or model output.
    """
    return record(
        db,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        merchant_id=case.merchant_id,
        actor_id=actor_id,
        actor_type="USER" if actor_id else "SYSTEM",
        metadata={"case_id": str(case.id), "transaction_id": str(case.transaction_id), **meta},
    )
