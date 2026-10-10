from functools import lru_cache

from app.core.config import PayPalMode, get_settings
from app.services.paypal.fixture import FixturePayPalGateway
from app.services.paypal.gateway import PayPalGateway
from app.services.paypal.sandbox import SandboxPayPalGateway


class GatewayNotConfigured(Exception):
    pass


@lru_cache
def get_gateway() -> PayPalGateway:
    """Resolve the gateway for this process. Sandbox without credentials is an error, not a
    silent fallback to fixtures: we never want simulated data to appear in sandbox mode."""
    settings = get_settings()
    if settings.paypal_mode is PayPalMode.FIXTURE:
        return FixturePayPalGateway()
    if not settings.paypal_credentials_configured:
        raise GatewayNotConfigured(
            "PayPal sandbox credentials are not configured "
            "(SENTINEL_PAYPAL_CLIENT_ID / SENTINEL_PAYPAL_CLIENT_SECRET)"
        )
    assert settings.paypal_client_id and settings.paypal_client_secret
    return SandboxPayPalGateway(
        settings.paypal_client_id,
        settings.paypal_client_secret.get_secret_value(),
        timeout=settings.paypal_timeout_seconds,
    )
