"""Offline only: guarded integrated staging must fail closed without approval."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.db import session

HOST = "dpg-offline-reviewed-staging-a"
URL = f"postgresql+psycopg://sentinel_staging:OFFLINE_PASSWORD@{HOST}/sentinel_staging"
BASE = {
    "hosted_deployment": True,
    "environment": "production",
    "deployment_stage": "staging",
    "render_project_id": "prj-dbq48lon74is739m7nl0",
    "render_workspace_id": "tea-d8gorhflk1mc73f4pmr0",
    "cookie_secure": True,
    "storage_backend": "database",
    "require_workers_ready": True,
    "cors_origins": [],
    "database_tls_policy": "render_internal_integrated_staging",
    "render_internal_tls_reviewed_host": HOST,
    "render_integration_tls_approved": True,
    "database_url": URL,
    "paypal_mode": "sandbox",
    "paypal_client_id": "OFFLINE_CLIENT",
    "paypal_client_secret": "OFFLINE_SECRET",
    "paypal_webhook_id": "OFFLINE_WEBHOOK",
    "paypal_return_url": "https://sentinel-v2-staging.onrender.com/api/v1/paypal/return",
    "paypal_cancel_url": "https://sentinel-v2-staging.onrender.com/api/v1/paypal/cancel",
    "ai_provider": "google",
    "ai_model": "gemini-3.1-flash-lite",
    "ai_api_key": "OFFLINE_GOOGLE_KEY",
    "supabase_url": "https://cfslzvvdjxstpupkqbpw.supabase.co",
    "supabase_service_role_key": "OFFLINE_ROLE",
    "refund_execution_enabled": False,
    "allow_webhook_fixtures": False,
}


def settings(**changes):
    return Settings(_env_file=None, **(BASE | changes))


def test_integrated_scope_is_encrypted_and_does_not_weaken_prod_defaults():
    config = settings()
    assert config.bridge_required
    assert config.worker_configuration_ready
    assert config.paypal_credentials_configured
    assert config.ai_configured
    args = session.database_connect_args(config)
    assert args == {
        "sslmode": "require",
        "gssencmode": "disable",
        "host": HOST,
        "port": "5432",
        "dbname": "sentinel_staging",
        "user": "sentinel_staging",
        "password": "OFFLINE_PASSWORD",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"render_integration_tls_approved": False},
        {"database_tls_policy": "render_internal_staging"},
        {"deployment_stage": "production"},
        {"environment": "development"},
        {"hosted_deployment": False},
        {"render_project_id": "other"},
        {"render_workspace_id": "other"},
        {"paypal_mode": "fixture"},
        {"paypal_client_id": None, "paypal_client_secret": None},
        {"paypal_webhook_id": None},
        {"paypal_return_url": "https://example.com/api/v1/paypal/return"},
        {"paypal_cancel_url": "https://example.com/api/v1/paypal/cancel"},
        {"ai_provider": "none"},
        {"ai_api_key": None},
        {"ai_model": "gemini-3.1-flash-lite-preview"},
        {"supabase_url": "https://other.supabase.co"},
        {"supabase_service_role_key": None},
        {"refund_execution_enabled": True},
        {"allow_webhook_fixtures": True},
        {"cookie_secure": False},
        {"require_workers_ready": False},
        {"storage_backend": "local"},
        {"render_internal_tls_reviewed_host": "dpg-wrong"},
        {"database_url": URL.replace(HOST, "other.example")},
        {"database_url": URL + "?sslmode=disable"},
        {"database_url": URL + "?hostaddr=127.0.0.1"},
    ],
)
def test_integrated_tls_rejects_unapproved_or_untrusted_profiles(change):
    with pytest.raises(ValidationError):
        settings(**change)


def test_integrated_tls_revalidates_effective_migration_destination():
    config = settings()
    with pytest.raises(ValueError, match="Unapproved Render"):
        session.database_connect_args(config, database_url=URL.replace(HOST, "other.example"))


def test_integrated_tls_error_does_not_disclose_supplied_secrets():
    with pytest.raises(ValidationError) as error:
        settings(
            render_integration_tls_approved=False,
            database_url=URL.replace("OFFLINE_PASSWORD", "VERY_SECRET_TEST_PASSWORD"),
        )
    assert "VERY_SECRET_TEST_PASSWORD" not in str(error.value)
    assert "OFFLINE_GOOGLE_KEY" not in str(error.value)
