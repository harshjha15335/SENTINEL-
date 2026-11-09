"""Backend Credential Readiness and Fixture Mode Verification for SENTINEL.

Validates that:
1. The FastAPI backend config receives the validated Sandbox credential pair and webhook ID.
2. Gateway factory instantiates SandboxPayPalGateway without errors.
3. In fixture mode, the backend cleanly falls back to FixtureGateway without attempting network access.
"""

import os
import subprocess
import sys

def get_user_env(key: str) -> str:
    return os.environ.get(key) or subprocess.run(
        ["powershell", "-NoProfile", "-Command", f'[Environment]::GetEnvironmentVariable("{key}", "User")'],
        capture_output=True, text=True
    ).stdout.strip()

print("=" * 70)
print("SENTINEL — Backend Credential & Webhook Readiness Verification")
print("=" * 70)

cid = get_user_env("SENTINEL_PAYPAL_CLIENT_ID")
csec = get_user_env("SENTINEL_PAYPAL_CLIENT_SECRET")
wh_id = get_user_env("SENTINEL_PAYPAL_WEBHOOK_ID")

if not cid or not csec:
    print("[FAIL] Missing SENTINEL_PAYPAL_CLIENT_ID or SENTINEL_PAYPAL_CLIENT_SECRET in User environment.")
    sys.exit(1)

os.environ["SENTINEL_PAYPAL_CLIENT_ID"] = cid
os.environ["SENTINEL_PAYPAL_CLIENT_SECRET"] = csec
os.environ["SENTINEL_PAYPAL_WEBHOOK_ID"] = wh_id
os.environ["SENTINEL_PAYPAL_MODE"] = "sandbox"

from app.core.config import PayPalMode, get_settings
from app.services.paypal.factory import get_gateway
from app.services.paypal.sandbox import SandboxPayPalGateway
from app.services.paypal.fixture import FixturePayPalGateway

get_settings.cache_clear()
get_gateway.cache_clear()

settings = get_settings()
print("\n1. Verifying Sandbox Backend Settings:")
print(f"   - PayPal Mode:                   {settings.paypal_mode}")
print(f"   - Credentials Configured:        {settings.paypal_credentials_configured}")
print(f"   - Webhook ID Configured:         {bool(settings.paypal_webhook_id)} ({settings.paypal_webhook_id})")
print(f"   - Client ID length:              {len(settings.paypal_client_id)}")
print(f"   - Secret held in SecretStr:      {type(settings.paypal_client_secret).__name__} (length: {len(settings.paypal_client_secret.get_secret_value())})")

assert settings.paypal_webhook_id == "4J572318CT6195232", "Expected webhook ID 4J572318CT6195232"

gw = get_gateway()
print(f"   - Resolved Gateway:              {type(gw).__name__}")
assert isinstance(gw, SandboxPayPalGateway)
print("   [PASS] Sandbox gateway and webhook configuration ready.")

# Check 2: Verify Fixture mode fallback
print("\n2. Verifying Fixture Mode Backend Integrity:")
os.environ["SENTINEL_PAYPAL_MODE"] = "fixture"
get_settings.cache_clear()
get_gateway.cache_clear()

fixture_settings = get_settings()
print(f"   - PayPal Mode:                   {fixture_settings.paypal_mode}")
fixture_gw = get_gateway()
assert isinstance(fixture_gw, FixturePayPalGateway)
print("   [PASS] Fixture gateway functions correctly.")

print("\n" + "=" * 70)
print("[SUCCESS] All backend credential and webhook ID checks passed!")
print("=" * 70)
