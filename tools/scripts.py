"""TypeScript build without Node.js.

The two tools used are native binaries, published on the npm registry as
per-platform packages:

    tsc      TypeScript 7 (Go)   @typescript/typescript-<platform>   type-checking
    esbuild  esbuild (Go)        @esbuild/<platform>                 bundling

They are downloaded once into .build/toolchain/ (exact versions below, each
tarball checked against the registry's sha512 integrity), then run directly.

    check(root)            tsc -p tsconfig.json (type errors fail the build)
    bundle(entries, out)   one minified IIFE bundle (+ source map) per entry
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import platform
import subprocess
import sys
import tarfile
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

Log = Callable[[str], None]

REGISTRY = "https://registry.npmjs.org"


@dataclass(frozen=True)
class Tool:
    name: str
    package: str      # npm package, {platform} is replaced
    version: str
    binary: str       # path of the executable inside the package


TSC = Tool("tsc", "@typescript/typescript-{platform}", "7.0.2", "lib/tsc")
ESBUILD = Tool("esbuild", "@esbuild/{platform}", "0.28.2", "bin/esbuild")

TARGET = "es2020"


# ------------------------------------------------------------- installation

def npm_platform() -> str:
    """This machine as npm names it: linux-x64, darwin-arm64, win32-x64, ..."""
    os_name = {"linux": "linux", "darwin": "darwin", "win32": "win32"}.get(sys.platform)
    arch = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine().lower())
    if not os_name or not arch:
        raise SystemExit(f"scripts: no prebuilt tsc/esbuild for {sys.platform}/{platform.machine()}")
    return f"{os_name}-{arch}"


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def _verify(data: bytes, integrity: str, what: str) -> None:
    algo, _, expected = integrity.partition("-")
    if algo != "sha512":
        raise SystemExit(f"scripts: unexpected integrity format for {what}: {integrity}")
    actual = base64.b64encode(hashlib.sha512(data).digest()).decode()
    if actual != expected:
        raise SystemExit(f"scripts: checksum mismatch for {what}, download refused")


def install(tool: Tool, cache: Path, log: Log) -> Path:
    """Path of the tool's executable, downloading it on first use."""
    package = tool.package.format(platform=npm_platform())
    home = cache / f"{package.replace('/', '__')}@{tool.version}"
    exe = home / tool.binary
    if exe.exists():
        return exe

    log(f"downloading {package}@{tool.version}")
    meta: dict[str, Any] = json.loads(_fetch(f"{REGISTRY}/{package}/{tool.version}"))
    tarball = _fetch(meta["dist"]["tarball"])
    _verify(tarball, meta["dist"]["integrity"], f"{package}@{tool.version}")

    tmp = home.with_name(home.name + ".tmp")
    with tarfile.open(fileobj=io.BytesIO(tarball)) as tar:
        # npm tarballs hold everything under package/
        members = [m for m in tar.getmembers() if m.name.startswith("package/")]
        for m in members:
            m.name = m.name.removeprefix("package/")
        tar.extractall(tmp, members=members, filter="data")
    (tmp / tool.binary).chmod(0o755)
    tmp.rename(home)
    return exe


# ----- commands -----

def check(root: Path, cache: Path, log: Log) -> bool:
    """Type-check the project (tsconfig.json). Returns False on type errors."""
    tsc = install(TSC, cache, log)
    return subprocess.run([str(tsc), "-p", str(root / "tsconfig.json")], cwd=root).returncode == 0


def bundle(entries: list[Path], out: Path, cache: Path, log: Log) -> bool:
    """One minified bundle (with source map) per entry, named after it."""
    esbuild = install(ESBUILD, cache, log)
    cmd = [str(esbuild), *map(str, entries), "--bundle", "--format=iife", f"--target={TARGET}",
           "--minify", "--sourcemap", f"--outdir={out}", "--log-level=warning"]
    return subprocess.run(cmd).returncode == 0
