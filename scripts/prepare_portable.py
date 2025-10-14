#!/usr/bin/env python3
"""
Prepare a portable/offline setup for Procnet Live.

What it does:
- (Optionally) pip install -r requirements.txt
- Download vis-network UMD bundle + LICENSE into procnet_live/web/vendor/
- Write a manifest with the exact version and JS checksum

Usage:
  python scripts/prepare_portable.py --version 9.1.6
  python scripts/prepare_portable.py --skip-pip
  python scripts/prepare_portable.py --project-root /path/to/project
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from subprocess import check_call, CalledProcessError

DEFAULT_VERSION = "9.1.6"
CDN_JS = "https://unpkg.com/vis-network@{ver}/standalone/umd/vis-network.min.js"

def license_candidates(ver: str) -> list[str]:
    # vis-network is dual-licensed; the repo has LICENSE-MIT and LICENSE-APACHE-2.0
    # Try GitHub tag first, then unpkg fallbacks.
    return [
        f"https://raw.githubusercontent.com/visjs/vis-network/v{ver}/LICENSE-MIT",
        f"https://raw.githubusercontent.com/visjs/vis-network/v{ver}/LICENSE-APACHE-2.0",
        f"https://unpkg.com/vis-network@{ver}/LICENSE-MIT",
        f"https://unpkg.com/vis-network@{ver}/LICENSE-APACHE-2.0",
    ]

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def fetch(url: str, dest: Path, timeout: float = 30.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "procnet-live/portable-prep"})
    with urllib.request.urlopen(req, timeout=timeout) as r, tmp.open("wb") as f:
        f.write(r.read())
    tmp.replace(dest)

def try_fetch_first(urls: list[str], dest_dir: Path, ver: str) -> Path | None:
    for url in urls:
        base = url.rsplit("/", 1)[-1]  # e.g. LICENSE-MIT
        lic_name = f"{base}.vis-network-{ver}.txt"
        dest = dest_dir / lic_name
        try:
            print(f"[prepare] downloading LICENSE {url} -> {dest}")
            fetch(url, dest)
            return dest
        except urllib.error.HTTPError as e:
            print(f"[prepare] {url} -> HTTP {e.code}, trying next...")
        except Exception as e:
            print(f"[prepare] {url} -> {e.__class__.__name__}: {e}, trying next...")
    return None

def maybe_pip_install(requirements: Path) -> None:
    if not requirements.exists():
        print(f"[prepare] requirements.txt missing at {requirements}, skipping pip install")
        return
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements)]
    print("[prepare] running:", " ".join(cmd))
    try:
        check_call(cmd)
    except CalledProcessError as e:
        print(f"[prepare] pip install failed: {e}")
        sys.exit(e.returncode)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=DEFAULT_VERSION, help="vis-network version (tag) to vendor, e.g. 9.1.6")
    ap.add_argument("--skip-pip", action="store_true", help="skip 'pip install -r requirements.txt'")
    ap.add_argument("--project-root", default=".", help="project root (contains procnet_live/ and requirements.txt)")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    req = root / "requirements.txt"

    if not args.skip_pip:
        maybe_pip_install(req)

    vendor_dir = root / "procnet_live" / "web" / "vendor"
    vendor_dir.mkdir(parents=True, exist_ok=True)

    js_name = f"vis-network-{args.version}.standalone.min.js"
    js_path = vendor_dir / js_name
    js_url = CDN_JS.format(ver=args.version)

    print(f"[prepare] downloading JS {js_url} -> {js_path}")
    fetch(js_url, js_path)

    lic_dest = try_fetch_first(license_candidates(args.version), vendor_dir, args.version)
    if not lic_dest:
        print("[prepare] WARNING: Could not fetch any LICENSE file for vis-network "
              f"v{args.version}. You can proceed, but please include the license later.")

    manifest = {
        "vis_network_version": args.version,
        "js_file": js_name,
        "license_file": lic_dest.name if lic_dest else None,
        "sha256_js": sha256_of(js_path),
    }
    (vendor_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("[prepare] done.")
    print(json.dumps(manifest, indent=2))
    print("[prepare] done.")
    print(f"[prepare] vis-network version: {args.version}")
    print(f"[prepare] js file: {js_name}")
    if lic_dest:
        print(f"[prepare] license file: {lic_dest.name}")
    else:
        print("[prepare] license file: (none downloaded)")
    print(f"[prepare] js sha256: {sha256_of(js_path)}")

if __name__ == "__main__":
    main()
