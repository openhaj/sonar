"""Machine-readable summary of the tracker, for other pages to consume.

Written to OUTPUT_DIR/summary.json by `run.py build`; read by the site's
tools/hajlibc/pages.py (same shape as PosixSummary there).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TypedDict

from app.model import ReleaseStats, Stats
from app.sources import commit_of
from config import CATEGORIES, CATEGORY_LABELS, OUTPUT_DIR, WEIGHTS


class Counts(TypedDict):
    done: int
    total: int


class HeaderCounts(TypedDict):
    total: int
    present: int
    complete: int


class VersionSummary(TypedDict):
    name: str
    commit: str | None
    library: str  # where its functions were read from: local, release, partial, none
    percent: float
    totals: dict[str, Counts]
    headers: HeaderCounts


class Summary(TypedDict):
    generated: str
    weights: dict[str, float]
    categories: dict[str, str]
    versions: list[VersionSummary]


def _version(name: str, release: ReleaseStats, library: str) -> VersionSummary:
    headers = release["per_header"].values()
    return {
        "name": name,
        "commit": commit_of(name),
        "library": library,
        "percent": round(release["percent"], 2),
        "totals": {c: {"done": release["totals"][c]["done"], "total": release["totals"][c]["total"]}
                   for c in CATEGORIES},
        "headers": {
            "total": len(headers),
            "present": sum(1 for h in headers if h["present"]),
            "complete": sum(1 for h in headers if h["percent"] >= 99.999),
        },
    }


def export(stats: Stats) -> None:
    summary: Summary = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "weights": WEIGHTS,
        "categories": {c: CATEGORY_LABELS.get(c, c) for c in CATEGORIES},
        "versions": [_version(v, stats["releases"][v], stats["libraries"].get(v, "none")) for v in stats["versions"]],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
