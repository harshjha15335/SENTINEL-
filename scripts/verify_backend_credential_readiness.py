"""Backend Credential Readiness and Fixture Mode Verification for SENTINEL.

Validates that:
1. The FastAPI backend config receives the validated Sandbox credential pair without proxy placeholders.
2. Gateway factory instantiates SandboxPayPalGateway without errors.
3. In fixture mode (SENTINEL_PAYPAL_MODE=fixture), the backend cleanly falls back to FixtureGateway
   without attempting network access or throwing errors even if credentials are empty or present.
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
print("SENTINEL — Backend Credential & Fixture Mode Verification")
print("=" * 70)

# Check 1: Ingesting validated credentials from environment
cid = get_user_env("SENTINEL_PAYPAL_CLIENT_ID")
csec = get_user_env("SENTINEL_PAYPAL_CLIENT_SECRET")

if not cid or not csec:
    print("[FAIL] Missing SENTINEL_PAYPAL_CLIENT_ID or SENTINEL_PAYPAL_CLIENT_SECRET in User environment.")
    sys.exit(1)

# Set into process environment to simulate running backend
os.environ["SENTINEL_PAYPAL_CLIENT_ID"] = cid
os.environ["SENTINEL_PAYPAL_CLIENT_SECRET"] = csec
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
print(f"   - Client ID length:              {len(settings.paypal_client_id)}")
print(f"   - Secret held in SecretStr:      {type(settings.paypal_client_secret).__name__} (length: {len(settings.paypal_client_secret.get_secret_value())})")

# Assert no proxy placeholder
secret_val = settings.paypal_client_secret.get_secret_value()
assert not secret_val.startswith(("proxy:", "vault:", "http:", "https:")), "Secret must not be a proxy placeholder"
assert not any(c.isspace() for c in secret_val), "Secret must not contain whitespace"

gw = get_gateway()
print(f"   - Resolved Gateway:              {type(gw).__name__}")
assert isinstance(gw, SandboxPayPalGateway), f"Expected SandboxPayPalGateway, got {type(gw).__name__}"
print("   [PASS] Sandbox gateway ready.")

# Check 2: Verify Fixture mode fallback and independence
print("\n2. Verifying Fixture Mode Backend Integrity:")
os.environ["SENTINEL_PAYPAL_MODE"] = "fixture"
get_settings.cache_clear()
get_gateway.cache_clear()

fixture_settings = get_settings()
print(f"   - PayPal Mode:                   {fixture_settings.paypal_mode}")
fixture_gw = get_gateway()
print(f"   - Resolved Gateway:              {type(fixture_gw).__name__}")
assert isinstance(fixture_gw, FixturePayPalGateway), f"Expected FixturePayPalGateway, got {type(fixture_gw).__name__}"
print("   [PASS] Fixture gateway functions correctly and is isolated from credentials.")

# Check 3: Verify Empty Credentials in Fixture Mode
os.environ["SENTINEL_PAYPAL_CLIENT_ID"] = ""
os.environ["SENTINEL_PAYPAL_CLIENT_SECRET"] = ""
get_settings.cache_clear()
get_gateway.cache_clear()

empty_fixture_settings = get_settings()
assert empty_fixture_settings.paypal_client_id is None
assert empty_fixture_settings.paypal_client_secret is None
assert empty_fixture_settings.paypal_credentials_configured is False
empty_gw = get_gateway()
assert isinstance(empty_gw, FixturePayPalGateway)
print("   [PASS] Empty credentials in fixture mode cleanly resolve to FixturePayPalGateway without startup errors.")

print("\n" + "=" * 70)
print("[SUCCESS] All backend credential and fixture mode checks passed!")
print("=" * 70)

