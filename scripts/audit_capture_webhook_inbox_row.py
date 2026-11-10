"""SENTINEL — Strictly Read-Only Audit of Supabase Webhook Inbox Row.

Inspects the exact inbox row matching PayPal capture webhook WH-8PS64288TE824605G-0B900988FU9876821
and all LIVE_SANDBOX events. Pure PostgREST SELECT: zero mutations, zero leases.

Usage:
    python scripts/audit_capture_webhook_inbox_row.py
"""

import getpass
import json
import os
import sys

import httpx

PROJECT_URL = "https://cfslzvvdjxstpupkqbpw.supabase.co"
TARGET_EVENT_ID = "WH-8PS64288TE824605G-0B900988FU9876821"


def main() -> None:
    print("=" * 70)
    print("SENTINEL — Read-Only Supabase Inbox Row Audit")
    print(f"Target Event ID: {TARGET_EVENT_ID}")
    print("=" * 70)

    key = os.environ.get("SENTINEL_SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not key:
        try:
            key = getpass.getpass("Enter Supabase service_role Key: ").strip()
        except (KeyboardInterrupt, EOFError):
            sys.exit("\n[ABORT] Entry cancelled.")

    if not key:
        sys.exit("[FAIL] Supabase service_role key is required.")

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }

    with httpx.Client(timeout=15.0) as client:
        # 1. Query exact target event ID
        print(f"\n[1/3] Querying specific inbox row: {TARGET_EVENT_ID}...")
        url = f"{PROJECT_URL}/rest/v1/sentinel_webhook_inbox"
        params = {
            "provider_event_id": f"eq.{TARGET_EVENT_ID}",
            "select": "id,provider_event_id,event_type,status,data_origin,received_at,processed_at,attempts,available_at,lease_token,last_error",
        }
        try:
            resp = client.get(url, headers=headers, params=params)
            print(f"  - HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    print("  - [FOUND] Inbox Row Details:")
                    print(json.dumps(rows[0], indent=4))
                else:
                    print(f"  - [NOT FOUND] No row in sentinel_webhook_inbox matching {TARGET_EVENT_ID}!")
            else:
                print(f"  - [FAIL] PostgREST returned HTTP {resp.status_code}: {resp.text}")
        except httpx.HTTPError as exc:
            print(f"  - [ERROR] Network error: {exc}")

        # 2. Query all LIVE_SANDBOX events in inbox
        print("\n[2/3] Querying all LIVE_SANDBOX inbox rows...")
        params_all = {
            "data_origin": "eq.LIVE_SANDBOX",
            "select": "id,provider_event_id,event_type,status,received_at,processed_at,attempts,last_error",
            "order": "received_at.asc",
        }
        try:
            resp_all = client.get(url, headers=headers, params=params_all)
            print(f"  - HTTP Status: {resp_all.status_code}")
            if resp_all.status_code == 200:
                all_rows = resp_all.json()
                print(f"  - Total LIVE_SANDBOX rows: {len(all_rows)}")
                for idx, r in enumerate(all_rows, 1):
                    print(f"    Row {idx}: {r.get('provider_event_id')} | {r.get('event_type')} | status: {r.get('status')} | received: {r.get('received_at')} | processed: {r.get('processed_at')} | attempts: {r.get('attempts')} | error: {r.get('last_error')}")
            else:
                print(f"  - [FAIL] HTTP {resp_all.status_code}: {resp_all.text}")
        except httpx.HTTPError as exc:
            print(f"  - [ERROR] Network error: {exc}")

        # 3. Query aggregate metrics RPC
        print("\n[3/3] Querying sentinel_webhook_metrics RPC...")
        try:
            resp_m = client.post(f"{PROJECT_URL}/rest/v1/rpc/sentinel_webhook_metrics", headers=headers, json={})
            print(f"  - HTTP Status: {resp_m.status_code}")
            if resp_m.status_code == 200:
                print("  - Aggregate Metrics:")
                print(json.dumps(resp_m.json(), indent=4))
        except httpx.HTTPError as exc:
            print(f"  - [ERROR] Network error: {exc}")

    print("\n" + "=" * 70)
    print("AUDIT COMPLETE (Zero mutations, zero leases)")
    print("=" * 70)


if __name__ == "__main__":
    main()

