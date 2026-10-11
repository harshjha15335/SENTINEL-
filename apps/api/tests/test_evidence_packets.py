import hashlib
import io
import uuid

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.main import app
from app.models import EvidenceArtifact, StoredBlob
from app.models.enums import Role
from app.services.storage import DatabaseStorage, LocalStorage, StorageError, check_key, get_storage
from tests.conftest import Tenant
from tests.phase4 import PNG_1PX, client_for, make_case, make_pdf, upload


def test_pdf_upload_is_checked_hashed_and_extracted(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant)
    client, h = client_for(tenant, Role.ANALYST)
    pdf = make_pdf("Invoice 1001\nTotal 42.00 USD")
    resp = upload(client, h, case.id, pdf, category="INVOICE", description="Order invoice")
    assert resp.status_code == 201, resp.text
    ev = resp.json()
    assert ev["sha256"] == hashlib.sha256(pdf).hexdigest()
    assert ev["size_bytes"] == len(pdf)
    assert ev["content_type"] == "application/pdf"
    assert ev["extraction_status"] == "EXTRACTED"
    assert "Invoice 1001" in ev["text_preview"]
    assert ev["data_origin"] == "MERCHANT_PROVIDED"
    assert ev["verified"] is False
    assert ev["page_count"] == 1

    listing = client.get(f"/api/v1/cases/{case.id}/evidence").json()
    assert [i["id"] for i in listing["items"]] == [ev["id"]]
    checklist = {c["key"]: c["provided"] for c in listing["checklist"]}
    assert checklist == {
        "delivery": False,
        "invoice": True,
        "communication": False,
        "policy": False,
    }

    dl = client.get(f"/api/v1/cases/{case.id}/evidence/{ev['id']}/download")
    assert dl.status_code == 200
    assert dl.content == pdf
    assert dl.headers["content-type"] == "application/pdf"
    assert dl.headers["content-disposition"].startswith("attachment;")
    assert "sandbox" in dl.headers["content-security-policy"]
    assert dl.headers["x-content-type-options"] == "nosniff"
    assert dl.headers["cache-control"] == "private, no-store"


def test_image_upload_is_stored_without_ocr(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant)
    client, h = client_for(tenant, Role.ANALYST)
    resp = upload(
        client,
        h,
        case.id,
        PNG_1PX,
        name="label.png",
        content_type="image/png",
        category="SHIPPING_PROOF",
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["extraction_status"] == "NOT_SUPPORTED"
    assert resp.json()["text_preview"] is None


@pytest.mark.parametrize(
    ("data", "name", "ctype", "status"),
    [
        (b"<html><script>alert(1)</script></html>", "x.html", "text/html", 422),
        (b"<svg onload=alert(1)></svg>", "x.svg", "image/svg+xml", 422),
        (PNG_1PX, "invoice.pdf", "application/pdf", 422),  # signature does not match
        (b"%PDF-1.4 not really", "invoice.png", "image/png", 422),  # wrong declared type
        (b"%PDF-1.4\n", "invoice.exe", "application/pdf", 422),  # wrong extension
        (b"", "empty.pdf", "application/pdf", 422),
        (b"%PDF-1.4\n%%garbage", "broken.pdf", "application/pdf", 422),
    ],
)
def test_invalid_files_are_rejected(
    db: Session, tenant: Tenant, data: bytes, name: str, ctype: str, status: int
) -> None:
    case = make_case(db, tenant)
    client, h = client_for(tenant, Role.ANALYST)
    resp = upload(client, h, case.id, data, name=name, content_type=ctype)
    assert resp.status_code == status, resp.text
    assert db.scalar(select(EvidenceArtifact.id)) is None


def test_active_and_encrypted_pdfs_are_rejected(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant)
    client, h = client_for(tenant, Role.ANALYST)
    js = make_pdf("hello").replace(
        b"/Type /Catalog", b"/Type /Catalog /OpenAction << /S /JavaScript /JS (app.alert(1)) >>"
    )
    assert upload(client, h, case.id, js).status_code == 422

    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(make_pdf("secret"))))
    writer.encrypt("pw")
    buf = io.BytesIO()
    writer.write(buf)
    resp = upload(client, h, case.id, buf.getvalue())
    assert resp.status_code == 422
    assert "Encrypted" in resp.json()["error"]["message"]


def test_size_limit(db: Session, tenant: Tenant, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "evidence_max_bytes", 1024)
    case = make_case(db, tenant)
    client, h = client_for(tenant, Role.ANALYST)
    resp = upload(client, h, case.id, make_pdf("x" * 50 + "\n") + b" " * 2048)
    assert resp.status_code == 413


def test_duplicate_upload_conflicts(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant)
    client, h = client_for(tenant, Role.ANALYST)
    pdf = make_pdf("Same file")
    assert upload(client, h, case.id, pdf).status_code == 201
    assert upload(client, h, case.id, pdf).status_code == 409


def test_unsafe_filenames_never_reach_the_filesystem(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant)
    client, h = client_for(tenant, Role.ANALYST)
    resp = upload(client, h, case.id, make_pdf("x"), name="../../../etc/passwd\x00.pdf")
    assert resp.status_code == 201, resp.text
    ev = resp.json()
    name = ev["original_filename"]
    assert name.startswith("passwd") and name.endswith(".pdf")
    assert "/" not in name and ".." not in name and "\x00" not in name
    row = db.get(EvidenceArtifact, uuid.UUID(ev["id"]))
    assert row is not None
    assert row.storage_key.startswith(f"{tenant.merchant.id}/evidence/")
    assert ".." not in row.storage_key and "passwd" not in row.storage_key
    storage = get_storage()
    assert isinstance(storage, LocalStorage)
    for bad in ("../x", f"{tenant.merchant.id}/evidence/../../x", "/etc/passwd", "a/b/c"):
        with pytest.raises(StorageError):
            check_key(bad)
        with pytest.raises(StorageError):
            storage.get(db, bad)


def test_evidence_access_control(db: Session, tenant: Tenant, other_tenant: Tenant) -> None:
    case = make_case(db, tenant)
    other_case = make_case(db, tenant, payer="SYN-PAYER-0002")
    client, h = client_for(tenant, Role.ANALYST)
    ev = upload(client, h, case.id, make_pdf("private")).json()
    url = f"/api/v1/cases/{case.id}/evidence/{ev['id']}/download"

    assert TestClient(app).get(url).status_code == 401
    oc, oh = client_for(other_tenant, Role.ADMIN)
    assert oc.get(url).status_code == 404
    assert upload(oc, oh, case.id, make_pdf("intrude")).status_code == 404
    # Right merchant, wrong case path: not found.
    assert (
        client.get(f"/api/v1/cases/{other_case.id}/evidence/{ev['id']}/download").status_code == 404
    )

    viewer, vh = client_for(tenant, Role.VIEWER)
    assert upload(viewer, vh, case.id, make_pdf("viewer")).status_code == 403
    assert viewer.get(url).status_code == 200


def test_database_storage_backend(db: Session) -> None:
    store = DatabaseStorage()
    key = f"{uuid.uuid4()}/evidence/{uuid.uuid4()}"
    store.put(db, key, b"bytes")
    db.commit()
    assert store.get(db, key) == b"bytes"
    store.delete(db, key)
    db.commit()
    assert db.scalar(select(StoredBlob.key)) is None
    with pytest.raises(StorageError):
        store.get(db, key)


def test_evidence_packet_generation_and_download(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant)
    client, h = client_for(tenant, Role.ANALYST)
    upload(
        client, h, case.id, make_pdf("Invoice <b>1001</b> & co"), description="<script>x</script>"
    )
    client.post(
        f"/api/v1/cases/{case.id}/notes", json={"body": "Note with <i>markup</i>"}, headers=h
    )
    run = client.post(f"/api/v1/cases/{case.id}/investigations", json={}, headers=h).json()

    resp = client.post(f"/api/v1/cases/{case.id}/packets", headers=h)
    assert resp.status_code == 201, resp.text
    packet = resp.json()
    assert packet["submitted_to_paypal"] is False
    assert packet["investigation_run_id"] == run["id"]
    assert packet["contents"]["data_origin"] == "SYNTHETIC_DEMO"
    assert len(packet["contents"]["evidence_ids"]) == 1

    dl = client.get(f"/api/v1/cases/{case.id}/packets/{packet['id']}/download")
    assert dl.status_code == 200
    assert dl.headers["content-type"] == "application/pdf"
    assert hashlib.sha256(dl.content).hexdigest() == packet["sha256"]
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(dl.content)).pages)
    flat = " ".join(text.split())
    assert "not been submitted to PayPal" in flat
    assert "Synthetic demo" in flat
    assert "Deterministic summary" in flat
    assert "Evidence inventory" in flat
    assert "Human review status" in flat
    assert "No financial action has been executed" in flat
    # Nothing SENTINEL does not hold is invented.
    assert "No shipping, delivery or buyer-contact events exist unless listed here" in flat

    listing = client.get(f"/api/v1/cases/{case.id}/packets").json()
    assert [p["id"] for p in listing] == [packet["id"]]

    viewer, vh = client_for(tenant, Role.VIEWER)
    assert viewer.post(f"/api/v1/cases/{case.id}/packets", headers=vh).status_code == 403
    assert viewer.get(f"/api/v1/cases/{case.id}/packets/{packet['id']}/download").status_code == 200


def test_packet_is_not_downloadable_across_merchants(
    db: Session, tenant: Tenant, other_tenant: Tenant
) -> None:
    case = make_case(db, tenant)
    client, h = client_for(tenant, Role.ANALYST)
    packet = client.post(f"/api/v1/cases/{case.id}/packets", headers=h).json()
    oc, _ = client_for(other_tenant, Role.ADMIN)
    assert oc.get(f"/api/v1/cases/{case.id}/packets/{packet['id']}/download").status_code == 404
    assert (
        TestClient(app).get(f"/api/v1/cases/{case.id}/packets/{packet['id']}/download").status_code
        == 401
    )
