"""Authenticate evidence intake before parsing and bound multipart spooling.

This route class is deliberately limited to evidence uploads. It does not buffer the
request body, trust Content-Length, or change the webhook's raw-body semantics.
"""

from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any
from uuid import UUID

from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartException, MultiPartParser

from app.auth.deps import current_principal, operator
from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.services.cases import get_case

# Bound non-file multipart metadata as well as the file itself.
MULTIPART_OVERHEAD_BYTES = 64 * 1024


class EvidenceParser(MultiPartParser):
    def __init__(self, request: Request, file_limit: int) -> None:
        self.file_limit = file_limit
        self.part_bytes = 0
        self.too_large = False
        total_limit = file_limit + MULTIPART_OVERHEAD_BYTES

        async def stream() -> AsyncGenerator[bytes, None]:
            received = 0
            async for chunk in request.stream():
                received += len(chunk)
                if received > total_limit:
                    self.too_large = True
                    raise MultiPartException("Evidence request exceeds the size limit")
                yield chunk

        super().__init__(
            request.headers,
            stream(),
            max_files=1,
            max_fields=2,
            max_part_size=MULTIPART_OVERHEAD_BYTES,
        )

    def on_part_begin(self) -> None:
        self.part_bytes = 0
        super().on_part_begin()

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        self.part_bytes += end - start
        if self._current_part.file is not None and self.part_bytes > self.file_limit:
            self.too_large = True
            raise MultiPartException("Evidence file exceeds the size limit")
        super().on_part_data(data, start, end)


def authorize_upload(request: Request) -> None:
    # Complete this short check before consuming the body. The normal dependencies
    # recheck authorization before storage, including expiry during a slow upload.
    with get_sessionmaker()() as db:
        principal = operator(current_principal(request, db))
        try:
            case_id = UUID(request.path_params["case_id"])
        except ValueError:
            return  # Preserve FastAPI's path validation response.
        get_case(db, principal.merchant_id, case_id)


class EvidenceUploadRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def guarded(request: Request) -> Response:
            await run_in_threadpool(authorize_upload, request)
            limit = get_settings().evidence_max_bytes
            declared = request.headers.get("content-length")
            if declared is not None:
                try:
                    length = int(declared)
                except ValueError:
                    raise HTTPException(400, "Invalid Content-Length") from None
                if length < 0:
                    raise HTTPException(400, "Invalid Content-Length")
                if length > limit + MULTIPART_OVERHEAD_BYTES:
                    raise HTTPException(413, "Evidence request exceeds the size limit")
            try:
                parser = EvidenceParser(request, limit)
            except MultiPartException as exc:
                raise HTTPException(400, exc.message) from exc
            try:
                form = await parser.parse()
            except BaseException as exc:
                # Starlette closes on MultiPartException; also cover disconnects,
                # cancellation and unexpected parser failures after temp-file creation.
                for file in parser._files_to_close_on_error:
                    file.close()
                if isinstance(exc, MultiPartException):
                    raise HTTPException(413 if parser.too_large else 400, exc.message) from exc
                raise
            request._form = form
            try:
                return await handler(request)
            finally:
                try:
                    await form.close()
                finally:
                    # MultipartParser.finalize may accept a truncated body;
                    # unfinished file parts never reach FormData.items.
                    for file in parser._files_to_close_on_error:
                        file.close()

        return guarded
