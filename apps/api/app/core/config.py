"""Typed application configuration loaded from environment variables."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PayPalMode(StrEnum):
    """How SENTINEL talks to PayPal.

    SANDBOX makes real authenticated requests to PayPal's sandbox.
    FIXTURE never leaves the process; every record it produces is labelled SIMULATED.
    There is deliberately no LIVE mode (see docs/SECURITY.md).
    """

    SANDBOX = "sandbox"
    FIXTURE = "fixture"


class AIProvider(StrEnum):
    """Which LLM provider the investigation agent uses. NONE means deterministic summaries only."""

    NONE = "none"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class StorageBackend(StrEnum):
    """Where evidence files and generated packets are stored. Never a public static directory."""

    LOCAL = "local"
    DATABASE = "database"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SENTINEL_", env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://sentinel:sentinel@127.0.0.1:5432/sentinel"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    cookie_secure: bool = False
    session_ttl_minutes: int = 8 * 60
    log_level: str = "INFO"

    paypal_mode: PayPalMode = PayPalMode.SANDBOX
    paypal_client_id: str | None = None
    paypal_client_secret: SecretStr | None = None
    paypal_webhook_id: str | None = None
    paypal_timeout_seconds: float = 20.0

    # Investigation agent. Without a provider and key, only deterministic summaries are produced.
    ai_provider: AIProvider = AIProvider.NONE
    ai_model: str | None = None
    ai_api_key: SecretStr | None = None
    ai_timeout_seconds: float = 90.0
    ai_request_limit: int = 12
    ai_tool_calls_limit: int = 24
    ai_total_tokens_limit: int = 120_000
    investigation_stale_seconds: int = 600

    # Evidence uploads and generated packets.
    storage_backend: StorageBackend = StorageBackend.LOCAL
    storage_dir: str = "var/storage"
    evidence_max_bytes: int = 10 * 1024 * 1024
    evidence_max_text_chars: int = 50_000

    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 300

    @model_validator(mode="after")
    def _no_partial_paypal_credentials(self) -> "Settings":
        has_id = bool(self.paypal_client_id)
        has_secret = self.paypal_client_secret is not None and bool(
            self.paypal_client_secret.get_secret_value()
        )
        if has_id != has_secret:
            raise ValueError(
                "SENTINEL_PAYPAL_CLIENT_ID and SENTINEL_PAYPAL_CLIENT_SECRET must be set together"
            )
        return self

    @property
    def ai_configured(self) -> bool:
        return (
            self.ai_provider is not AIProvider.NONE
            and self.ai_api_key is not None
            and bool(self.ai_api_key.get_secret_value())
        )

    @property
    def paypal_credentials_configured(self) -> bool:
        return bool(self.paypal_client_id and self.paypal_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
