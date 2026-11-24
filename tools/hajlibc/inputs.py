"""Read what the pages are generated from: the git repositories, blåsix's
results, its lcov tracefile and the POSIX tracker's summary.

External JSON is checked here, field by field; everything after is typed.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, cast

from . import lcov
from .model import (
    CategoryCoverage, CoverageReport, FileCoverage, FunctionCoverage, HeaderRow, Interface, Leak,
    PosixSummary, Ratio, RepoInfo, TestRecord, TestReport, UnitFailure,
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

# Statuses of a test that count as a failure (blåsix: statusFailed()).
FAILED = ("fail", "crash", "timeout", "error")
VERDICTS = ("verified", "failing", "missing", "broken", "unbuilt", "untested")


def slug(name: str) -> str:
    """sys/mman.h -> sys-mman-h"""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _group(unit: str) -> str:
    """ctype/classify/isalnum -> classify; ctype/defs -> ""."""
    parts = unit.split("/")
    return "/".join(parts[1:-1])


def _test(t: dict[str, Any]) -> TestRecord:
    return {
        "category": _str(t, "category"), "function": _str(t, "function"), "test": _str(t, "test"),
        "unit": _str(t, "unit"), "file": _str(t, "file"), "line": _int(t, "line"),
        "status": _str(t, "status"), "checks": _int(t, "checks"), "failed": _int(t, "failed"),
        "ms": _float(t, "ms"), "signal": _int(t, "signal"), "exit": _int(t, "exit"),
        "messages": _str(t, "messages"), "output": _str(t, "output"),
        "spec_ref": _str(t, "spec_ref"), "since": _str(t, "since"), "until": _str(t, "until"),
    }


def _interface(i: dict[str, Any]) -> Interface:
    built = i.get("built")
    unit = _str(i, "unit")
    return {
        "header": _str(i, "header"), "category": _str(i, "category"), "name": _str(i, "name"),
        "kind": _str(i, "kind"), "since": _str(i, "since"), "option": _str(i, "option"),
        "requirement": _str(i, "requirement"), "obsolescent": i.get("obsolescent") is True,
        "probe": _str(i, "probe"), "unit": unit, "group": _group(unit) if unit else "",
        "built": built if isinstance(built, bool) else None,
        "tests": _int(i, "tests"), "passed": _int(i, "passed"), "failed": _int(i, "failed"),
        "skipped": _int(i, "skipped"), "unimplemented": _int(i, "unimplemented"),
        "verdict": _str(i, "verdict"),
    }


def _header_row(c: dict[str, Any], interfaces: list[Interface]) -> HeaderRow:
    header = _str(c, "header")
    return {
        "header": header, "slug": slug(header), "category": _str(c, "category"),
        "required": _int(c, "required"), "option": _int(c, "option"), "obsolescent": _int(c, "obsolescent"),
        "present": _int(c, "present"), "undeclared": _int(c, "undeclared"), "unlinked": _int(c, "unlinked"),
        "broken": _int(c, "broken"), "unprobed": _int(c, "unprobed"), "tested": _int(c, "tested"),
        "verified": _int(c, "verified"), "failing": _int(c, "failing"),
        "missing": sum(1 for i in interfaces if i["header"] == header and i["verdict"] == "missing"),
        "unbuilt": _int(c, "unbuilt"), "untested": _int(c, "untested"),
        "leaked": _int(c, "leaked"), "nodiag": _int(c, "nodiag"),
    }


def _check_consistency(rows: list[HeaderRow], interfaces: list[Interface], warn: Callable[[str], None]) -> None:
    """blåsix's table and its verdicts must agree: report it if they do not."""
    for row in rows:
        verdicts = Counter(i["verdict"] for i in interfaces if i["header"] == row["header"])
        for key in ("verified", "failing", "unbuilt", "untested"):
            if verdicts[key] != row[key]:
                warn(f"{row['header']}: blåsix says {row[key]} {key}, its interfaces {verdicts[key]}")
        if sum(verdicts.values()) != row["required"]:
            warn(f"{row['header']}: {row['required']} required, {sum(verdicts.values())} interfaces listed")


def load_tests(base: Path, warn: Callable[[str], None]) -> TestReport | None:
    """blåsix's results.json of the most recent run under `base`.

    Verdicts and the conformance table are blåsix's own (results.json
    "interfaces" and "conformance"): nothing is recomputed here.
    """
    path = _newest(base, "*/results.json")
    if path is None:
        return None
    data: dict[str, Any] = json.loads(path.read_text())
    if "conformance" not in data or "verdict" not in next(iter(_objects(data.get("interfaces"))), {"verdict": ""}):
        warn(f"{path}: written by an older blåsix (no verdicts): run the tests again")
        return None

    tests = [_test(t) for t in _objects(data.get("tests"))]
    unavailable: list[UnitFailure] = [
        {"category": _str(u, "category"), "function": _str(u, "function"), "unit": _str(u, "unit"),
         "reason": _str(u, "reason") or "build", "error": _str(u, "error"), "log": _str(u, "log")}
        for u in _objects(data.get("unavailable"))
    ]
    interfaces = [_interface(i) for i in _objects(data.get("interfaces"))]
    rows = [_header_row(c, interfaces) for c in _objects(data.get("conformance"))]
    _check_consistency(rows, interfaces, warn)
    leaks: list[Leak] = [{"header": _str(h, "header"), "name": _str(h, "name")}
                         for h in _objects(data.get("hidden")) if h.get("leaked") is True]

    summary: dict[str, int] = {}
    raw_summary = data.get("summary")
    if isinstance(raw_summary, dict):
        for key, value in cast("dict[str, Any]", raw_summary).items():
            if isinstance(value, int):
                summary[key] = value
    summary["unavailable"] = len(unavailable)   # units, not tests: blåsix counts none
    verdicts = Counter(i["verdict"] for i in interfaces)

    return {
        "summary": {
            "target": _str(data, "target"),
            "libc": _str(data, "libc"),
            "mode": _str(data, "mode"),
            "generated": _mtime(path),
            "summary": summary,
            "total": len(tests),
            "checks": sum(t["checks"] for t in tests),
            "functions": sum(1 for i in interfaces if i["tests"]),
            "interfaces": len(interfaces),
            "verdicts": {v: verdicts.get(v, 0) for v in VERDICTS},
            "headers": [{"header": r["header"], "slug": r["slug"], "required": r["required"],
                         "present": r["present"], "verified": r["verified"], "failing": r["failing"],
                         "missing": r["missing"], "untested": r["untested"], "unbuilt": r["unbuilt"]}
                        for r in rows],
        },
        "tests": tests,
        "unavailable": unavailable,
        "interfaces": interfaces,
        "conformance": rows,
        "leaks": leaks,
    }


# ----- coverage -----


def ratio(found: int, hit: int) -> Ratio:
    return {"found": found, "hit": hit, "percent": round(100 * hit / found, 2) if found else 0.0}


def _sum(ratios: list[Ratio]) -> Ratio:
    return ratio(sum(r["found"] for r in ratios), sum(r["hit"] for r in ratios))


def _category(path: str) -> str:
    """src/string/mem/memchr.c -> string; include/... -> include."""
    parts = path.split("/")
    if parts[0] == "src" and len(parts) > 2:
        return parts[1]
    return parts[0] if len(parts) > 1 else "."


def _file_coverage(path: str, rec: lcov.SourceRecord) -> FileCoverage:
    branch_hits: dict[int, list[int | None]] = defaultdict(list)
    for (line, _block, _branch), taken in sorted(rec.branches.items()):
        branch_hits[line].append(taken)
    functions: list[FunctionCoverage] = sorted(
        ({"name": name, "line": line, "calls": calls} for name, (line, calls) in rec.functions.items()),
        key=lambda f: (f["line"], f["name"]))
    return {
        "path": path,
        "category": _category(path),
        "lines": ratio(len(rec.lines), sum(1 for h in rec.lines.values() if h > 0)),
        "functions": ratio(len(functions), sum(1 for f in functions if f["calls"] > 0)),
        "branches": ratio(len(rec.branches), sum(1 for t in rec.branches.values() if t)),
        "hits": dict(sorted(rec.lines.items())),
        "branch_hits": dict(branch_hits),
        "function_list": functions,
    }


def load_coverage(base: Path, repo: Path, warn: Callable[[str], None]) -> CoverageReport | None:
    """The lcov tracefile of blåsix's coverage run (coverage/lcov.info): every
    file compiled into the library, run by the tests or not."""
    path = _newest(base, "*/coverage/lcov.info")
    if path is None:
        if _newest(base, "*/coverage/lines.tsv"):
            warn(f"{base}: coverage written by an older blåsix (no lcov.info): run the tests again")
        return None
    root = repo.resolve()
    files: list[FileCoverage] = []
    for sf, rec in lcov.parse(path).items():
        source = Path(sf)
        if not source.is_relative_to(root):
            warn(f"{path.name}: {sf} is not in {root}: left out")
            continue
        files.append(_file_coverage(source.relative_to(root).as_posix(), rec))
    files.sort(key=lambda f: f["path"])

    by_category: dict[str, list[FileCoverage]] = defaultdict(list)
    for f in files:
        by_category[f["category"]].append(f)
    categories: list[CategoryCoverage] = [
        {"name": name, "slug": slug(name), "files": len(group),
         "lines": _sum([f["lines"] for f in group]),
         "functions": _sum([f["functions"] for f in group]),
         "branches": _sum([f["branches"] for f in group])}
        for name, group in sorted(by_category.items(), key=lambda kv: (kv[0] == "include", kv[0]))
    ]
    return {
        "summary": {
            "generated": _mtime(path),
            "files": len(files),
            "lines": _sum([f["lines"] for f in files]),
            "functions": _sum([f["functions"] for f in files]),
            "branches": _sum([f["branches"] for f in files]),
            "categories": categories,
        },
        "files": files,
        "tracefile": str(path),
    }


# ----- POSIX tracker -----


def load_posix(directory: Path) -> PosixSummary | None:
    """The tracker's summary.json (written by tools/posix-tracker, same shape)."""
    path = directory / "summary.json"
    if not path.exists():
        return None
    summary: PosixSummary = json.loads(path.read_text())
    return summary
