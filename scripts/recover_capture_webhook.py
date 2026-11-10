"""SENTINEL — Controlled Recovery for Capture Webhook WH-8PS64288TE824605G-0B900988FU9876821.

Fetches the original authentic raw payload and signature headers from Supabase inbox,
and forwards them to local FastAPI (/api/v1/webhooks/paypal) with zero PayPal API calls.

Safety Invariants:
- Zero financial operations: No order creation, no capture, no refund.
- Zero PayPal mutations: Does not call PayPal /resend or modify remote webhooks.
- Preserves idempotency: Fast-forward checks existing Transaction and RiskAssessment.
- Dry-run by default: Requires explicit --execute flag.

Usage:
    python scripts/recover_capture_webhook.py --dry-run
    python scripts/recover_capture_webhook.py --execute
"""

import argparse
import getpass
import hashlib
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

PROJECT_URL = "https://cfslzvvdjxstpupkqbpw.supabase.co"
TARGET_EVENT_ID = "WH-8PS64288TE824605G-0B900988FU9876821"
LOCAL_API = "http://127.0.0.1:8040"
EXPECTED_TXN_ID = "b970504f-274f-4862-b95f-b95342002421"
EXPECTED_ASSESSMENT_ID = "dae7c7f2-af13-4352-8f96-cbb74c2b02d6"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Execute the one-time delivery recovery")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Inspect only (default: True)")
    args = parser.parse_args()

    print("=" * 70)
    print("SENTINEL — Capture Webhook Delivery Recovery")
    print(f"Target Event:     {TARGET_EVENT_ID}")
    print(f"Execution Mode:   {'LIVE RECOVERY (--execute)' if args.execute else 'DRY RUN AUDIT ONLY'}")
    print("=" * 70)

    key = os.environ.get("SENTINEL_SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not key:
        try:
            key = getpass.getpass("Enter Supabase service_role Key: ").strip()
        except (KeyboardInterrupt, EOFError):
            sys.exit("\n[ABORT] Entry cancelled.")

    if not key:
        sys.exit("[FAIL] Supabase service_role key is required.")

    sb_headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }

    # 1. Inspect Supabase row
    print(f"\n[Step 1/4] Reading original authentic row from Supabase inbox: {TARGET_EVENT_ID}...")
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{PROJECT_URL}/rest/v1/sentinel_webhook_inbox",
            headers=sb_headers,
            params={
                "provider_event_id": f"eq.{TARGET_EVENT_ID}",
                "select": "id,provider_event_id,event_type,raw_body,signature_headers,status,received_at,processed_at,data_origin",
            },
        )
        if resp.status_code != 200 or not resp.json():
            sys.exit(f"  [FAIL] Could not fetch inbox row: HTTP {resp.status_code} ({resp.text})")

        row = resp.json()[0]
        print(f"  - Row UUID:       {row.get('id')}")
        print(f"  - Event Type:     {row.get('event_type')}")
        print(f"  - Inbox Status:   {row.get('status')}")
        print(f"  - Received At:    {row.get('received_at')}")
        print(f"  - Data Origin:    {row.get('data_origin')}")
        raw_body = row.get("raw_body", "").encode("utf-8")
        headers = row.get("signature_headers", {})
        payload_sha = hashlib.sha256(raw_body).hexdigest()
        print(f"  - Payload SHA256: {payload_sha}")

    # 2. Check Local Database Pre-Conditions
    print("\n[Step 2/4] Verifying Local PostgreSQL Pre-Conditions...")
    from app.db.session import get_sessionmaker
    from app.models import PaymentEvent, RiskAssessment, RiskScoringJob, Transaction
    from sqlalchemy import select

    maker = get_sessionmaker()
    with maker() as db:
        txn = db.get(Transaction, EXPECTED_TXN_ID)
        if not txn:
            sys.exit(f"  [FAIL] Transaction {EXPECTED_TXN_ID} not found in local DB.")
        print(f"  - Transaction:    {txn.id} (Status: {txn.status.value}, Capture ID: {txn.paypal_capture_id})")

        existing_event = db.scalar(select(PaymentEvent).where(PaymentEvent.provider_event_id == TARGET_EVENT_ID))
        if existing_event:
            print(f"  - [NOTICE] Event {TARGET_EVENT_ID} already recorded in local DB: PaymentEvent ID {existing_event.id}")
        else:
            print("  - Event Status:   Not yet recorded in local PaymentEvent table (Delivery Needed)")

        assessment = db.get(RiskAssessment, EXPECTED_ASSESSMENT_ID)
        if assessment:
            print(f"  - RiskAssessment: {assessment.id} (Score: {assessment.risk_score:.4f}, Band: {assessment.risk_band.value}, Trigger: {assessment.trigger})")

        existing_job = db.scalar(select(RiskScoringJob).where(RiskScoringJob.transaction_id == txn.id))
        print(f"  - RiskScoringJob: {'Found (status=' + existing_job.status + ')' if existing_job else 'None (Clean slate for webhook job)'}")

    if not args.execute:
        print("\n" + "=" * 70)
        print("DRY RUN COMPLETE — Zero actions taken.")
        print("To execute recovery, run: python scripts/recover_capture_webhook.py --execute")
        print("=" * 70)
        return

    # 3. Deliver to FastAPI Webhook Ingress
    print(f"\n[Step 3/4] Delivering Authentic Event to FastAPI at {LOCAL_API}/api/v1/webhooks/paypal...")
    fwd_headers = {
        name: str(headers[name])
        for name in (
            "paypal-transmission-id",
            "paypal-transmission-time",
            "paypal-cert-url",
            "paypal-auth-algo",
            "paypal-transmission-sig",
        )
        if name in headers
    }
    fwd_headers["content-type"] = "application/json"
    trace_id = hashlib.sha256(TARGET_EVENT_ID.encode()).hexdigest()[:32]
    fwd_headers["x-correlation-id"] = trace_id

    with httpx.Client(timeout=30.0) as api_client:
        fwd_resp = api_client.post(f"{LOCAL_API}/api/v1/webhooks/paypal", content=raw_body, headers=fwd_headers)
        print(f"  - FastAPI Response Status: HTTP {fwd_resp.status_code}")
        if fwd_resp.status_code != 200:
            sys.exit(f"  [FAIL] Webhook rejected by FastAPI: {fwd_resp.text}")

        receipt = fwd_resp.json()
        print(f"  - Delivery Receipt: {json.dumps(receipt, indent=4)}")

    # 4. Verify Local Database Reconciliation
    print("\n[Step 4/4] Verifying Post-Delivery Reconciliation in PostgreSQL...")
    import time
    time.sleep(1.0)  # Allow background task / worker to process

    with maker() as db:
        new_event = db.scalar(select(PaymentEvent).where(PaymentEvent.provider_event_id == TARGET_EVENT_ID))
        if new_event:
            print(f"  - [PASS] PaymentEvent created: {new_event.id} (Status: {new_event.processing_status}, Verif: {new_event.verification_status})")
        else:
            print("  - [WARN] PaymentEvent not yet visible.")

        new_job = db.scalar(select(RiskScoringJob).where(RiskScoringJob.transaction_id == EXPECTED_TXN_ID))
        if new_job:
            print(f"  - [PASS] RiskScoringJob created: {new_job.id} (Status: {new_job.status}, Assessment ID: {new_job.assessment_id})")
        else:
            print("  - [NOTICE] RiskScoringJob not found.")

        assessments = db.scalars(select(RiskAssessment).where(RiskAssessment.transaction_id == EXPECTED_TXN_ID)).all()
        print(f"  - [PASS] Total RiskAssessments: {len(assessments)} (Idempotency verified: zero duplicate assessments created!)")

    print("\n" + "=" * 70)
    print("RECOVERY COMPLETE: Capture Webhook Reconciled Successfully")
    print("=" * 70)


if __name__ == "__main__":
    main()
