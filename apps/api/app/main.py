from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import audit, auth, catalog, dashboard, health, paypal, transactions, webhooks
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware, SecurityHeadersMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="SENTINEL API",
        version="0.1.0",
        description="Payment trust & recovery for PayPal merchants (sandbox only).",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "X-Correlation-Id"],
        expose_headers=["X-Correlation-Id"],
    )
    app.add_middleware(CorrelationIdMiddleware)
    install_error_handlers(app)

    v1 = APIRouter(prefix="/api/v1")
    for module in (health, auth, catalog, paypal, transactions, dashboard, audit, webhooks):
        v1.include_router(module.router)
    app.include_router(v1)
    return app


app = create_app()
