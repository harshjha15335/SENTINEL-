"""Evidence upload, listing and authorised download for a case."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import Principal
from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError
from app.models import EvidenceArtifact
from app.models.enums import DataOrigin, EvidenceCategory
from app.services import audit
from app.services.cases import get_case
from app.services.evidence.ingest import inspect_upload
from app.services.storage import get_storage, new_key, storage_for


def upload(
    db: Session,
    principal: Principal,
    case_id: uuid.UUID,
    *,
    data: bytes,
    declared_type: str | None,
    filename: str | None,
    category: EvidenceCategory,
    description: str,
) -> EvidenceArtifact:
    case = get_case(db, principal.merchant_id, case_id)
    settings = get_settings()
    info = inspect_upload(
        data,
        declared_type=declared_type,
        filename=filename,
        max_bytes=settings.evidence_max_bytes,
        max_chars=settings.evidence_max_text_chars,
    )
    duplicate = db.scalar(
        select(EvidenceArtifact.id).where(
            EvidenceArtifact.case_id == case.id, EvidenceArtifact.sha256 == info.sha256
        )
    )
    if duplicate is not None:
        raise ConflictError(
            "This file is already attached to the case", details={"evidence_id": str(duplicate)}
        )
    storage = get_storage()
    key = new_key(principal.merchant_id, "evidence")
    artifact = EvidenceArtifact(
        merchant_id=case.merchant_id,
        case_id=case.id,
        uploaded_by_user_id=principal.user.id,
        category=category,
        description=description,
        original_filename=info.filename,
        content_type=info.content_type,
        size_bytes=info.size_bytes,
        sha256=info.sha256,
        storage_backend=storage.name,
        storage_key=key,
        extraction_status=info.extraction_status,
        extraction_note=info.extraction_note,
        extracted_text=info.text,
        page_count=info.page_count,
        data_origin=DataOrigin.MERCHANT_PROVIDED,
    )
    db.add(artifact)
    try:
        db.flush()
        storage.put(db, key, data)
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("This file is already attached to the case") from exc
    # Filename, description and extracted text stay out of the audit log.
    audit.record_for_case(
        db,
        case,
        "evidence.uploaded",
        principal.user.id,
        entity_type="evidence",
        entity_id=artifact.id,
        sha256=info.sha256,
        size_bytes=info.size_bytes,
        content_type=info.content_type,
        category=category.value,
        extraction_status=info.extraction_status.value,
    )
    try:
        db.commit()
    except Exception:
        storage.delete(db, key)
        raise
    return artifact


def list_for_case(
    db: Session, merchant_id: uuid.UUID, case_id: uuid.UUID
) -> list[EvidenceArtifact]:
    case = get_case(db, merchant_id, case_id)
    return list(
        db.scalars(
            select(EvidenceArtifact)
            .where(
                EvidenceArtifact.case_id == case.id,
                EvidenceArtifact.merchant_id == merchant_id,
            )
            .order_by(EvidenceArtifact.created_at)
        ).unique()
    )


def get_artifact(
    db: Session, merchant_id: uuid.UUID, case_id: uuid.UUID, evidence_id: uuid.UUID
) -> EvidenceArtifact:
    artifact = db.scalar(
        select(EvidenceArtifact).where(
            EvidenceArtifact.id == evidence_id,
            EvidenceArtifact.case_id == case_id,
            EvidenceArtifact.merchant_id == merchant_id,
        )
    )
    if artifact is None:
        raise NotFoundError("Evidence not found")
    return artifact


def read_for_download(
    db: Session, principal: Principal, case_id: uuid.UUID, evidence_id: uuid.UUID
) -> tuple[EvidenceArtifact, bytes]:
    case = get_case(db, principal.merchant_id, case_id)
    artifact = get_artifact(db, principal.merchant_id, case.id, evidence_id)
    data = storage_for(artifact.storage_backend).get(db, artifact.storage_key)
    audit.record_for_case(
        db,
        case,
        "evidence.downloaded",
        principal.user.id,
        entity_type="evidence",
        entity_id=artifact.id,
        sha256=artifact.sha256,
    )
    db.commit()
    return artifact, data
