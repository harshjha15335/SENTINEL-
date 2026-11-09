"""Validation and text extraction for merchant-uploaded evidence.

Uploaded files are untrusted. We accept a deliberately small set of formats, check the declared
type, the extension and the file signature agree, refuse PDFs with active content, and extract
plain text only (no rendering, no OCR). Acceptance says nothing about a document's authenticity.
"""

import hashlib
import io
import logging
import re
import unicodedata
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.errors import DomainError
from app.models.enums import ExtractionStatus

log = logging.getLogger(__name__)

PDF = "application/pdf"
PNG = "image/png"
JPEG = "image/jpeg"

ALLOWED: dict[str, tuple[str, ...]] = {
    PDF: (".pdf",),
    PNG: (".png",),
    JPEG: (".jpg", ".jpeg"),
}
MAX_PDF_PAGES = 50
# Names that mark executable or embedded content in a PDF. A plain-text scan is a heuristic
# (compressed object streams can hide them); it is one layer, not a guarantee.
_PDF_ACTIVE = (
    b"/JavaScript",
    b"/JS ",
    b"/JS(",
    b"/JS<",
    b"/Launch",
    b"/EmbeddedFile",
    b"/XFA",
    b"/RichMedia",
)
_FILENAME_OK = re.compile(r"[^A-Za-z0-9 ._()\-]")


class EvidenceValidationError(DomainError):
    status_code = 422
    code = "invalid_evidence"


class EvidenceTooLargeError(DomainError):
    status_code = 413
    code = "evidence_too_large"


@dataclass(frozen=True)
class Inspected:
    content_type: str
    filename: str
    sha256: str
    size_bytes: int
    extraction_status: ExtractionStatus
    extraction_note: str | None
    text: str | None
    page_count: int | None


def safe_filename(raw: str | None) -> str:
    """Display name only. Never used to build a storage path."""
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(c for c in name if unicodedata.category(c)[0] != "C")
    name = _FILENAME_OK.sub("_", name).strip(" .")
    return (name or "evidence")[:120]


def sniff(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return PDF
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if data.startswith(b"\xff\xd8\xff"):
        return JPEG
    return None


def clean_text(text: str, limit: int) -> str:
    # Drop control characters (except newlines/tabs) and collapse runs of blank space.
    text = "".join(c for c in text if c in "\n\t" or unicodedata.category(c)[0] != "C")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:limit]


def inspect_upload(
    data: bytes, *, declared_type: str | None, filename: str | None, max_bytes: int, max_chars: int
) -> Inspected:
    if len(data) == 0:
        raise EvidenceValidationError("The file is empty")
    if len(data) > max_bytes:
        raise EvidenceTooLargeError(
            f"Files may be at most {max_bytes // (1024 * 1024)} MB",
            details={"max_bytes": max_bytes},
        )
    declared = (declared_type or "").split(";")[0].strip().lower()
    if declared not in ALLOWED:
        raise EvidenceValidationError(
            "Only PDF, PNG and JPEG files are accepted", details={"allowed": sorted(ALLOWED)}
        )
    name = safe_filename(filename)
    if not name.lower().endswith(ALLOWED[declared]):
        raise EvidenceValidationError("The file extension does not match its declared type")
    detected = sniff(data)
    if detected != declared:
        raise EvidenceValidationError("The file contents do not match its declared type")

    sha = hashlib.sha256(data).hexdigest()
    if detected == PDF:
        status, note, text, pages = _pdf_text(data, max_chars)
    else:
        status, note, text, pages = (
            ExtractionStatus.NOT_SUPPORTED,
            "Image stored as-is. SENTINEL does not read text from images (no OCR).",
            None,
            None,
        )
    return Inspected(detected, name, sha, len(data), status, note, text, pages)


def _pdf_text(
    data: bytes, max_chars: int
) -> tuple[ExtractionStatus, str | None, str | None, int | None]:
    if any(marker in data for marker in _PDF_ACTIVE):
        raise EvidenceValidationError(
            "PDFs with scripts, launch actions, forms (XFA) or embedded files are not accepted"
        )
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise EvidenceValidationError("Encrypted or password-protected PDFs are not accepted")
        pages = len(reader.pages)
    except EvidenceValidationError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError) as exc:
        raise EvidenceValidationError("The PDF could not be read") from exc

    chunks: list[str] = []
    failed = 0
    for page in reader.pages[:MAX_PDF_PAGES]:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            failed += 1
        if sum(len(c) for c in chunks) > max_chars:
            break
    text = clean_text("\n\n".join(chunks), max_chars)
    notes = []
    if pages > MAX_PDF_PAGES:
        notes.append(f"Text read from the first {MAX_PDF_PAGES} of {pages} pages.")
    if failed:
        notes.append(f"Text could not be read from {failed} page(s).")
    if len(text) >= max_chars:
        notes.append(f"Extracted text truncated at {max_chars} characters.")
    if not text:
        status = ExtractionStatus.FAILED if failed else ExtractionStatus.NO_TEXT
        notes.append("No text layer found (scanned documents are not OCR'd).")
        return status, " ".join(notes), None, pages
    return ExtractionStatus.EXTRACTED, " ".join(notes) or None, text, pages
