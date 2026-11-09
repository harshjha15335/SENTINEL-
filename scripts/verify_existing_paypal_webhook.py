"""Authorized Read-Only PayPal Webhook Verification Script for SENTINEL.

Performs at most 3 non-financial HTTP calls to PayPal Sandbox:
1. POST /v1/oauth2/token (Basic Auth, grant_type=client_credentials) - in-memory only.
2. GET /v1/notifications/webhooks (List webhooks for authenticated Sandbox app).
3. GET /v1/notifications/webhooks/4J572318CT6195232 (Show details of candidate webhook).

SAFETY & SECURITY GUARANTEES:
- Max 3 requests. Zero retries.
- Zero financial operations. No webhook creation, modification, or deletion.
- In-memory credential and token handling. Zero tokens or secrets printed or logged.
"""

import json
import os
import subprocess
import sys
from typing import Any

REQUIRED_EVENTS = {
    "PAYMENT.CAPTURE.COMPLETED",
    "PAYMENT.CAPTURE.PENDING",
    "PAYMENT.CAPTURE.DENIED",
    "PAYMENT.CAPTURE.REFUNDED",
    "PAYMENT.CAPTURE.REVERSED",
    "CHECKOUT.ORDER.APPROVED",
    "CUSTOMER.DISPUTE.CREATED",
    "CUSTOMER.DISPUTE.UPDATED",
    "CUSTOMER.DISPUTE.RESOLVED",
}

EXPECTED_WEBHOOK_ID = "4J572318CT6195232"
EXPECTED_RECEIVER_URL = "https://cfslzvvdjxstpupkqbpw.supabase.co/functions/v1/paypal-webhook"
BASE_URL = "https://api-m.sandbox.paypal.com"


def get_secret(name: str) -> str:
    val = os.environ.get(name, "")
    if val:
        return val
    try:
        cmd = ["powershell", "-NoProfile", "-Command", f'[Environment]::GetEnvironmentVariable("{name}", "User")']
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return ""


def main():
    print("=" * 70)
    print("SENTINEL — Authorized Read-Only Webhook Verification")
    print("=" * 70)

    client_id = get_secret("SENTINEL_PAYPAL_CLIENT_ID")
    client_secret = get_secret("SENTINEL_PAYPAL_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("[FAIL] Missing SENTINEL_PAYPAL_CLIENT_ID or SENTINEL_PAYPAL_CLIENT_SECRET in environment.")
        sys.exit(1)

    try:
        import httpx
    except ImportError:
        print("[FAIL] httpx is required.")
        sys.exit(1)

    request_count = 0

    # 1. Obtain at most ONE new OAuth access token in-memory
    print("\n[Request 1/3] Obtaining OAuth token from PayPal Sandbox...")
    token = None
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        request_count += 1
        oauth_resp = client.post(
            "/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"Accept": "application/json"},
        )
        oauth_debug_id = oauth_resp.headers.get("paypal-debug-id", "<none>")
        print(f"  - Status:   HTTP {oauth_resp.status_code}")
        print(f"  - Debug ID: {oauth_debug_id}")

        if oauth_resp.status_code != 200:
            print(f"[FAIL] OAuth token request failed: HTTP {oauth_resp.status_code}")
            try:
                print("  - Error:", oauth_resp.json().get("error"))
            except Exception:
                pass
            sys.exit(2)

        body = oauth_resp.json()
        token = body.get("access_token")
        expires_in = body.get("expires_in")
        print(f"  - Result:   Token successfully acquired in-memory (expires in {expires_in}s)")

        # Prepare headers for authenticated requests
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # 2. Execute GET /v1/notifications/webhooks
        print("\n[Request 2/3] Querying GET /v1/notifications/webhooks...")
        request_count += 1
        list_resp = client.get("/v1/notifications/webhooks", headers=headers)
        list_debug_id = list_resp.headers.get("paypal-debug-id", "<none>")
        print(f"  - Status:   HTTP {list_resp.status_code}")
        print(f"  - Debug ID: {list_debug_id}")

        if list_resp.status_code != 200:
            print(f"[FAIL] Failed to list webhooks: HTTP {list_resp.status_code}")
            sys.exit(3)

        webhooks_data = list_resp.json().get("webhooks", [])
        print(f"  - Result:   Discovered {len(webhooks_data)} webhook(s) under this Sandbox app:")
        found_in_list = None
        for wh in webhooks_data:
            wh_id = wh.get("id")
            wh_url = wh.get("url")
            print(f"      * Webhook ID: {wh_id} -> {wh_url}")
            if wh_id == EXPECTED_WEBHOOK_ID:
                found_in_list = wh

        # 3. Execute GET /v1/notifications/webhooks/4J572318CT6195232
        print(f"\n[Request 3/3] Querying GET /v1/notifications/webhooks/{EXPECTED_WEBHOOK_ID}...")
        request_count += 1
        detail_resp = client.get(f"/v1/notifications/webhooks/{EXPECTED_WEBHOOK_ID}", headers=headers)
        detail_debug_id = detail_resp.headers.get("paypal-debug-id", "<none>")
        print(f"  - Status:   HTTP {detail_resp.status_code}")
        print(f"  - Debug ID: {detail_debug_id}")

        print(f"\nTotal PayPal Requests Dispatched: {request_count} (Limit: 3)")

        if detail_resp.status_code == 404:
            print(f"\n[VERIFICATION RESULT: NOT FOUND]")
            print(f"Candidate Webhook ID '{EXPECTED_WEBHOOK_ID}' does NOT exist in this PayPal Sandbox account.")
            print("Action: Do not modify webhooks. Report finding.")
            sys.exit(0)
        elif detail_resp.status_code != 200:
            print(f"\n[VERIFICATION RESULT: UNEXPECTED RESPONSE]")
            print(f"Query returned HTTP {detail_resp.status_code}. Details: {detail_resp.text}")
            sys.exit(0)

        detail = detail_resp.json()
        registered_url = detail.get("url", "")
        event_types = {e.get("name") for e in detail.get("event_types", [])}

        print(f"\n[VERIFIED WEBHOOK METADATA]")
        print(f"  - Webhook ID:      {detail.get('id')}")
        print(f"  - Registered URL:  {registered_url}")
        print(f"  - Target URL Match: {registered_url == EXPECTED_RECEIVER_URL}")

        url_matches = (registered_url == EXPECTED_RECEIVER_URL)
        missing_events = REQUIRED_EVENTS - event_types
        extra_events = event_types - REQUIRED_EVENTS

        print(f"\n[EVENT SUBSCRIPTION COMPARISON]")
        print(f"  - Subscribed Events Count: {len(event_types)}")
        print(f"  - Matches Required 9 Events: {len(missing_events) == 0}")

        if missing_events:
            print(f"  - Missing Events: {sorted(list(missing_events))}")
        if extra_events:
            print(f"  - Additional Subscribed Events: {sorted(list(extra_events))}")

        if url_matches and not missing_events:
            print("\n[CONCLUSION: VERIFIED AND MATCHING]")
            print("Webhook exists, belongs to this Sandbox app, matches the Supabase URL, and has all required events.")
            # Set locally
            set_cmd = f'[Environment]::SetEnvironmentVariable("SENTINEL_PAYPAL_WEBHOOK_ID", "{EXPECTED_WEBHOOK_ID}", "User")'
            subprocess.run(["powershell", "-NoProfile", "-Command", set_cmd], check=True)
            os.environ["SENTINEL_PAYPAL_WEBHOOK_ID"] = EXPECTED_WEBHOOK_ID
            print(f"[ACTION] SENTINEL_PAYPAL_WEBHOOK_ID set to '{EXPECTED_WEBHOOK_ID}' in User environment!")
        else:
            print("\n[CONCLUSION: MISMATCH DETECTED]")
            if not url_matches:
                print(f"  - URL Mismatch: Expected '{EXPECTED_RECEIVER_URL}', got '{registered_url}'")
            if missing_events:
                print(f"  - Subscription Mismatch: Missing {len(missing_events)} required events.")
            print("Action: Stopping without making any modifications.")


if __name__ == "__main__":
    main()
