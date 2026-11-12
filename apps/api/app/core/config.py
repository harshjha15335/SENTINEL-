"""Typed application configuration loaded from environment variables."""

import os
import re
import subprocess
import sys
import unicodedata
from enum import StrEnum
from functools import lru_cache
from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def validate_checkout_url(url: str, *, name: str = "checkout URL") -> str:
    """Validate scheme, structure, and security of checkout redirect URLs.

    Invariants:
    - Must be valid HTTP (loopback/localhost only) or HTTPS
    - Must not contain user credentials (user:pass@host)
    - Must not contain whitespace, CRLF, or control characters
    - Must not exceed PayPal's 2048 character limit
    """
    if not url or not isinstance(url, str):
        raise ValueError(f"{name} must be a non-empty string")
    # Check the original input: urlsplit strips some controls during parsing.
    if any(c.isspace() or unicodedata.category(c).startswith("C") for c in url):
        raise ValueError(f"{name} must not contain whitespace or control characters")
    if len(url) > 2048:
        raise ValueError(f"{name} exceeds PayPal 2048-character limit")
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port  # Access validates malformed and out-of-range ports.
    except ValueError as exc:
        raise ValueError(f"{name} has an invalid host or port") from exc
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"{name} must use http or https scheme")
    if not host or not parsed.netloc:
        raise ValueError(f"{name} must contain a valid hostname")
    try:
        ip_address(host)
    except ValueError:
        try:
            ascii_host = host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError(f"{name} has an invalid hostname") from exc
        labels = ascii_host.rstrip(".").split(".")
        if len(ascii_host) > 253 or any(
            not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
            for label in labels
        ):
            raise ValueError(f"{name} has an invalid hostname") from None
    if parsed.netloc.endswith(":") or port == 0:
        raise ValueError(f"{name} has an invalid port")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{name} must not contain user credentials")
    if parsed.scheme == "http" and host.lower() not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError(f"{name} insecure http is only permitted on loopback")
    return url


def _populate_windows_user_env() -> None:
    if sys.platform != "win32" or "pytest" in sys.modules:
        return
    for var in (
        "SENTINEL_PAYPAL_CLIENT_ID",
        "SENTINEL_PAYPAL_CLIENT_SECRET",
        "SENTINEL_PAYPAL_WEBHOOK_ID",
    ):
        if not os.environ.get(var):
            try:
                cmd = [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f'[Environment]::GetEnvironmentVariable("{var}", "User")',
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)  # noqa: S603
                val = res.stdout.strip()
                if val:
                    os.environ[var] = val
            except (subprocess.SubprocessError, OSError):
                pass


_populate_windows_user_env()


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
    GOOGLE = "google"


class StorageBackend(StrEnum):
    """Where evidence files and generated packets are stored. Never a public static directory."""

    LOCAL = "local"
    DATABASE = "database"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SENTINEL_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    environment: str = "development"
    hosted_deployment: bool = False
    database_url: str = "postgresql+psycopg://sentinel:sentinel@127.0.0.1:5432/sentinel"
    database_ssl_root_cert: str | None = None
    # Owner-approved synthetic Render staging only; actual host review is still required.
    database_tls_policy: Literal["verify_full", "render_internal_staging"] = "verify_full"
    render_internal_tls_reviewed_host: str | None = None
    deployment_stage: str | None = None
    render_project_id: str | None = None
    render_workspace_id: str | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    cookie_secure: bool = False
    session_ttl_minutes: int = 8 * 60
    log_level: str = "INFO"

    paypal_mode: PayPalMode = PayPalMode.SANDBOX
    paypal_client_id: str | None = None
    paypal_client_secret: SecretStr | None = None
    paypal_webhook_id: str | None = None
    paypal_timeout_seconds: float = 20.0
    refund_execution_enabled: bool = False
    paypal_return_url: str | None = None
    paypal_cancel_url: str | None = None

    # Investigation agent. Without a provider and key, only deterministic summaries are produced.
    ai_provider: AIProvider = AIProvider.NONE
    ai_model: str | None = None
    ai_api_key: SecretStr | None = None
    ai_timeout_seconds: float = Field(default=90.0, gt=0, allow_inf_nan=False)
    ai_request_limit: int = Field(default=12, ge=1)
    ai_tool_calls_limit: int = Field(default=24, ge=1)
    ai_total_tokens_limit: int = Field(default=120_000, ge=1)
    ai_sdk_max_retries: int = Field(default=0, ge=0, le=2)
    ai_max_output_tokens: int = Field(default=2048, ge=1)
    # Local serialized input bounds include instructions, history and tool/output schemas.
    # Bytes are a model-independent context safeguard, not an exact token estimate.
    ai_max_input_bytes: int = Field(default=64_000, ge=1)
    ai_total_input_bytes_limit: int = Field(default=256_000, ge=1)
    investigation_stale_seconds: int = 600

    # Local-only deterministic webhook ingress. Never enabled in production.
    allow_webhook_fixtures: bool = False
    require_workers_ready: bool = False
    # A configured bridge is mandatory even in fixture mode; absence is intentional
    # only for fixture-only installations. Secrets never appear in health output.
    supabase_url: str | None = None
    supabase_service_role_key: SecretStr | None = None
    # Global inbox aggregates are visible only to this installation operator's merchant.
    # Tenant administrators otherwise see their own application queues only.
    operations_inbox_merchant_id: UUID | None = None
    webhook_fixture_key: SecretStr | None = None

    # Evidence uploads and generated packets.
    storage_backend: StorageBackend = StorageBackend.LOCAL
    storage_dir: str = "var/storage"
    evidence_max_bytes: int = 10 * 1024 * 1024
    evidence_max_text_chars: int = 50_000

    # Built web app (apps/web/dist). When set, the API also serves the UI from the same
    # origin, which is how the single-container deployment runs.
    web_dist: str | None = None

    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 300

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, value: str) -> str:
        # Hosts such as Render hand out postgres:// or postgresql:// URLs; use psycopg 3.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @field_validator("paypal_client_id")
    @classmethod
    def _paypal_client_id_shape(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if any(char.isspace() for char in value):
            raise ValueError("PayPal client ID must be nonempty without embedded whitespace")
        return value

    @field_validator("paypal_client_secret")
    @classmethod
    def _paypal_secret_shape(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        normalized = value.get_secret_value().strip()
        if not normalized:
            return None
        if any(char.isspace() for char in normalized):
            raise ValueError("PayPal secret must be nonempty without embedded whitespace")
        return SecretStr(normalized)

    @field_validator("paypal_return_url", "paypal_cancel_url")
    @classmethod
    def _validate_paypal_redirect_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_checkout_url(value)

    @model_validator(mode="after")
    def _no_partial_paypal_credentials(self) -> "Settings":
        if self.hosted_deployment and (
            self.environment != "production"
            or not self.cookie_secure
            or self.storage_backend is not StorageBackend.DATABASE
            or not self.require_workers_ready
            or any(not origin.startswith("https://") for origin in self.cors_origins)
        ):
            raise ValueError(
                "Hosted deployment requires production, secure cookies, database storage, "
                "worker readiness and HTTPS-only CORS origins (or an empty list)"
            )
        if self.hosted_deployment and self.paypal_mode is PayPalMode.SANDBOX:
            for value in (self.paypal_return_url, self.paypal_cancel_url):
                if value is None:
                    raise ValueError("Hosted sandbox requires explicit public HTTPS callback URLs")
                parsed = urlsplit(value)
                host = (parsed.hostname or "").lower().rstrip(".")
                try:
                    public = ip_address(host).is_global
                except ValueError:
                    public = "." in host and not host.endswith(
                        (".localhost", ".local", ".internal")
                    )
                if parsed.scheme != "https" or not public:
                    raise ValueError("Hosted sandbox requires explicit public HTTPS callback URLs")
        if self.allow_webhook_fixtures and (
            self.environment == "production" or not self.webhook_fixture_key
        ):
            raise ValueError("Webhook fixtures require a key and a non-production environment")
        has_id = bool(self.paypal_client_id)
        has_secret = self.paypal_client_secret is not None and bool(
            self.paypal_client_secret.get_secret_value()
        )
        if has_id != has_secret:
            raise ValueError(
                "SENTINEL_PAYPAL_CLIENT_ID and SENTINEL_PAYPAL_CLIENT_SECRET must be set together"
            )
        return self

    @model_validator(mode="after")
    def _complete_supabase_configuration(self) -> "Settings":
        has_url = bool(self.supabase_url)
        has_key = self.supabase_service_role_key is not None and bool(
            self.supabase_service_role_key.get_secret_value().strip()
        )
        if has_url != has_key:
            raise ValueError("Supabase URL and service-role key must be configured together")
        if self.supabase_url:
            try:
                parsed = urlsplit(self.supabase_url)
                valid = (
                    parsed.scheme == "https"
                    and parsed.hostname is not None
                    and parsed.hostname.endswith(".supabase.co")
                    and parsed.username is None
                    and parsed.password is None
                    and parsed.port is None
                    and parsed.path in ("", "/")
                    and not parsed.query
                    and not parsed.fragment
                    and not any(
                        c.isspace() or unicodedata.category(c).startswith("C")
                        for c in self.supabase_url
                    )
                )
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("Supabase requires a valid project HTTPS origin")
        return self

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @model_validator(mode="after")
    def _scoped_database_tls(self) -> "Settings":
        if self.database_tls_policy == "render_internal_staging":
            self.render_internal_database_args()
        return self

    def render_internal_database_args(self, database_url: str | None = None) -> dict[str, str]:
        """Validate effective migration/runtime destination, never claim server identity.

        `require` encrypts but does not authenticate the server. The exact private
        host/account binding is an operator-reviewed trust input, not attestation.
        """
        from sqlalchemy.engine import make_url
        from sqlalchemy.exc import ArgumentError

        try:
            destination = make_url(self.database_url if database_url is None else database_url)
            host = destination.host or ""
            allowed = (
                self.database_tls_policy == "render_internal_staging"
                and self.hosted_deployment
                and self.environment == "production"
                and self.deployment_stage == "staging"
                and self.render_project_id == "prj-dbq48lon74is739m7nl0"
                and self.render_workspace_id == "tea-d8gorhflk1mc73f4pmr0"
                and self.paypal_mode is PayPalMode.FIXTURE
                and self.ai_provider is AIProvider.NONE
                and self.ai_api_key is None
                and not self.paypal_credentials_configured
                and not self.paypal_webhook_id
                and not self.supabase_configured
                and not self.refund_execution_enabled
                and not self.allow_webhook_fixtures
                and self.cookie_secure
                and self.require_workers_ready
                and self.storage_backend is StorageBackend.DATABASE
                and self.database_ssl_root_cert is None
                and destination.drivername == "postgresql+psycopg"
                and host == self.render_internal_tls_reviewed_host
                and re.fullmatch(r"dpg-[a-z0-9]+(?:-[a-z0-9]+)*", host) is not None
                and destination.port in (None, 5432)
                and destination.database == "sentinel_staging"
                and destination.username == "sentinel_staging"
                and bool(destination.password)
                and set(destination.query).issubset({"sslmode"})
                and destination.query.get("sslmode", "require") == "require"
            )
        except (ArgumentError, ValueError):
            raise ValueError("Invalid Render internal staging database destination") from None
        # Render supplies DATABASE_URL, not libpq routing/services/client files.
        # Reject ambient settings rather than silently ignoring or trusting them.
        overrides = {
            "PGHOST",
            "PGHOSTADDR",
            "PGPORT",
            "PGDATABASE",
            "PGUSER",
            "PGPASSWORD",
            "PGPASSFILE",
            "PGSERVICE",
            "PGSERVICEFILE",
            "PGSSLMODE",
            "PGSSLROOTCERT",
            "PGSSLCERT",
            "PGSSLKEY",
            "PGSSLCRL",
            "PGSSLCRLDIR",
            "PGGSSENCMODE",
            "PGTARGETSESSIONATTRS",
            "PGOPTIONS",
        }
        if not allowed or any(os.environ.get(name) for name in overrides):
            raise ValueError("Unapproved Render internal staging TLS scope")
        return {
            "sslmode": "require",
            "gssencmode": "disable",
            "host": host,
            "port": "5432",
            "dbname": "sentinel_staging",
            "user": "sentinel_staging",
            "password": destination.password or "",
        }

    @property
    def bridge_required(self) -> bool:
        return self.paypal_mode is PayPalMode.SANDBOX or self.supabase_configured

    @property
    def worker_configuration_ready(self) -> bool:
        return not self.bridge_required or self.supabase_configured

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
