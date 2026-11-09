"""Offline construction: no provider requests."""

import pytest
from pydantic_ai.models.google import GoogleModel

from app.core.config import Settings
from app.services.investigation.provider import resolve_provider


@pytest.mark.parametrize("retries", [0, 1, 2])
def test_google_retry_attempts(retries):
    spec = resolve_provider(
        Settings(
            _env_file=None,
            ai_provider="google",
            ai_model="gemini-3.1-flash-lite",
            ai_api_key="offline-placeholder",
            ai_sdk_max_retries=retries,
        )
    )
    assert spec is not None
    model = spec.build()
    assert isinstance(model, GoogleModel)
    assert model.client._api_client._http_options.retry_options.attempts == retries + 1


@pytest.mark.parametrize(
    "key,model", [(None, "gemini-3.1-flash-lite"), ("offline-placeholder", None)]
)
def test_google_missing_config(key, model):
    assert (
        resolve_provider(
            Settings(_env_file=None, ai_provider="google", ai_model=model, ai_api_key=key)
        )
        is None
    )
