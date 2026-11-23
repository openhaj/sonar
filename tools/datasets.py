"""Immutable data sets kept outside git.

A data set is a .tar.gz archive described by a small manifest committed in
the repository (TOML):

    name    = "posix-2024"
    sha256  = "…"                 # identity of the archive: never changes
    urls    = ["https://…", …]    # mirrors, tried in order

The archive is fetched once into .build/datasets/, checked against its
sha256 (a mismatch is refused) and extracted next to it. Changing the data
means publishing a new archive and updating the manifest, so a given commit
of the repository always builds with exactly the same data.

Before the archive is published (or offline), point the environment variable
named in the manifest's `env` at a local copy of the archive: it is checked
the same way.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import tarfile
import tomllib
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

Log = Callable[[str], None]


@dataclass(frozen=True)
class Dataset:
    name: str
    sha256: str
    urls: tuple[str, ...]
    env: str | None  # environment variable that may point to a local copy

    @property
    def archive_name(self) -> str:
        return f"{self.name}.tar.gz"


def load_manifest(path: Path) -> Dataset:
    raw: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    name, sha256, urls, env = raw.get("name"), raw.get("sha256"), raw.get("urls", []), raw.get("env")
    if not isinstance(name, str) or not isinstance(sha256, str) or len(sha256) != 64:
        raise SystemExit(f"{path}: needs a name and a 64-character sha256")
    if not isinstance(urls, list):
        raise SystemExit(f"{path}: urls must be a list")
    return Dataset(
        name=name,
        sha256=sha256.lower(),
        urls=tuple(u for u in cast("list[Any]", urls) if isinstance(u, str)),
        env=env if isinstance(env, str) else None,
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as response, dest.open("wb") as out:
        shutil.copyfileobj(response, out)


def _fetch_archive(ds: Dataset, archive: Path, log: Log) -> None:
    """Put a verified copy of the archive at `archive`."""
    archive.parent.mkdir(parents=True, exist_ok=True)
    tmp = archive.with_suffix(".part")
    local = os.environ.get(ds.env) if ds.env else None
    sources = ([local] if local else []) + list(ds.urls)  # local copy first, then mirrors
    if not sources:
        raise SystemExit(f"{ds.name}: no URL in the manifest" + (f" and {ds.env} is not set" if ds.env else ""))

    for origin in sources:
        log(f"fetching {ds.archive_name} from {origin}")
        try:
            if origin == local:
                shutil.copyfile(origin, tmp)
            else:
                _download(origin, tmp)
        except OSError as err:
            log(f"  failed: {err}")
            continue
        actual = _sha256(tmp)
        if actual == ds.sha256:
            tmp.replace(archive)
            return
        log(f"  refused: sha256 is {actual}, the manifest says {ds.sha256}")
    tmp.unlink(missing_ok=True)
    raise SystemExit(f"{ds.name}: could not get an archive matching the manifest")


def ensure(manifest: Path, cache: Path, log: Log) -> Path:
    """Directory holding the extracted data set (fetched and checked on first use)."""
    ds = load_manifest(manifest)
    tag = f"{ds.name}-{ds.sha256[:12]}"
    dest = cache / tag
    if (dest / ".complete").is_file():
        return dest

    archive = cache / "archives" / f"{tag}.tar.gz"
    if not (archive.is_file() and _sha256(archive) == ds.sha256):
        _fetch_archive(ds, archive, log)

    tmp = dest.with_name(dest.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    with tarfile.open(archive) as tar:
        tar.extractall(tmp, filter="data")
    (tmp / ".complete").write_text(ds.sha256 + "\n")
    shutil.rmtree(dest, ignore_errors=True)
    tmp.rename(dest)
    log(f"{ds.name}: extracted to {dest}")
    return dest


def make_archive(source: Path, out: Path) -> str:
    """Pack the files of `source` into a reproducible .tar.gz (same input, same
    bytes: sorted names, no timestamps or owners). Returns its sha256."""
    import gzip
    import io

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            info = tarfile.TarInfo(path.relative_to(source).as_posix())
            info.size = path.stat().st_size
            info.mode = 0o644
            info.mtime = 0
            with path.open("rb") as f:
                tar.addfile(info, f)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
        gz.write(buffer.getvalue())
    return _sha256(out)
