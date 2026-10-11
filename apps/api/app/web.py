"""Serve the built web app from the API process (single-container deployment).

Only GET requests outside ``/api`` reach this handler. Files that exist in the build are
served as-is; any other path returns ``index.html`` so client-side routes such as
``/cases/<id>`` work on reload. Paths are resolved inside the build directory only.
"""

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse

# The browser bundle never holds secrets; PayPal's sandbox JS SDK is the only third party.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' https://www.sandbox.paypal.com https://www.paypal.com",
        "frame-src https://www.sandbox.paypal.com https://www.paypal.com",
        "connect-src 'self' https://www.sandbox.paypal.com https://api-m.sandbox.paypal.com",
        "img-src 'self' data: https://*.paypal.com https://*.paypalobjects.com",
        "style-src 'self' 'unsafe-inline'",
        "font-src 'self' data:",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
    ]
)


def mount_web(app: FastAPI, dist: str) -> None:
    root = Path(dist).resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError(f"SENTINEL_WEB_DIST has no index.html: {root}")
    router = APIRouter(include_in_schema=False)
    headers = {"Content-Security-Policy": CONTENT_SECURITY_POLICY}

    @router.api_route("/{path:path}", methods=["GET", "HEAD"])
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (root / path).resolve()
        if path and candidate.is_relative_to(root) and candidate.is_file():
            cache = (
                "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
            )
            return FileResponse(candidate, headers={**headers, "Cache-Control": cache})
        return FileResponse(index, headers={**headers, "Cache-Control": "no-cache"})

    app.include_router(router)
