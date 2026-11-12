"""Bounded local upload intake tests: no external traffic or exhaustion load."""

import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest
import starlette.formparsers

from app.core.config import get_settings
from app.main import app
from app.models.enums import Role
from tests.conftest import login
from tests.phase4 import make_case, make_pdf


def multipart(data: bytes, *, extra_file: bool = False) -> bytes:
    body = (
        b'--audit\r\nContent-Disposition: form-data; name="category"\r\n\r\nINVOICE\r\n'
        b'--audit\r\nContent-Disposition: form-data; name="file"; filename="a.pdf"\r\n'
        b"Content-Type: application/pdf\r\n\r\n" + data + b"\r\n"
    )
    if extra_file:
        body += (
            b'--audit\r\nContent-Disposition: form-data; name="file"; filename="b.pdf"\r\n'
            b"Content-Type: application/pdf\r\n\r\n" + data + b"\r\n"
        )
    return body + b"--audit--\r\n"


@pytest.fixture
def spools(monkeypatch):
    original = starlette.formparsers.SpooledTemporaryFile
    records = []

    def create(*args, **kwargs):
        file = original(*args, **kwargs)
        file.audit_bytes_written = 0
        original_write = file.write

        def write(data):
            file.audit_bytes_written += len(data)
            return original_write(data)

        file.write = write
        records.append(file)
        return file

    monkeypatch.setattr(starlette.formparsers, "SpooledTemporaryFile", create)
    return records


def streamed(client, url, headers, body, *, disconnect=False):
    async def run():
        async def chunks() -> AsyncIterator[bytes]:
            for start in range(0, len(body), 512):
                yield body[start : start + 512]
                if disconnect and start > 1024:
                    raise RuntimeError("local interrupted upload")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            cookies=dict(client.cookies),
        ) as c:
            return await c.post(url, headers=headers, content=chunks())

    return asyncio.run(run())


@pytest.mark.parametrize("auth", ["missing", "invalid", "csrf", "viewer"])
def test_rejects_unauthorized_before_creating_tempfile(app_client, tenant, db, spools, auth):
    case = make_case(db, tenant)
    headers = {}
    if auth in ("csrf", "viewer"):
        csrf = login(
            app_client, tenant.users[Role.VIEWER if auth == "viewer" else Role.ANALYST].email
        )
        if auth == "viewer":
            headers["X-CSRF-Token"] = csrf
    elif auth == "invalid":
        app_client.cookies.set("sentinel_session", "invalid-token")
    response = app_client.post(
        f"/api/v1/cases/{case.id}/evidence",
        headers=headers,
        data={"category": "INVOICE"},
        files={"file": ("a.pdf", b"0" * (11 * 1024 * 1024))},
    )
    assert response.status_code == (403 if auth in ("csrf", "viewer") else 401)
    assert spools == []


@pytest.mark.parametrize("declared", [None, "0", "1", "999999999"])
def test_stream_size_bound_does_not_trust_length(
    app_client, tenant, db, monkeypatch, spools, declared
):
    monkeypatch.setattr(get_settings(), "evidence_max_bytes", 4096)
    case = make_case(db, tenant)
    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    headers = {"X-CSRF-Token": csrf, "Content-Type": "multipart/form-data; boundary=audit"}
    if declared is not None:
        headers["Content-Length"] = declared
    response = streamed(
        app_client, f"/api/v1/cases/{case.id}/evidence", headers, multipart(b"0" * 8192)
    )
    assert response.status_code == 413, response.text
    assert all(f.closed and f.audit_bytes_written <= 4096 for f in spools)


@pytest.mark.parametrize("delta,expected", [(-1, 201), (0, 201), (1, 413)])
def test_exact_file_boundary_and_cleanup(
    app_client, tenant, db, monkeypatch, spools, delta, expected
):
    pdf = make_pdf("bounded evidence")
    monkeypatch.setattr(get_settings(), "evidence_max_bytes", len(pdf) - delta)
    case = make_case(db, tenant)
    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    response = streamed(
        app_client,
        f"/api/v1/cases/{case.id}/evidence",
        {"X-CSRF-Token": csrf, "Content-Type": "multipart/form-data; boundary=audit"},
        multipart(pdf),
    )
    assert response.status_code == expected, response.text
    assert spools and all(f.closed for f in spools)


def test_multiple_files_rejected_and_cleaned(app_client, tenant, db, spools):
    case = make_case(db, tenant)
    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    response = streamed(
        app_client,
        f"/api/v1/cases/{case.id}/evidence",
        {"X-CSRF-Token": csrf, "Content-Type": "multipart/form-data; boundary=audit"},
        multipart(make_pdf("one file only"), extra_file=True),
    )
    assert response.status_code == 400
    assert spools and all(f.closed for f in spools)


def test_interrupted_stream_closes_tempfiles(app_client, tenant, db, spools):
    case = make_case(db, tenant)
    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    with pytest.raises(BaseExceptionGroup) as caught:
        streamed(
            app_client,
            f"/api/v1/cases/{case.id}/evidence",
            {"X-CSRF-Token": csrf, "Content-Type": "multipart/form-data; boundary=audit"},
            multipart(b"0" * 8192),
            disconnect=True,
        )
    assert (
        caught.value.subgroup(
            lambda exc: isinstance(exc, RuntimeError) and "interrupted upload" in str(exc)
        )
        is not None
    )
    assert spools and all(f.closed for f in spools)


def test_aggregate_metadata_bound(app_client, tenant, db, monkeypatch, spools):
    monkeypatch.setattr(get_settings(), "evidence_max_bytes", 4096)
    case = make_case(db, tenant)
    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    # Individually bounded form fields exceed the aggregate request cap.
    # A huge malformed header would instead hit the parser's own syntax bound,
    # so it cannot isolate this request-size guard.
    body = (
        b'--audit\r\nContent-Disposition: form-data; name="category"\r\n\r\n'
        + b"x" * 40000
        + b'\r\n--audit\r\nContent-Disposition: form-data; name="description"\r\n\r\n'
        + b"y" * 40000
        + b"\r\n--audit--\r\n"
    )
    response = streamed(
        app_client,
        f"/api/v1/cases/{case.id}/evidence",
        {"X-CSRF-Token": csrf, "Content-Type": "multipart/form-data; boundary=audit"},
        body,
    )
    assert response.status_code == 413
    assert spools == []


def test_concurrent_bounded_upload_rejections(app_client, tenant, db, monkeypatch, spools):
    monkeypatch.setattr(get_settings(), "evidence_max_bytes", 4096)
    case = make_case(db, tenant)
    csrf = login(app_client, tenant.users[Role.ANALYST].email)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            cookies=dict(app_client.cookies),
        ) as c:

            async def send():
                async def chunks():
                    body = multipart(b"0" * 8192)
                    for start in range(0, len(body), 512):
                        yield body[start : start + 512]

                return await c.post(
                    f"/api/v1/cases/{case.id}/evidence",
                    content=chunks(),
                    headers={
                        "X-CSRF-Token": csrf,
                        "Content-Type": "multipart/form-data; boundary=audit",
                    },
                )

            return await asyncio.gather(*(send() for _ in range(3)))

    assert [r.status_code for r in asyncio.run(run())] == [413, 413, 413]
    assert all(f.closed and f.audit_bytes_written <= 4096 for f in spools)


def test_truncated_body_closes_unfinished_file(app_client, tenant, db, spools):
    case = make_case(db, tenant)
    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    body = multipart(make_pdf("unfinished file")).rsplit(b"\r\n--audit--\r\n", 1)[0]
    response = streamed(
        app_client,
        f"/api/v1/cases/{case.id}/evidence",
        {"X-CSRF-Token": csrf, "Content-Type": "multipart/form-data; boundary=audit"},
        body,
    )
    assert response.status_code == 422
    assert spools and all(f.closed for f in spools)
