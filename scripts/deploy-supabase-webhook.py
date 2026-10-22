#!/usr/bin/env python3
"""Create a Supabase project and deploy SENTINEL's webhook using secure account access.

Requires SUPABASE_ACCESS_TOKEN in the environment. No tokens or database passwords
are accepted as command-line arguments or printed. This script does not push Git.
"""

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.supabase.com/v1"


def function_upload():
    """Official CLI-compatible multipart upload, also usable with proxy-backed keys."""
    boundary = "sentinel-" + secrets.token_hex(16)
    prefix = "supabase/functions/paypal-webhook/"
    metadata = {
        "name": "paypal-webhook",
        "entrypoint_path": prefix + "index.ts",
        "verify_jwt": False,
    }
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="metadata"\r\n\r\n'.encode()
        + json.dumps(metadata).encode()
        + b"\r\n"
    ]
    for filename in ["index.ts", "receiver.ts"]:
        path = prefix + filename
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path}"\r\nContent-Type: application/typescript\r\n\r\n'.encode()
            + (ROOT / path).read_bytes()
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument(
        "--project-ref", help="Deploy to an existing project instead of creating one"
    )
    parser.add_argument(
        "--use-cli",
        action="store_true",
        help="Deploy through the CLI instead of direct API upload",
    )
    args = parser.parse_args()
    token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    if not token:
        parser.error(
            "Add SUPABASE_ACCESS_TOKEN in secure environment settings. Create an account at https://supabase.com/dashboard first if needed."
        )
    cli = os.environ.get("SUPABASE_CLI") or shutil.which("supabase")
    if args.use_cli and not cli:
        parser.error(
            "Install the official Supabase CLI or set SUPABASE_CLI to its path"
        )

    def request(path, body=None, method=None, content_type="application/json"):
        req = urllib.request.Request(
            API + path,
            data=body
            if isinstance(body, bytes)
            else (None if body is None else json.dumps(body).encode()),
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": content_type,
            },
            method=method or ("POST" if body is not None else "GET"),
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read()
                return json.loads(data) if data else None
        except urllib.error.HTTPError as exc:
            raise SystemExit(
                f"Supabase API returned HTTP {exc.code}; response body withheld to protect credentials"
            ) from None
        except urllib.error.URLError:
            raise SystemExit(
                "Cannot reach Supabase API; check environment network access. No deployment success is assumed."
            ) from None

    private = Path(
        os.environ.get(
            "SENTINEL_SUPABASE_STATE_DIR",
            str(ROOT.parent / "sentinel-supabase-private"),
        )
    )
    private.mkdir(mode=0o700, parents=True, exist_ok=True)
    private.chmod(0o700)
    state_path = private / "deployment.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}

    def save():
        fd = os.open(state_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(state, stream)
        state_path.chmod(0o600)

    ref = args.project_ref or state.get("project_ref")
    if not ref:
        organizations = request("/organizations")
        organization = os.environ.get("SUPABASE_ORGANIZATION_ID")
        available = {org.get("slug") or org["id"] for org in organizations}
        if not organization and len(available) == 1:
            organization = next(iter(available))
        if not organization or organization not in available:
            raise SystemExit(
                "Set SUPABASE_ORGANIZATION_ID to your chosen organization; the script will not guess between accounts."
            )
        if state.get("creation_started"):
            candidates = [
                p
                for p in request("/projects")
                if p.get("name") == state["name"]
                and p.get("organization_id") == organization
            ]
            if len(candidates) != 1:
                raise SystemExit(
                    "A previous creation attempt has an unknown outcome. Inspect Supabase projects, then pass --project-ref; no duplicate project was created."
                )
            project = candidates[0]
        else:
            state.update(
                name="sentinel-" + secrets.token_hex(3),
                db_password=secrets.token_urlsafe(32),
                creation_started=True,
            )
            save()  # Preserve the password and creation intent before an ambiguous timeout.
            print(
                "Creating SENTINEL project in your selected organization; no plan upgrade is requested."
            )
            project = request(
                "/projects",
                {
                    "name": state["name"],
                    "organization_id": organization,
                    "db_pass": state["db_password"],
                    "region": args.region,
                },
            )
        ref = project["id"]
    if not isinstance(ref, str) or not ref.isalnum():
        raise SystemExit("Unexpected project reference")
    state["project_ref"] = ref
    save()
    print("Waiting for project readiness...")
    for _ in range(120):
        if request(f"/projects/{ref}").get("status") == "ACTIVE_HEALTHY":
            break
        time.sleep(5)
    else:
        raise SystemExit(
            "Project is still provisioning; rerun later to resume without creating another project"
        )

    migration = ROOT / "supabase/migrations/202610200001_webhook_inbox.sql"
    request(f"/projects/{ref}/database/query", {"query": migration.read_text()})
    if not args.use_cli:
        body, content_type = function_upload()
        request(
            f"/projects/{ref}/functions/deploy?slug=paypal-webhook",
            body,
            content_type=content_type,
        )
    else:
        subprocess.run(
            [
                cli,
                "functions",
                "deploy",
                "paypal-webhook",
                "--project-ref",
                ref,
                "--use-api",
                "--no-verify-jwt",
            ],
            cwd=ROOT,
            check=True,
        )
    url = f"https://{ref}.supabase.co/functions/v1/paypal-webhook"
    with urllib.request.urlopen(url, timeout=30) as response:
        if response.status != 200:
            raise SystemExit(
                "Deployment check failed: public endpoint did not return HTTP 200"
            )
    unsigned = urllib.request.Request(
        url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        urllib.request.urlopen(unsigned, timeout=30).close()
        raise SystemExit("Deployment check failed: unsigned webhook was accepted")
    except urllib.error.HTTPError as exc:
        if exc.code != 400:
            raise SystemExit(
                f"Deployment check failed: expected unsigned rejection 400, got {exc.code}"
            ) from None
    state["webhook_url"] = url
    save()
    print("Public webhook URL:", url)
    print(
        "Register this URL in the PayPal sandbox app, then configure PayPal credentials and the returned webhook ID in Supabase Edge Function secrets."
    )
    print(
        "Real signed delivery remains unverified until PayPal sends a signed event. Run the inbox bridge to update SENTINEL."
    )


if __name__ == "__main__":
    main()
