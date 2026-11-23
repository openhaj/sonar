from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, TypedDict, cast

from app.model import ScanResult

from config import CACHE_DIR, SOURCES_DIR

CACHE_VERSION = 1

def _hash_dir(root: Path) -> str:
    h = hashlib.sha256()
    if not root.exists():
        return h.hexdigest()

    entries: list[tuple[str, int, int]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix == ".hajscan":
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        rel = p.relative_to(root).as_posix()
        entries.append((rel, st.st_size, int(st.st_mtime)))

    for rel, size, mtime in entries:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(str(size).encode("ascii"))
        h.update(b"\0")
        h.update(str(mtime).encode("ascii"))
        h.update(b"\0")

    return h.hexdigest()

def _cache_path(version: str) -> Path:
    return CACHE_DIR / f"{version}.json"

def _load_cache(version: str) -> dict[str, Any] | None:
    p = _cache_path(version)
    if not p.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(p.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("cache_version") != CACHE_VERSION:
        return None
    if data.get("analyzer") != _analyzer_fingerprint():
        return None
    return data

def _save_cache(version: str, fingerprint: str, scan: ScanResult) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "cache_version": CACHE_VERSION,
        "version":       version,
        "fingerprint":   fingerprint,
        "analyzer":      _analyzer_fingerprint(),
        "scan":          scan,
    }
    _cache_path(version).write_text(
        json.dumps(payload, indent=2), "utf-8")

def clear_cache(version: str | None = None) -> None:
    clear_file_cache(version)
    if version is None:
        if CACHE_DIR.exists():
            for p in CACHE_DIR.glob("*.json"):
                p.unlink()
        return
    p = _cache_path(version)
    if p.exists():
        p.unlink()

def _fingerprint(root: Path) -> str:
    # Trees extracted by app/sources.py carry their commit id: that is the
    # identity of the release (build artifacts left by the scan don't count).
    mark = root / ".source-commit"
    if mark.is_file():
        return "commit:" + mark.read_text().strip()
    return _hash_dir(root)


def _as_scan(value: Any) -> ScanResult | None:
    """A ScanResult read back from JSON, or None if it does not look like one."""
    if not isinstance(value, dict):
        return None
    scan = cast("dict[str, Any]", value)
    version, defined, headers = scan.get("version"), scan.get("defined"), scan.get("headers_present")
    if not isinstance(version, str) or not isinstance(defined, list) or not isinstance(headers, list):
        return None
    library = scan.get("library")
    if library not in ("local", "release", "partial", "none"):
        return None  # scanned before this field existed: rescan
    return {
        "version": version,
        "defined": [n for n in cast("list[Any]", defined) if isinstance(n, str)],
        "headers_present": [h for h in cast("list[Any]", headers) if isinstance(h, str)],
        "library": library,
    }


def get_cached_scan(version: str) -> ScanResult | None:
    root = SOURCES_DIR / version
    if not root.exists():
        return None
    fp = _fingerprint(root)
    cached = _load_cache(version)
    if cached is None:
        return None
    if cached.get("fingerprint") != fp:
        return None
    return _as_scan(cached.get("scan"))

def put_cached_scan(version: str, scan: ScanResult) -> None:
    root = SOURCES_DIR / version
    fp = _fingerprint(root)
    _save_cache(version, fp, scan)


FILE_CACHE_DIR = CACHE_DIR / "files"
FILE_CACHE_VERSION = 1

_APP_DIR = Path(__file__).resolve().parent


def _analyzer_fingerprint() -> str:
    h = hashlib.sha256()
    for name in ("analyze.py", "cache.py", "prebuilt.py"):
        try:
            h.update((_APP_DIR / name).read_bytes())
        except OSError:
            pass
    return h.hexdigest()


class FileEntry(TypedDict):
    deps: dict[str, str]  # file -> sha256 (the file itself and what it includes)
    names: list[str]


class FileCache:
    def __init__(self, version: str) -> None:
        self.version = version
        self.root = (SOURCES_DIR / version).resolve()
        self.path = FILE_CACHE_DIR / f"{version}.json"
        self.analyzer = _analyzer_fingerprint()
        self._hashes: dict[Path, str | None] = {}
        self.entries: dict[str, FileEntry] = {}
        self.new_entries: dict[str, FileEntry] = {}
        self.hits = 0
        self.misses = 0
        self._load()

    # ----- persistance -----

    def _load(self) -> None:
        try:
            data: dict[str, Any] = json.loads(self.path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if (data.get("cache_version") != FILE_CACHE_VERSION
                or data.get("analyzer") != self.analyzer):
            return
        files: dict[str, Any] = data.get("files") or {}
        for rel, entry in files.items():
            deps, names = entry.get("deps"), entry.get("names")
            if isinstance(deps, dict) and isinstance(names, list):
                # written by store() below: the shape is ours
                self.entries[rel] = {"deps": cast("dict[str, str]", deps), "names": cast("list[str]", names)}

    def save(self) -> None:
        """Écrit uniquement les entrées vues pendant ce scan (les fichiers
        supprimés disparaissent du cache)."""
        FILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "cache_version": FILE_CACHE_VERSION,
            "version":       self.version,
            "analyzer":      self.analyzer,
            "files":         self.new_entries,
        }
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload), "utf-8")
        tmp.replace(self.path)

    # ----- fingerprints ---

    def _key(self, p: Path) -> str:
        p = p.resolve()
        try:
            return p.relative_to(self.root).as_posix()
        except ValueError:
            return str(p)

    def _abs(self, key: str) -> Path:
        p = Path(key)
        return p if p.is_absolute() else self.root / p

    def file_hash(self, p: Path) -> str | None:
        p = p.resolve()
        if p not in self._hashes:
            try:
                self._hashes[p] = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                self._hashes[p] = None
        return self._hashes[p]

    # ----- API -----

    def lookup(self, path: Path) -> list[str] | None:
        rel = self._key(path)
        entry = self.entries.get(rel)
        if entry is None:
            self.misses += 1
            return None
        deps = entry["deps"]
        if not deps or any(self.file_hash(self._abs(key)) != sha for key, sha in deps.items()):
            self.misses += 1
            return None
        self.hits += 1
        self.new_entries[rel] = entry
        return list(entry["names"])

    def store(self, path: Path, deps: set[Path], names: set[str]) -> None:
        dep_hashes: dict[str, str] = {}
        for d in deps | {path}:
            sha = self.file_hash(d)
            if sha is None:
                continue
            dep_hashes[self._key(d)] = sha
        self.new_entries[self._key(path)] = {
            "deps":  dep_hashes,
            "names": sorted(names),
        }


def clear_file_cache(version: str | None = None) -> None:
    if not FILE_CACHE_DIR.exists():
        return
    if version is None:
        for p in FILE_CACHE_DIR.glob("*.json"):
            p.unlink()
        return
    p = FILE_CACHE_DIR / f"{version}.json"
    if p.exists():
        p.unlink()
