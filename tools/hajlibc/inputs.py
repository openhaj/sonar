"""Read what the pages are generated from: the git repository, blåsix's
results, the coverage report and the POSIX tracker's summary.

External JSON is checked here, field by field; everything after is typed.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from .model import (
    CoverageReport, FileCoverage, HeaderConformance, LineCounts, PosixSummary, RepoInfo,
    TestRecord, TestReport, Unavailable,
)

# ----- helpers -----


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _newest(base: Path, pattern: str) -> Path | None:
    """The most recently written file matching `pattern` under `base`."""
    found = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime) if base.exists() else []
    return found[-1] if found else None


def _mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")


def _objects(value: Any) -> list[dict[str, Any]]:
    """The JSON objects of a JSON array (anything else is dropped)."""
    if not isinstance(value, list):
        return []
    return [cast("dict[str, Any]", v) for v in cast("list[Any]", value) if isinstance(v, dict)]


def _str(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    return value if isinstance(value, str) else ""


def _int(obj: dict[str, Any], key: str) -> int:
    value = obj.get(key)
    return value if isinstance(value, int) else 0


def _float(obj: dict[str, Any], key: str) -> float:
    value = obj.get(key)
    return float(value) if isinstance(value, (int, float)) else 0.0


# ----- repository -----


def repo_info(repo: Path) -> RepoInfo:
    tags = [t for t in _git(repo, "tag", "--list", "v*", "--sort=-v:refname").splitlines() if t]
    latest = tags[0] if tags else None
    url = _git(repo, "remote", "get-url", "origin")
    url = re.sub(r"^git@github\.com:", "https://github.com/", url).removesuffix(".git")
    src = repo / "src"
    return {
        "url": url,
        "commit": _git(repo, "rev-parse", "HEAD"),
        "commit_short": _git(repo, "rev-parse", "--short", "HEAD"),
        "commit_date": _git(repo, "log", "-1", "--format=%cI"),
        "commit_subject": _git(repo, "log", "-1", "--format=%s"),
        "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "latest_release": latest,
        "latest_release_date": _git(repo, "log", "-1", "--format=%cI", latest) if latest else None,
        "releases": len(tags),
        "commits": int(_git(repo, "rev-list", "--count", "HEAD") or 0),
        "sources": {
            "c": sum(1 for _ in src.rglob("*.c")),
            "asm": sum(1 for _ in src.rglob("*.S")),
            "headers": sum(1 for _ in (repo / "include").rglob("*.h")),
        },
    }


# ----- tests -----

PRESENT_PROBES = ("ok", "present", "pass")


def _conformance(interfaces: list[dict[str, Any]], tests: list[TestRecord]) -> dict[str, HeaderConformance]:
    """Per header: required interfaces, which are present (declared and
    linked), which have tests, and which pass all of them."""
    statuses: dict[str, list[str]] = defaultdict(list)
    for t in tests:
        statuses[t["function"]].append(t["status"])

    headers: dict[str, HeaderConformance] = {}
    for interface in interfaces:
        h = headers.setdefault(_str(interface, "header"), {"required": 0, "present": 0, "tested": 0, "verified": 0})
        h["required"] += 1
        if interface.get("probe") in PRESENT_PROBES:
            h["present"] += 1
        results = statuses.get(_str(interface, "name"))
        if results:
            h["tested"] += 1
            if all(s == "pass" for s in results):
                h["verified"] += 1
    return dict(sorted(headers.items()))


def load_tests(base: Path) -> TestReport | None:
    """blåsix's results.json of the most recent run under `base`."""
    path = _newest(base, "*/results.json")
    if path is None:
        return None
    data: dict[str, Any] = json.loads(path.read_text())

    tests: list[TestRecord] = [
        {"category": _str(t, "category"), "function": _str(t, "function"), "test": _str(t, "test"),
         "status": _str(t, "status"), "checks": _int(t, "checks"), "ms": _float(t, "ms")}
        for t in _objects(data.get("tests"))
    ]
    unavailable: list[Unavailable] = [
        {"category": _str(u, "category"), "function": _str(u, "function")}
        for u in _objects(data.get("unavailable"))
    ]
    interfaces = _objects(data.get("interfaces"))

    raw_summary = data.get("summary")
    summary: dict[str, int] = {}
    if isinstance(raw_summary, dict):
        for key, value in cast("dict[str, Any]", raw_summary).items():
            if isinstance(value, int):
                summary[key] = value
    # blåsix's summary does not count the units that did not build
    summary["unavailable"] = max(summary.get("unavailable", 0), len(unavailable))

    return {
        "summary": {
            "target": _str(data, "target"),
            "libc": _str(data, "libc"),
            "generated": _mtime(path),
            "summary": summary,
            "total": len(tests),
            "checks": sum(t["checks"] for t in tests),
            "functions": len({t["function"] for t in tests}),
            "interfaces": len(interfaces),
            "probes": dict(Counter(_str(i, "probe") or "unprobed" for i in interfaces)),
            "headers": _conformance(interfaces, tests),
        },
        "tests": tests,
        "unavailable": unavailable,
    }


# ----- coverage -----


def _counts(lines: int, hit: int) -> LineCounts:
    return {"lines": lines, "hit": hit, "percent": round(100 * hit / lines, 2) if lines else 0.0}


def load_coverage(base: Path) -> CoverageReport | None:
    """blåsix's per-file line coverage (lines.tsv: file, percent, lines)."""
    path = _newest(base, "*/coverage/lines.tsv")
    if path is None:
        return None
    files: list[FileCoverage] = []
    for row in path.read_text().splitlines():
        cells = row.split("\t")
        if len(cells) != 3:
            continue
        name, percent, lines = cells[0], float(cells[1]), int(cells[2])
        files.append({"file": name, "lines": lines, "hit": round(percent * lines / 100), "percent": percent})
    files.sort(key=lambda f: f["file"])

    per_dir: dict[str, tuple[int, int]] = {}
    for f in files:
        top = f["file"].split("/")[0]
        lines, hit = per_dir.get(top, (0, 0))
        per_dir[top] = (lines + f["lines"], hit + f["hit"])

    total = _counts(sum(f["lines"] for f in files), sum(f["hit"] for f in files))
    return {
        "summary": {
            "generated": _mtime(path),
            "lines": total["lines"],
            "hit": total["hit"],
            "percent": total["percent"],
            "dirs": {d: _counts(lines, hit) for d, (lines, hit) in sorted(per_dir.items())},
        },
        "files": files,
    }


# ----- POSIX tracker -----


def load_posix(directory: Path) -> PosixSummary | None:
    """The tracker's summary.json (written by tools/posix-tracker, same shape)."""
    path = directory / "summary.json"
    if not path.exists():
        return None
    summary: PosixSummary = json.loads(path.read_text())
    return summary
