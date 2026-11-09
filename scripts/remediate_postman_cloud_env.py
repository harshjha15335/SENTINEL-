"""Audit and Remediate Postman Cloud Environment.

Ensures that no raw secrets or tokens exist in Postman Cloud environment values.
Replaces client secret with Postman Local Vault reference {{vault:paypal_client_secret}}
and clears any access tokens.
"""

import json
import os
import subprocess
import sys
import httpx

def get_key() -> str:
    val = os.environ.get("POSTMAN_API_KEY", "")
    if val:
        return val
    try:
        cmd = ["powershell", "-NoProfile", "-Command", '[Environment]::GetEnvironmentVariable("POSTMAN_API_KEY", "User")']
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return ""

key = get_key()
if not key:
    print("[FAIL] POSTMAN_API_KEY not found.")
    sys.exit(1)

headers = {"X-Api-Key": key, "Content-Type": "application/json"}
env_uid = "60068779-db526925-d32a-47b1-99d5-cb3cbb5ef82f"
url = f"https://api.getpostman.com/environments/{env_uid}"

with httpx.Client(timeout=15.0) as client:
    resp = client.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"[FAIL] Could not read environment: HTTP {resp.status_code}")
        sys.exit(2)

    env = resp.json().get("environment", {})
    values = env.get("values", [])
    print(f"Audit of Postman Cloud Environment '{env.get('name')}':")

    secret_shared = False
    for v in values:
        k = v.get("key")
        val = str(v.get("value", ""))
        v_type = v.get("type")
        is_vault = val.startswith("{{vault:")
        is_empty = val == ""
        # Check if actual secret was shared
        if k == "paypal_client_secret" and not is_vault and not is_empty:
            secret_shared = True
            print(f"  - {k} (type: {v_type}): [RAW VALUE DETECTED - Needs Remediation]")
        elif k == "paypal_access_token" and not is_empty:
            print(f"  - {k} (type: {v_type}): [TOKEN DETECTED - Needs Clearing]")
        else:
            print(f"  - {k} (type: {v_type}): Safe (vault reference or empty: {is_vault or is_empty})")

    if secret_shared or any(v.get("key") == "paypal_access_token" and v.get("value") for v in values):
        print("\nRemediating Postman Cloud Environment...")
        sanitized_values = [
            {
                "key": "paypal_base_url",
                "value": "https://api-m.sandbox.paypal.com",
                "type": "default",
                "enabled": True,
            },
            {
                "key": "paypal_client_id",
                "value": "{{vault:paypal_client_id}}",
                "type": "default",
                "enabled": True,
            },
            {
                "key": "paypal_client_secret",
                "value": "{{vault:paypal_client_secret}}",
                "type": "secret",
                "enabled": True,
            },
            {
                "key": "paypal_access_token",
                "value": "",
                "type": "secret",
                "enabled": True,
            },
            {
                "key": "paypal_webhook_id",
                "value": "",
                "type": "default",
                "enabled": True,
            },
        ]
        update_resp = client.put(url, headers=headers, json={"environment": {"name": env.get("name"), "values": sanitized_values}})
        if update_resp.status_code in (200, 201):
            print("[SUCCESS] Postman Cloud Environment sanitized successfully!")
            print("All cloud values have been replaced with local vault references or cleared.")
        else:
            print(f"[FAIL] Remediation update returned HTTP {update_resp.status_code}: {update_resp.text}")
    else:
        print("[INFO] No cloud raw secrets found. Environment is already using safe references.")
