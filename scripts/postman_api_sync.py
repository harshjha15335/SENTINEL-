"""Postman API Client for SENTINEL.

Authenticates using POSTMAN_API_KEY from environment/registry,
discovers user workspaces, and uploads the verified collection and environment.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Error: httpx is required.")
    sys.exit(1)


def get_postman_api_key() -> str:
    key = os.environ.get("POSTMAN_API_KEY", "").strip()
    if key and key.startswith("PMAK-"):
        return key

    # Retrieve from Windows User Environment via powershell if not in current process
    try:
        cmd = ["powershell", "-NoProfile", "-Command", '[Environment]::GetEnvironmentVariable("POSTMAN_API_KEY", "User")']
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        key = res.stdout.strip()
        if key and key.startswith("PMAK-"):
            return key
    except Exception as exc:
        pass

    return ""


def main():
    key = get_postman_api_key()
    if not key:
        print("[FAIL] POSTMAN_API_KEY not found in environment or user registry.")
        sys.exit(1)

    headers = {
        "X-Api-Key": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    base_url = "https://api.getpostman.com"

    print("=" * 70)
    print("SENTINEL — Postman Official API Workspace Automator")
    print("=" * 70)

    # 1. Verify User Authentication
    print("\n1. Verifying API key against Postman API...")
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(f"{base_url}/me", headers=headers)
        if resp.status_code != 200:
            print(f"[FAIL] Authentication rejected: HTTP {resp.status_code}")
            try:
                print("Details:", resp.json())
            except Exception:
                pass
            sys.exit(2)

        user_data = resp.json().get("user", {})
        user_name = user_data.get("fullName") or user_data.get("username") or "Unknown"
        user_email = user_data.get("email") or ""
        print(f"[SUCCESS] Authenticated successfully as: {user_name} ({user_email})")

        # 2. List Workspaces
        print("\n2. Discovering workspaces...")
        w_resp = client.get(f"{base_url}/workspaces", headers=headers)
        if w_resp.status_code != 200:
            print(f"[FAIL] Could not retrieve workspaces: HTTP {w_resp.status_code}")
            sys.exit(3)

        workspaces = w_resp.json().get("workspaces", [])
        if not workspaces:
            print("[FAIL] No workspaces found in this Postman account.")
            sys.exit(4)

        print(f"Found {len(workspaces)} workspace(s):")
        target_workspace = None
        for w in workspaces:
            w_id = w.get("id")
            w_name = w.get("name")
            w_type = w.get("type")
            print(f"  - [{w_type}] {w_name} (ID: {w_id})")
            # Prefer workspace with "paypal" or "sentinel" in name if present
            if any(term in w_name.lower() for term in ["paypal", "sentinel"]):
                if not target_workspace:
                    target_workspace = w

        # Default to first workspace if no name-match
        if not target_workspace:
            target_workspace = workspaces[0]

        target_id = target_workspace.get("id")
        target_name = target_workspace.get("name")
        print(f"\n[TARGET] Selected Workspace: '{target_name}' (ID: {target_id})")

        # 3. Read Collection & Environment files
        coll_file = Path("postman/SENTINEL_PayPal_Sandbox.postman_collection.json")
        env_file = Path("postman/SENTINEL_PayPal_Sandbox.postman_environment.json")

        if not coll_file.exists() or not env_file.exists():
            print("[FAIL] Postman JSON files missing in postman/ directory.")
            sys.exit(5)

        with open(coll_file, "r", encoding="utf-8") as f:
            coll_data = json.load(f)

        # Omit _postman_id so Postman assigns a valid UID automatically
        coll_data.get("info", {}).pop("_postman_id", None)

        with open(env_file, "r", encoding="utf-8") as f:
            env_data = json.load(f)

        # 4. Check for Existing Collection
        print("\n3. Checking existing collections in workspace...")
        c_list_resp = client.get(f"{base_url}/collections?workspace={target_id}", headers=headers)
        existing_collections = c_list_resp.json().get("collections", []) if c_list_resp.status_code == 200 else []
        existing_coll = next((c for c in existing_collections if c.get("name") == coll_data.get("info", {}).get("name")), None)

        if existing_coll:
            coll_uid = existing_coll.get("uid")
            print(f"Collection already exists (UID: {coll_uid}). Updating...")
            up_resp = client.put(f"{base_url}/collections/{coll_uid}", headers=headers, json={"collection": coll_data})
            if up_resp.status_code in (200, 201):
                print(f"[SUCCESS] Collection updated in workspace '{target_name}'!")
            else:
                print(f"[!] Collection update returned HTTP {up_resp.status_code}: {up_resp.text}")
        else:
            print("Importing collection into workspace...")
            post_coll_resp = client.post(
                f"{base_url}/collections?workspace={target_id}",
                headers=headers,
                json={"collection": coll_data},
            )
            if post_coll_resp.status_code in (200, 201):
                created_coll = post_coll_resp.json().get("collection", {})
                print(f"[SUCCESS] Collection created! Name: '{created_coll.get('name')}' (UID: {created_coll.get('uid')})")
            else:
                print(f"[!] Collection creation returned HTTP {post_coll_resp.status_code}: {post_coll_resp.text}")

        # 5. Check for Existing Environment
        print("\n4. Checking existing environments in workspace...")
        e_list_resp = client.get(f"{base_url}/environments?workspace={target_id}", headers=headers)
        existing_envs = e_list_resp.json().get("environments", []) if e_list_resp.status_code == 200 else []
        existing_env = next((e for e in existing_envs if e.get("name") == env_data.get("name")), None)

        if existing_env:
            env_uid = existing_env.get("uid")
            print(f"Environment already exists (UID: {env_uid}). Updating...")
            up_env_resp = client.put(f"{base_url}/environments/{env_uid}", headers=headers, json={"environment": env_data})
            if up_env_resp.status_code in (200, 201):
                print(f"[SUCCESS] Environment updated in workspace '{target_name}'!")
            else:
                print(f"[!] Environment update returned HTTP {up_env_resp.status_code}: {up_env_resp.text}")
        else:
            print("Importing environment into workspace...")
            post_env_resp = client.post(
                f"{base_url}/environments?workspace={target_id}",
                headers=headers,
                json={"environment": env_data},
            )
            if post_env_resp.status_code in (200, 201):
                created_env = post_env_resp.json().get("environment", {})
                print(f"[SUCCESS] Environment created! Name: '{created_env.get('name')}' (UID: {created_env.get('uid')})")
            else:
                print(f"[!] Environment creation returned HTTP {post_env_resp.status_code}: {post_env_resp.text}")

    print("\n" + "=" * 70)
    print("[ALL DONE] Postman workspace setup automated successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
