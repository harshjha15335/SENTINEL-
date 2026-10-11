"""Case investigation workbench routes: investigations, evidence, packets and approvals.

Every route loads the case through the principal's merchant first, so a case id from another
merchant is a 404 everywhere. Mutations need ADMIN or ANALYST and the CSRF header.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import Principal, any_member, operator
from app.core.config import get_settings
from app.core.errors import ConflictError
from app.db.session import get_db
from app.models import ApprovalRequest, EvidenceArtifact, EvidencePacket, InvestigationRun
from app.models.enums import (
    ApprovalDecisionValue,
    EvidenceCategory,
    InvestigationMode,
    InvestigationStatus,
)
from app.schemas.api import (
    AIStatusOut,
    ApprovalRequestOut,
    ChecklistItemOut,
    CreateApprovalRequest,
    DecideApprovalRequest,
    EvidenceListOut,
    EvidenceOut,
    EvidencePacketOut,
    InvestigationRunOut,
    StartInvestigationRequest,
)
from app.services import approvals, packets
from app.services.evidence import service as evidence
from app.services.evidence.ingest import ALLOWED
from app.services.investigation import provider, runner
from app.services.investigation.deterministic import (
    DETERMINISTIC_CHOSEN_LABEL,
    DETERMINISTIC_LABEL,
)
from app.services.investigation.schemas import InvestigationFindings
from app.services.investigation.toolbox import evidence_checklist

router = APIRouter(tags=["investigations"])
case_router = APIRouter(prefix="/cases/{case_id}", tags=["investigations"])

AI_LABEL = "AI-generated analysis"


def run_out(run: InvestigationRun) -> InvestigationRunOut:
    if run.mode is InvestigationMode.AI_AGENT:
        label = AI_LABEL
    elif (run.usage or {}).get("deterministic_reason") == "requested":
        label = DETERMINISTIC_CHOSEN_LABEL
    else:
        label = DETERMINISTIC_LABEL
    return InvestigationRunOut(
        id=run.id,
        case_id=run.case_id,
        status=run.status,
        mode=run.mode,
        label=label,
        generated_by_ai=run.mode is InvestigationMode.AI_AGENT,
        provider=run.provider,
        model_name=run.model_name,
        prompt_version=run.prompt_version,
        findings=InvestigationFindings.model_validate(run.findings) if run.findings else None,
        tool_calls=run.tool_calls,  # type: ignore[arg-type]
        source_refs=run.source_refs,  # type: ignore[arg-type]
        usage={k: v for k, v in (run.usage or {}).items()},
        error_category=run.error_category,
        error_message=run.error_message,
        data_origin=run.data_origin,
        initiated_by=run.initiated_by,  # type: ignore[arg-type]
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_ms=run.duration_ms,
    )


def evidence_out(e: EvidenceArtifact) -> EvidenceOut:
    return EvidenceOut(
        id=e.id,
        case_id=e.case_id,
        category=e.category,
        description=e.description,
        original_filename=e.original_filename,
        content_type=e.content_type,
        size_bytes=e.size_bytes,
        sha256=e.sha256,
        extraction_status=e.extraction_status,
        extraction_note=e.extraction_note,
        page_count=e.page_count,
        text_preview=(e.extracted_text or "")[:600] or None,
        data_origin=e.data_origin,
        uploaded_by=e.uploaded_by,  # type: ignore[arg-type]
        created_at=e.created_at,
    )


def packet_out(p: EvidencePacket) -> EvidencePacketOut:
    return EvidencePacketOut.model_validate(p)


def approval_out(a: ApprovalRequest) -> ApprovalRequestOut:
    return ApprovalRequestOut.model_validate(a)


def _download(data: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
            # If a browser ever renders the file inline, it gets no script or network access.
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )


@router.get("/ai/status", response_model=AIStatusOut)
def ai_status(principal: Principal = Depends(any_member)) -> AIStatusOut:
    return AIStatusOut.model_validate(provider.status())


# -- investigations ---------------------------------------------------------------------------


@case_router.post("/investigations", response_model=InvestigationRunOut, status_code=202)
def start_investigation(
    case_id: uuid.UUID,
    background: BackgroundTasks,
    body: StartInvestigationRequest | None = None,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> InvestigationRunOut:
    deterministic = body is not None and body.mode == "deterministic"
    run = runner.start(db, principal, case_id, deterministic=deterministic)
    background.add_task(runner.execute, run.id)
    return run_out(run)


@case_router.get("/investigations", response_model=list[InvestigationRunOut])
def list_investigations(
    case_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> list[InvestigationRunOut]:
    return [run_out(r) for r in runner.list_runs(db, principal.merchant_id, case_id)]


@case_router.get("/investigations/{run_id}", response_model=InvestigationRunOut)
def get_investigation(
    case_id: uuid.UUID,
    run_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> InvestigationRunOut:
    return run_out(runner.get_run(db, principal.merchant_id, case_id, run_id))


@case_router.get("/investigations/{run_id}/findings", response_model=InvestigationFindings)
def get_findings(
    case_id: uuid.UUID,
    run_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> InvestigationFindings:
    run = runner.get_run(db, principal.merchant_id, case_id, run_id)
    if run.status is not InvestigationStatus.COMPLETED or run.findings is None:
        raise ConflictError(
            "This investigation has no findings", details={"status": run.status.value}
        )
    return InvestigationFindings.model_validate(run.findings)


# -- evidence ---------------------------------------------------------------------------------


@case_router.post("/evidence", response_model=EvidenceOut, status_code=201)
def upload_evidence(
    case_id: uuid.UUID,
    file: UploadFile = File(...),
    category: EvidenceCategory = Form(...),
    description: str = Form("", max_length=1000),
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    limit = get_settings().evidence_max_bytes
    data = file.file.read(limit + 1)  # never read more than one byte past the limit
    artifact = evidence.upload(
        db,
        principal,
        case_id,
        data=data,
        declared_type=file.content_type,
        filename=file.filename,
        category=category,
        description=description.strip(),
    )
    return evidence_out(artifact)


@case_router.get("/evidence", response_model=EvidenceListOut)
def list_evidence(
    case_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> EvidenceListOut:
    items = evidence.list_for_case(db, principal.merchant_id, case_id)
    return EvidenceListOut(
        items=[evidence_out(e) for e in items],
        checklist=[ChecklistItemOut.model_validate(c) for c in evidence_checklist(items)],
        max_bytes=get_settings().evidence_max_bytes,
        accepted_types=sorted(ALLOWED),
    )


@case_router.get(
    "/evidence/{evidence_id}/download",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def download_evidence(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> Response:
    artifact, data = evidence.read_for_download(db, principal, case_id, evidence_id)
    return _download(data, artifact.content_type, artifact.original_filename)


# -- evidence packets -------------------------------------------------------------------------


@case_router.post("/packets", response_model=EvidencePacketOut, status_code=201)
def generate_packet(
    case_id: uuid.UUID,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> EvidencePacketOut:
    return packet_out(packets.generate(db, principal, case_id))


@case_router.get("/packets", response_model=list[EvidencePacketOut])
def list_packets(
    case_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> list[EvidencePacketOut]:
    return [packet_out(p) for p in packets.list_for_case(db, principal.merchant_id, case_id)]


@case_router.get(
    "/packets/{packet_id}/download",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def download_packet(
    case_id: uuid.UUID,
    packet_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> Response:
    packet, data = packets.read_for_download(db, principal, case_id, packet_id)
    stamp = packet.created_at.strftime("%Y%m%d-%H%M%S")
    return _download(data, "application/pdf", f"sentinel-packet-{stamp}.pdf")


# -- approvals --------------------------------------------------------------------------------


@case_router.post("/approvals", response_model=ApprovalRequestOut, status_code=201)
def create_approval(
    case_id: uuid.UUID,
    body: CreateApprovalRequest,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> ApprovalRequestOut:
    req = approvals.create(
        db,
        principal,
        case_id,
        action=body.action_type,
        justification=body.justification.strip(),
        packet_id=body.packet_id,
    )
    return approval_out(req)


@case_router.get("/approvals", response_model=list[ApprovalRequestOut])
def list_approvals(
    case_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> list[ApprovalRequestOut]:
    return [approval_out(a) for a in approvals.list_for_case(db, principal.merchant_id, case_id)]


def _decide(
    db: Session,
    principal: Principal,
    case_id: uuid.UUID,
    approval_id: uuid.UUID,
    decision: ApprovalDecisionValue,
    body: DecideApprovalRequest,
) -> ApprovalRequestOut:
    req = approvals.decide(
        db, principal, case_id, approval_id, decision=decision, comment=body.comment.strip()
    )
    return approval_out(req)


@case_router.post("/approvals/{approval_id}/approve", response_model=ApprovalRequestOut)
def approve(
    case_id: uuid.UUID,
    approval_id: uuid.UUID,
    body: DecideApprovalRequest,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> ApprovalRequestOut:
    return _decide(db, principal, case_id, approval_id, ApprovalDecisionValue.APPROVED, body)


@case_router.post("/approvals/{approval_id}/reject", response_model=ApprovalRequestOut)
def reject(
    case_id: uuid.UUID,
    approval_id: uuid.UUID,
    body: DecideApprovalRequest,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> ApprovalRequestOut:
    return _decide(db, principal, case_id, approval_id, ApprovalDecisionValue.REJECTED, body)


router.include_router(case_router)
