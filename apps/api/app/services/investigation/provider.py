"""A small, typed abstraction over the LLM provider used by the investigation agent.

Business code asks for a ``ProviderSpec`` and never imports a vendor SDK directly. With no
provider or no key configured, ``resolve_provider`` returns ``None`` and investigations fall back
to the deterministic summary. Tests install a scripted model with ``override_provider``.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any

import pydantic_ai
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.profiles.google import GoogleJsonSchemaTransformer
from pydantic_ai.settings import ModelSettings

from app.core.config import AIProvider, Settings, get_settings

# pydantic-ai prints an observability banner on first use; SENTINEL logs JSON only.
pydantic_ai.BANNER_ENABLED = False


class SentinelGoogleJsonSchemaTransformer(GoogleJsonSchemaTransformer):
    """Google-compatible JSON Schema transformer.

    Inlines $defs and $ref pointers and converts nullable unions to nullable: true.
    Strips array bounds (minItems/maxItems) that the Gemini API schema parser rejects,
    relying on application-side validation in `validate_findings` for strict constraint enforcement.
    """

    def __init__(
        self,
        schema: dict[str, object],
        *,
        strict: bool | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            schema,
            strict=strict,
            prefer_inlined_defs=True,
            simplify_nullable_unions=True,
        )

    def transform(self, schema: dict[str, object]) -> dict[str, object]:
        schema = super().transform(schema)
        schema.pop("minItems", None)
        schema.pop("maxItems", None)
        return schema


class SentinelGoogleModel(GoogleModel):
    """Guarded Google GenAI model adapter for Gemini 3+.

    Fixes:
    1. Schema Compatibility: Replaces nested $defs/$ref in tool and output definitions
       with fully inlined, Google-compatible OpenAPI schemas.
    2. Modality Conflict: Prevents contradictory `responseModalities: ['TEXT']` from being
       sent alongside function declarations.
    3. Tool Calling Mode: Upgrades forced `mode: ANY` with 12 tools to `VALIDATED` (or `AUTO`),
       enabling tool exploration while strictly enforcing findings schemas.
    """

    def prepare_request(
        self,
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> tuple[ModelSettings | None, ModelRequestParameters]:
        model_settings, model_request_parameters = super().prepare_request(
            model_settings, model_request_parameters
        )

        def clean_tool(tool_def: Any) -> Any:
            transformer = SentinelGoogleJsonSchemaTransformer(
                tool_def.parameters_json_schema, strict=tool_def.strict
            )
            clean_schema = transformer.walk()
            return replace(tool_def, parameters_json_schema=clean_schema)

        model_request_parameters = replace(
            model_request_parameters,
            function_tools=[clean_tool(t) for t in model_request_parameters.function_tools],
            output_tools=[clean_tool(t) for t in model_request_parameters.output_tools],
        )
        return model_settings, model_request_parameters

    async def _build_content_and_config(
        self,
        messages: list[Any],
        model_settings: Any,
        model_request_parameters: Any,
    ) -> tuple[list[Any], Any]:
        contents, config = await super()._build_content_and_config(
            messages, model_settings, model_request_parameters
        )
        # Fix: Upstream PydanticAI 2.55.0 bug where response_modalities is sent as ['TEXT']
        # even when tools are declared. Removing response_modalities prevents API conflict
        # with function calling.
        if config.get("tools"):
            config["response_modalities"] = None

        return contents, config


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

            provider = AnthropicProvider(api_key=key)
            provider.client.max_retries = settings.ai_sdk_max_retries
            return AnthropicModel(model_name, provider=provider)

        return ProviderSpec("anthropic", model_name, build_anthropic)
    if settings.ai_provider is AIProvider.GOOGLE:

        def build_google() -> Model:
            from google.genai.types import HttpRetryOptions
            from pydantic_ai.providers.google import GoogleProvider

            # Google counts attempts including the initial call, unlike OpenAI retries.
            provider = GoogleProvider(
                api_key=key,
                retry_options=HttpRetryOptions(attempts=1 + settings.ai_sdk_max_retries),
            )
            return SentinelGoogleModel(model_name, provider=provider)

        return ProviderSpec("google", model_name, build_google)
    if settings.ai_provider is AIProvider.OPENAI:

        def build_openai() -> Model:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            provider = OpenAIProvider(api_key=key)
            provider.client.max_retries = settings.ai_sdk_max_retries
            return OpenAIChatModel(model_name, provider=provider)

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
