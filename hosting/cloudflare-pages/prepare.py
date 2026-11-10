"""Verify the immutable Gate 2A package and add only reviewed static-host configuration.

Usage: python hosting/cloudflare-pages/prepare.py GATE2A_ZIP NEW_RELEASE_DIRECTORY
Only NEW_RELEASE_DIRECTORY/publish is a future publish root. This script never deploys.
"""

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).resolve().parent
INPUT_SHA = "40d7818056312e178f7d8911f8cf9dd2c299f262e0c2c280162d0cc90e984f1c"
INPUT_SOURCE = "5261ebf24c9e2c58949fc883e8c377acea101d37"
spec = importlib.util.spec_from_file_location(
    "validator", ROOT / "apps/api/scripts/validate_static_demo.py"
)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def prepare(archive, release):
    if release.exists():
        raise ValueError("Refusing to overwrite an existing release")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != INPUT_SHA:
        raise ValueError("Unexpected Gate 2A package hash")
    payload = {}
    with ZipFile(archive) as source:
        if source.testzip() is not None:
            raise ValueError("Damaged ZIP")
        sums = dict(
            line.split("  ", 1)[::-1]
            for line in source.read("SHA256SUMS").decode().splitlines()
        )
        if set(sums) != set(source.namelist()) - {"SHA256SUMS"}:
            raise ValueError("Incomplete checksum manifest")
        for name, digest in sums.items():
            if hashlib.sha256(source.read(name)).hexdigest() != digest:
                raise ValueError("Package checksum mismatch")
        original = json.loads(source.read("MANIFEST.json"))
        if original["source_sha"] != INPUT_SOURCE:
            raise ValueError("Unexpected application source")
        for name in source.namelist():
            if name.startswith("portable/"):
                relative = name.removeprefix("portable/")
                if (
                    ".." in Path(relative).parts
                    or not relative
                    or relative.startswith("/")
                ):
                    raise ValueError("Unsafe archive entry")
                if (
                    original["files"][name]["sha256"]
                    != hashlib.sha256(source.read(name)).hexdigest()
                ):
                    raise ValueError("Payload mismatch")
                payload[relative] = source.read(name)
    for name in ["_headers", "404.html"]:
        payload[name] = (CONFIG / name).read_bytes()
    lines = payload["_headers"].decode().splitlines()
    if (
        max(map(len, lines)) > 2000
        or sum(bool(l) and not l.startswith((" ", "#")) for l in lines) > 100
    ):
        raise ValueError("Cloudflare header limits exceeded")
    if any(
        name in payload
        for name in ["_worker.js", "_routes.json", "wrangler.toml", ".env"]
    ):
        raise ValueError("Unexpected operational configuration")
    if len(payload) > 1000 or max(map(len, payload.values())) > 25 * 1024 * 1024:
        raise ValueError("Direct Upload file limits exceeded")
    for name, content in payload.items():
        if re.search(
            rb"-----BEGIN .*PRIVATE KEY|postgres(?:ql)?(?:\+psycopg)?://|\beyJ[A-Za-z0-9_-]+\.eyJ",
            content,
        ):
            raise ValueError("Credential pattern in public files")
    git = shutil.which("git") or "/usr/bin/git"
    revision = subprocess.check_output(
        [git, "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if subprocess.check_output(
        [git, "status", "--porcelain"], cwd=ROOT, text=True
    ).strip():
        raise ValueError(
            "Commit configuration before preparing a source-labelled release"
        )
    publish = release / "publish"
    publish.mkdir(parents=True)
    try:
        for name, content in sorted(payload.items()):
            target = publish / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(0o644)
        validated = validator.validate(validator.read_snapshot(publish / "demo-data"))
        manifest = {
            "host_config_source": revision,
            "application_source": INPUT_SOURCE,
            "input_package_sha256": INPUT_SHA,
            "snapshot_validation": validated,
            "publish_directory": "publish",
            "router": "hash",
            "base": "./",
            "deployment_approval": "PENDING",
            "actual_host_verified": False,
            "files": {
                n: {"bytes": len(c), "sha256": hashlib.sha256(c).hexdigest()}
                for n, c in sorted(payload.items())
            },
        }
        (release / "HOST-MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        (release / "SHA256SUMS").write_text(
            "".join(
                f"{hashlib.sha256(c).hexdigest()}  publish/{n}\n"
                for n, c in sorted(payload.items())
            )
        )
        with ZipFile(
            release / "cloudflare-publish.zip", "x", compression=ZIP_DEFLATED
        ) as output:
            for name, content in sorted(payload.items()):
                info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                output.writestr(info, content)
        print(
            json.dumps(
                {
                    "revision": revision,
                    "files": len(payload),
                    "validation": validated,
                    "publish": str(publish),
                }
            )
        )
    except Exception:
        shutil.rmtree(release)
        raise


if __name__ == "__main__":
    prepare(*(Path(x).resolve() for x in sys.argv[1:]))
