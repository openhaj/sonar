"""Populate data/sources/ from the libc's git repository.

Every release tag (v0.1.0, v0.2.0, ...) becomes data/sources/0.1.0/, and the
repository's current HEAD becomes data/sources/dev/. Each tree is a clean
`git archive` of that commit; the commit id is stored in SOURCE_MARK so an
unchanged release is never extracted (nor rescanned) twice.
"""
from __future__ import annotations

import io
import shutil
import subprocess
import tarfile

from config import HAJLIBC_REPO, SOURCES_DIR, TAG_PATTERN, DEV_NAME

SOURCE_MARK = ".source-commit"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(HAJLIBC_REPO), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def version_key(name: str) -> tuple[int, tuple[tuple[int, str], ...]]:
    """Sort 0.2.0 < 0.10.0 < dev (numeric parts compare as numbers)."""
    if name == DEV_NAME:
        return (1, ())
    return (0, tuple((int(p), "") if p.isdigit() else (0, p) for p in name.split(".")))


def wanted_versions() -> dict[str, str]:
    """{version name: commit id} for every release tag plus HEAD."""
    out: dict[str, str] = {}
    for tag in _git("tag", "--list", TAG_PATTERN).splitlines():
        out[tag.lstrip("v")] = _git("rev-list", "-n", "1", tag)
    out[DEV_NAME] = _git("rev-parse", "HEAD")
    return dict(sorted(out.items(), key=lambda kv: version_key(kv[0])))


def commit_of(version: str) -> str | None:
    mark = SOURCES_DIR / version / SOURCE_MARK
    return mark.read_text().strip() if mark.is_file() else None


def _extract(version: str, commit: str) -> None:
    dest = SOURCES_DIR / version
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    data = subprocess.run(
        ["git", "-C", str(HAJLIBC_REPO), "archive", "--format=tar", commit],
        check=True, capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest, filter="data")
    (dest / SOURCE_MARK).write_text(commit + "\n")


def sync() -> dict[str, str]:
    if not (HAJLIBC_REPO / ".git").exists():
        raise SystemExit(f"!! libc repository not found: {HAJLIBC_REPO} "
                         "(git submodule update --init)")
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    wanted = wanted_versions()

    for d in SOURCES_DIR.iterdir():
        if d.is_dir() and d.name not in wanted:
            print(f"  [sources] {d.name}: removed (no such tag any more)")
            shutil.rmtree(d)

    for version, commit in wanted.items():
        if commit_of(version) == commit:
            print(f"  [sources] {version}: up to date ({commit[:9]})")
        else:
            print(f"  [sources] {version}: extracting {commit[:9]}")
            _extract(version, commit)
    return wanted
