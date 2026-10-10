from app.core.errors import ProviderUnavailableError
from app.services.paypal.factory import GatewayNotConfigured, get_gateway
from app.services.paypal.gateway import PayPalGateway


def paypal_gateway() -> PayPalGateway:
    try:
        return get_gateway()
    except GatewayNotConfigured as exc:
        raise ProviderUnavailableError(str(exc), details={"credential_dependency": True}) from exc
