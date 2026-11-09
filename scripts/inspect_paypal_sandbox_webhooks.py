"""Read-Only PayPal Webhook Inspection Script for SENTINEL.

Prepared for separately authorized execution to inspect whether the registered
webhook ID (4J572318CT6195232) is active and subscribed to the expected Supabase
receiver URL (https://cfslzvvdjxstpupkqbpw.supabase.co/functions/v1/paypal-webhook).

SAFETY RULES:
1. ONLY read-only GET requests (List Webhooks, Show Webhook Details).
2. Absolutely NO webhook creation, modification, or deletion.
3. Absolutely NO financial calls (no payments, captures, refunds, disputes).
4. Requires explicit --execute flag and an authorized access token to send any network requests.
"""

import argparse
import json
import os
import sys
from typing import Any

EXPECTED_WEBHOOK_ID = "4J572318CT6195232"
EXPECTED_RECEIVER_URL = "https://cfslzvvdjxstpupkqbpw.supabase.co/functions/v1/paypal-webhook"
BASE_URL = "https://api-m.sandbox.paypal.com"


def inspect_webhooks(access_token: str | None = None, execute: bool = False) -> int:
    print("=" * 70)
    print("SENTINEL — Read-Only PayPal Sandbox Webhook Inspector")
    print("=" * 70)

    print(f"\nConfiguration Targets:")
    print(f"  - Target PayPal Host:    {BASE_URL}")
    print(f"  - Expected Webhook ID:   {EXPECTED_WEBHOOK_ID}")
    print(f"  - Expected Receiver URL: {EXPECTED_RECEIVER_URL}")
    print(f"  - Endpoints to inspect:  GET /v1/notifications/webhooks")
    print(f"                           GET /v1/notifications/webhooks/{EXPECTED_WEBHOOK_ID}")

    if not execute:
        print("\n[DRY RUN MODE]")
        print("No network requests were performed.")
        print("To run this check once you have authorized it, provide an acquired access token:")
        print(f"    python scripts/inspect_paypal_sandbox_webhooks.py --access-token <TOKEN> --execute")
        return 0

    if not access_token:
        print("\n[!] Error: An access token is required for read-only webhook inspection.")
        print("    Run scripts/inspect_paypal_sandbox_webhooks.py --access-token <TOKEN> --execute")
        return 1

    try:
        import httpx
    except ImportError:
        print("Error: httpx is required.")
        return 2

    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    print("\nExecuting read-only GET /v1/notifications/webhooks...")
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        list_resp = client.get("/v1/notifications/webhooks", headers=headers)
        debug_id = list_resp.headers.get("paypal-debug-id", "<none>")
        print(f"Response Status: {list_resp.status_code} (Debug-ID: {debug_id})")

        if list_resp.status_code != 200:
            print(f"[!] Failed to list webhooks: HTTP {list_resp.status_code}")
            return 3

        data = list_resp.json()
        webhooks = data.get("webhooks", [])
        print(f"Discovered {len(webhooks)} webhook(s) in sandbox account:")
        found = False
        for wh in webhooks:
            w_id = wh.get("id")
            w_url = wh.get("url")
            print(f"  - ID: {w_id} -> URL: {w_url}")
            if w_id == EXPECTED_WEBHOOK_ID:
                found = True

        if found:
            print(f"\n[MATCH] Expected Webhook ID '{EXPECTED_WEBHOOK_ID}' is registered!")
        else:
            print(f"\n[NOTICE] Webhook ID '{EXPECTED_WEBHOOK_ID}' was not listed among discovered webhooks.")

        # Show Webhook Details
        print(f"\nExecuting read-only GET /v1/notifications/webhooks/{EXPECTED_WEBHOOK_ID}...")
        detail_resp = client.get(f"/v1/notifications/webhooks/{EXPECTED_WEBHOOK_ID}", headers=headers)
        print(f"Detail Status: {detail_resp.status_code}")
        if detail_resp.status_code == 200:
            wh_detail = detail_resp.json()
            actual_url = wh_detail.get("url")
            events = [e.get("name") for e in wh_detail.get("event_types", [])]
            print(f"  - Registered URL: {actual_url}")
            print(f"  - Matches Expected Supabase URL: {actual_url == EXPECTED_RECEIVER_URL}")
            print(f"  - Subscribed Event Types: {len(events)}")
            for ev in events[:5]:
                print(f"      * {ev}")
            if len(events) > 5:
                print(f"      * ... and {len(events) - 5} more")
        elif detail_resp.status_code == 404:
            print(f"[!] Webhook ID '{EXPECTED_WEBHOOK_ID}' was not found (HTTP 404).")
        else:
            print(f"[!] Webhook detail query returned HTTP {detail_resp.status_code}.")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read-only PayPal Sandbox Webhook Inspector")
    parser.add_argument("--access-token", type=str, help="Valid PayPal Sandbox Bearer access token")
    parser.add_argument("--execute", action="store_true", help="Execute read-only network inspection")
    args = parser.parse_args()
    sys.exit(inspect_webhooks(access_token=args.access_token, execute=args.execute))

