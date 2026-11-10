"""Read-only inspection of PayPal Sandbox Webhook Event History.

Safety:
- Max 3 requests (1 OAuth token, 1 List Events, 1 Event Details if available)
- In-memory credential handling only
- Read-only GET requests only; zero financial actions
"""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.verify_existing_paypal_webhook import get_secret

BASE_URL = "https://api-m.sandbox.paypal.com"
EXPECTED_WEBHOOK_ID = "4J572318CT6195232"


def main():
    print("=" * 70)
    print("SENTINEL — PayPal Sandbox Webhook Events History (Read-Only)")
    print("=" * 70)

    client_id = get_secret("SENTINEL_PAYPAL_CLIENT_ID")
    client_secret = get_secret("SENTINEL_PAYPAL_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("[FAIL] Missing PayPal Sandbox credentials.")
        sys.exit(1)

    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        # Request 1: OAuth token
        print("\n[Request 1/3] Obtaining OAuth token from PayPal Sandbox...")
        oauth_resp = client.post(
            "/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"Accept": "application/json"},
        )
        debug_id_oauth = oauth_resp.headers.get("paypal-debug-id", "<none>")
        print(f"  - Status:   HTTP {oauth_resp.status_code}")
        print(f"  - Debug ID: {debug_id_oauth}")

        if oauth_resp.status_code != 200:
            print("[FAIL] OAuth failed.")
            sys.exit(2)

        token = oauth_resp.json().get("access_token")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        # Request 2: List webhooks-events
        print("\n[Request 2/3] Querying GET /v1/notifications/webhooks-events (page_size=25)...")
        events_resp = client.get(
            "/v1/notifications/webhooks-events",
            headers=headers,
            params={"page_size": 25},
        )
        debug_id_events = events_resp.headers.get("paypal-debug-id", "<none>")
        print(f"  - Status:   HTTP {events_resp.status_code}")
        print(f"  - Debug ID: {debug_id_events}")

        if events_resp.status_code != 200:
            print(f"[FAIL] Could not query webhook events: {events_resp.text}")
            sys.exit(3)

        events_data = events_resp.json()
        events = events_data.get("events", [])
        total_count = events_data.get("total_count", len(events))
        print(f"  - Total events reported: {total_count}")
        print(f"  - Events in page: {len(events)}")

        if not events:
            print("\n[FINDING] Zero webhook events exist in this PayPal Sandbox account.")
            print("  - No Sandbox transaction, checkout, or capture has generated an event under this REST app.")
            print("  - No simulated webhook deliveries exist in the Sandbox event log.")
            return

        for idx, ev in enumerate(events, start=1):
            ev_id = ev.get("id")
            ev_type = ev.get("event_type")
            create_time = ev.get("create_time")
            status = ev.get("event_state")
            summary = ev.get("summary")
            resource_type = ev.get("resource_type")
            print(f"\n  Event #{idx}:")
            print(f"    ID:            {ev_id}")
            print(f"    Type:          {ev_type}")
            print(f"    Created:       {create_time}")
            print(f"    Status:        {status}")
            print(f"    Resource Type: {resource_type}")
            print(f"    Summary:       {summary}")

        # Check details of the first event if available
        first_event = events[0]
        ev_id = first_event.get("id")
        print(f"\n[Request 3/3] Querying GET /v1/notifications/webhooks-events/{ev_id}...")
        detail_resp = client.get(f"/v1/notifications/webhooks-events/{ev_id}", headers=headers)
        if detail_resp.status_code == 200:
            detail = detail_resp.json()
            print("  - Event Detail retrieved successfully:")
            print(f"    ID:       {detail.get('id')}")
            print(f"    Type:     {detail.get('event_type')}")
            print(f"    Resource: {detail.get('resource_type')}")
        else:
            print(f"  - Event detail query returned HTTP {detail_resp.status_code}")


if __name__ == "__main__":
    main()
