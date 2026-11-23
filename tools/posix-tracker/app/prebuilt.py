"""Prebuilt libraries from the libc's GitHub releases.

Used only when a release no longer builds locally (an old tag with a newer
toolchain or missing system headers): the release's archive for this
machine (`<name>-<version>-linux-<arch>.tar.gz`) is downloaded, checked
against the release's SHA256SUMS and against the digest GitHub reports, and
its `lib/*.a` is kept in WORK_DIR/prebuilt/<tag>/. Later scans reuse it
without network.
"""
from __future__ import annotations

import hashlib
import io
import json
import platform
import re
import subprocess
import tarfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast

from config import DEV_NAME, HAJLIBC_REPO, WORK_DIR

PREBUILT_DIR = WORK_DIR / "prebuilt"
API = "https://api.github.com"
ARCHES = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}


def _github_repo() -> str | None:
    """owner/name of the libc on GitHub, from its `origin` remote."""
    r = subprocess.run(["git", "-C", str(HAJLIBC_REPO), "remote", "get-url", "origin"],
                       capture_output=True, text=True)
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", r.stdout.strip())
    return m.group(1) if m else None


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "posix-tracker"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _assets(repo: str, tag: str) -> dict[str, dict[str, Any]]:
    """{asset name: asset} of the release `tag`."""
    release = cast("dict[str, Any]", json.loads(_get(f"{API}/repos/{repo}/releases/tags/{tag}")))
    assets = cast("list[dict[str, Any]]", release.get("assets", []))
    return {str(a.get("name")): a for a in assets}


def _expected_sha256(sums: str, filename: str) -> str | None:
    for line in sums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == filename:
            return parts[0].lower()
    return None


def _cached(tag: str) -> Path | None:
    found = sorted((PREBUILT_DIR / tag).glob("*.a"))
    return found[0] if found else None


def fetch_library(version: str) -> Path | None:
    """The released static library of `version` for this machine, or None
    (dev, no release, other architecture, offline, checksum mismatch)."""
    if version == DEV_NAME:
        return None
    tag = f"v{version}"
    cached = _cached(tag)
    if cached:
        return cached

    arch = ARCHES.get(platform.machine().lower())
    repo = _github_repo()
    if arch is None or repo is None:
        return None
    try:
        assets = _assets(repo, tag)
        suffix = f"-{version}-linux-{arch}.tar.gz"
        name = next((n for n in assets if n.endswith(suffix)), None)
        if name is None or "SHA256SUMS" not in assets:
            print(f"  [prebuilt] {tag}: no {arch} build in the release")
            return None
        sums = _get(str(assets["SHA256SUMS"]["browser_download_url"])).decode()
        archive = _get(str(assets[name]["browser_download_url"]))
    except urllib.error.HTTPError as err:
        print(f"  [prebuilt] {tag}: " + ("no GitHub release" if err.code == 404 else f"unavailable ({err})"))
        return None
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"  [prebuilt] {tag}: unavailable ({err})")
        return None

    actual = hashlib.sha256(archive).hexdigest()
    expected = _expected_sha256(sums, name)
    digest = str(assets[name].get("digest") or "")  # "sha256:…" when GitHub provides it
    if actual != expected or (digest.startswith("sha256:") and digest[7:] != actual):
        print(f"  [prebuilt] {tag}: checksum mismatch for {name}, refused")
        return None

    dest = PREBUILT_DIR / tag
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        libraries = [m for m in tar.getmembers() if m.isfile() and re.search(r"/lib/[^/]+\.a$", m.name)]
        for member in libraries:
            source = tar.extractfile(member)
            if source is not None:
                (dest / Path(member.name).name).write_bytes(source.read())
    (dest / "SOURCE").write_text(f"{name}\nsha256 {actual}\n")
    print(f"  [prebuilt] {tag}: using {name} (sha256 checked)")
    return _cached(tag)
