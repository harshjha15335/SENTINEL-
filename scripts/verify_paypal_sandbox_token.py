"""PayPal Sandbox Token-Only Verification Script for SENTINEL.

Performs a single, non-financial OAuth 2.0 token request against PayPal's
Sandbox endpoint (https://api-m.sandbox.paypal.com/v1/oauth2/token).

SAFETY RULES:
1. Performs ONLY one OAuth token request.
2. Absolutely NO financial API calls (no orders, captures, refunds, or disputes).
3. Secrets and access tokens are NEVER printed or logged.
4. Requires explicit --execute flag to run network verification.
"""

import argparse
import os
import re
import sys

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install via pip install httpx or activate apps/api/.venv.")
    sys.exit(1)

SANDBOX_OAUTH_URL = "https://api-m.sandbox.paypal.com/v1/oauth2/token"


def _check_credential_shape(client_id: str, client_secret: str) -> list[str]:
    warnings: list[str] = []
    if any(c.isspace() for c in client_id):
        warnings.append("Client ID contains embedded whitespace.")
    if any(c.isspace() for c in client_secret):
        warnings.append("Client Secret contains embedded whitespace.")
    if client_secret.startswith(("proxy:", "vault:", "secret:", "env:", "placeholder:", "http:", "https:")):
        warnings.append(
            "Client Secret appears to be an unexpanded proxy binding or secret reference "
            f"('{client_secret[:12]}...'). PayPal requires the raw Sandbox secret string."
        )
    if len(client_id) < 16:
        warnings.append("Client ID appears unusually short for a PayPal Sandbox Client ID.")
    if len(client_secret) < 16:
        warnings.append("Client Secret appears unusually short for a PayPal Sandbox Client Secret.")
    return warnings


def verify_paypal_sandbox(execute: bool = False) -> int:
    client_id = os.environ.get("SENTINEL_PAYPAL_CLIENT_ID", "").strip()
    client_secret = os.environ.get("SENTINEL_PAYPAL_CLIENT_SECRET", "").strip()

    print("=" * 70)
    print("SENTINEL — PayPal Sandbox OAuth Token Verification")
    print("=" * 70)

    if not client_id or not client_secret:
        print("\n[!] Configuration missing:")
        if not client_id:
            print("    - SENTINEL_PAYPAL_CLIENT_ID is not set in environment.")
        if not client_secret:
            print("    - SENTINEL_PAYPAL_CLIENT_SECRET is not set in environment.")
        print("\nTo set credentials securely in your shell session:")
        print("  Windows PowerShell:")
        print("    $env:SENTINEL_PAYPAL_CLIENT_ID=\"<your-sandbox-client-id>\"")
        print("    $env:SENTINEL_PAYPAL_CLIENT_SECRET=\"<your-sandbox-client-secret>\"")
        print("  Linux/macOS Bash:")
        print("    export SENTINEL_PAYPAL_CLIENT_ID=\"<your-sandbox-client-id>\"")
        print("    export SENTINEL_PAYPAL_CLIENT_SECRET=\"<your-sandbox-client-secret>\"")
        return 1

    print(f"\nTarget Endpoint: {SANDBOX_OAUTH_URL}")
    print(f"HTTP Method:     POST")
    print(f"Auth Scheme:     HTTP Basic Auth (base64(client_id:client_secret))")
    print(f"Request Body:    grant_type=client_credentials (x-www-form-urlencoded)")
    print(f"Client ID:       {client_id[:6]}...{client_id[-4:] if len(client_id) > 10 else ''} (length: {len(client_id)})")
    print(f"Client Secret:   [REDACTED] (length: {len(client_secret)})")

    shape_warnings = _check_credential_shape(client_id, client_secret)
    if shape_warnings:
        print("\n[!] Credential Shape Warnings:")
        for w in shape_warnings:
            print(f"    - {w}")

    if not execute:
        print("\n[DRY RUN MODE]")
        print("Network request was NOT performed.")
        print("To execute the live token verification against PayPal Sandbox, re-run with:")
        print("    python scripts/verify_paypal_sandbox_token.py --execute")
        return 0

    print("\nExecuting live token request to PayPal Sandbox...")
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                SANDBOX_OAUTH_URL,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                headers={"Accept": "application/json"},
            )
    except httpx.RequestError as exc:
        print(f"\n[FAIL] Network/Transport Error: {type(exc).__name__}: {exc}")
        print("Check local network, proxy settings, or egress firewall rules.")
        return 2

    debug_id = resp.headers.get("paypal-debug-id", "<none>")
    print(f"\nResponse Status: {resp.status_code} {resp.reason_phrase}")
    print(f"PayPal Debug ID: {debug_id}")

    if resp.status_code == 200:
        try:
            body = resp.json()
            token_type = body.get("token_type", "Bearer")
            expires_in = body.get("expires_in", "unknown")
            print("\n[SUCCESS] Sandbox OAuth2 Authentication Succeeded!")
            print(f"    - Token Type: {token_type}")
            print(f"    - Expires In: {expires_in} seconds (~{int(expires_in)//3600} hours)")
            print("    - Access Token: [ACQUIRED AND REDACTED]")
            print("\nYour PayPal Sandbox client credentials and Basic Auth encoding are valid.")
            return 0
        except Exception as exc:
            print(f"\n[!] Failed to parse token response: {exc}")
            return 3

    elif resp.status_code == 401:
        print("\n[FAIL] HTTP 401 Unauthorized (Authentication Failed)")
        try:
            err_body = resp.json()
            err_code = err_body.get("error", "unknown")
            err_desc = err_body.get("error_description", "")
            print(f"    - Error: {err_code}")
            # Provider error description might contain hints but never log raw secrets
            safe_desc = re.sub(re.escape(client_secret), "[REDACTED]", err_desc) if client_secret else err_desc
            print(f"    - Description: {safe_desc}")
        except Exception:
            pass

        print("\nDiagnostic Checklist for 401 invalid_client:")
        print("1. Paired Credentials:")
        print("   Ensure the Client ID and Client Secret are from the SAME Sandbox REST app in developer.paypal.com.")
        print("2. Sandbox vs Live:")
        print("   Ensure you selected 'Sandbox' (not 'Live') in the PayPal Developer Dashboard.")
        print("3. No Proxy Placeholders:")
        print("   HTTP Basic Auth encodes credentials into Base64 over end-to-end TLS.")
        print("   A forward proxy cannot rewrite or substitute secrets inside an encrypted TLS stream.")
        print("   Provide the exact raw PayPal Sandbox Secret directly.")
        print(f"4. Debug ID for PayPal Support: {debug_id}")
        return 1

    else:
        print(f"\n[FAIL] Unexpected Response: {resp.status_code}")
        return 4


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SENTINEL PayPal Sandbox Token-Only Verifier")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the single token request against PayPal Sandbox (default: dry run)",
    )
    args = parser.parse_args()
    sys.exit(verify_paypal_sandbox(execute=args.execute))

