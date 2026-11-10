"""Package two verified static builds without carrying workspace/review artifacts.

Usage: python scripts/package-static-candidate.py PORTABLE_DIR PAGES_DIR NEW_ZIP
The ZIP contains two alternative host roots plus manifest/checksums, never source or reports.
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

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "validator", ROOT / "apps/api/scripts/validate_static_demo.py"
)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def package(portable, pages, output):
    if output.exists():
        raise ValueError("Refusing to replace an existing candidate")
    source = subprocess.check_output(
        [shutil.which("git") or "/usr/bin/git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()
    payload, snapshots = {}, {}
    for mode, directory in [("portable", portable), ("pages", pages)]:
        snapshot = validator.read_snapshot(directory / "demo-data")
        validator.validate(snapshot)
        snapshots[mode] = snapshot["snapshot"]
        index = (directory / "index.html").read_text()
        prefix = "./assets/" if mode == "portable" else "/SENTINEL-/assets/"
        if prefix not in index:
            raise ValueError(f"Incorrect {mode} asset base")
        if (
            mode == "pages"
            and (directory / "404.html").read_bytes()
            != (directory / "index.html").read_bytes()
        ):
            raise ValueError("Pages requires an identical history fallback")
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("Symlinks are not permitted")
            if not path.is_file():
                continue
            relative = path.relative_to(directory).as_posix()
            allowed = (
                relative in {"index.html", "404.html", "sentinel.svg"}
                or (
                    relative.startswith("assets/")
                    and path.suffix in {".js", ".css", ".woff", ".woff2"}
                )
                or relative in {f"demo-data/{n}.json" for n in validator.FILES}
            )
            if not allowed:
                raise ValueError(f"Unexpected public file: {relative}")
            content = path.read_bytes()
            if re.search(
                rb"-----BEGIN .*PRIVATE KEY|postgres(?:ql)?(?:\+psycopg)?://|\beyJ[A-Za-z0-9_-]+\.eyJ",
                content,
            ):
                raise ValueError(f"Credential pattern in {relative}")
            payload[f"{mode}/{relative}"] = content
    if snapshots["portable"] != snapshots["pages"]:
        raise ValueError("Builds must use the identical validated export")
    manifest = {
        "source_sha": source,
        "snapshot_source_sha": snapshots["portable"]["commit"],
        "snapshot": snapshots["portable"],
        "design_approval": "APPROVED",
        "deployment_approval": "PENDING",
        "host_review": "PENDING",
        "modes": {
            "portable": {"router": "hash", "base": "./"},
            "pages": {
                "router": "history",
                "base": "/SENTINEL-/",
                "fallback": "404.html",
            },
        },
        "limitations": "Read-only approved synthetic/simulated snapshot. No backend workflows or provider execution.",
        "files": {
            name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in sorted(payload.items())
        },
    }
    payload["MANIFEST.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode()
    sums = (
        "\n".join(
            f"{hashlib.sha256(data).hexdigest()}  {name}"
            for name, data in sorted(payload.items())
        )
        + "\n"
    )
    payload["SHA256SUMS"] = sums.encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "x", compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    for name in ["MANIFEST.json", "SHA256SUMS"]:
        output.with_name(output.stem + "-" + name).write_bytes(payload[name])
    print(
        json.dumps(
            {
                "archive": str(output),
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "files": len(payload),
                "source_sha": source,
                "unresolved_references": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    package(*(Path(p).resolve() for p in sys.argv[1:]))
