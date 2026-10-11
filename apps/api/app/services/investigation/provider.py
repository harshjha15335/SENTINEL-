"""A small, typed abstraction over the LLM provider used by the investigation agent.

Business code asks for a ``ProviderSpec`` and never imports a vendor SDK directly. With no
provider or no key configured, ``resolve_provider`` returns ``None`` and investigations fall back
to the deterministic summary. Tests install a scripted model with ``override_provider``.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import pydantic_ai
from pydantic_ai.models import Model

from app.core.config import AIProvider, Settings, get_settings

# pydantic-ai prints an observability banner on first use; SENTINEL logs JSON only.
pydantic_ai.BANNER_ENABLED = False

DEFAULT_MODELS: dict[AIProvider, str] = {
    AIProvider.ANTHROPIC: "claude-sonnet-5-5",
}


@dataclass(frozen=True)
class ProviderSpec:
    provider: str
    model_name: str
    build: Callable[[], Model]


_overridden = False
_override: ProviderSpec | None = None


@contextmanager
def override_provider(spec: ProviderSpec | None) -> Iterator[None]:
    """Use a scripted model (tests only). ``None`` forces 'no provider configured'."""
    global _override, _overridden
    previous = (_overridden, _override)
    _overridden, _override = True, spec
    try:
        yield
    finally:
        _overridden, _override = previous


def resolve_provider(settings: Settings | None = None) -> ProviderSpec | None:
    if _overridden:
        return _override
    settings = settings or get_settings()
    if not settings.ai_configured or settings.ai_api_key is None:
        return None
    key = settings.ai_api_key.get_secret_value()
    model_name = settings.ai_model or DEFAULT_MODELS.get(settings.ai_provider)
    if not model_name:
        return None
    if settings.ai_provider is AIProvider.ANTHROPIC:

        def build_anthropic() -> Model:
            from pydantic_ai.models.anthropic import AnthropicModel
            from pydantic_ai.providers.anthropic import AnthropicProvider

            return AnthropicModel(model_name, provider=AnthropicProvider(api_key=key))

        return ProviderSpec("anthropic", model_name, build_anthropic)
    if settings.ai_provider is AIProvider.OPENAI:

        def build_openai() -> Model:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            return OpenAIChatModel(model_name, provider=OpenAIProvider(api_key=key))

        return ProviderSpec("openai", model_name, build_openai)
    return None


def status() -> dict[str, object]:
    """What the UI may know about the provider. Never includes the key."""
    spec = resolve_provider()
    settings = get_settings()
    return {
        "configured": spec is not None,
        "provider": spec.provider if spec else settings.ai_provider.value,
        "model_name": spec.model_name if spec else None,
        "fallback": None if spec else "DETERMINISTIC",
    }
