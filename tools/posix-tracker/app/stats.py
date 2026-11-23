"""Progress of each release against the POSIX reference (weighted per category)."""
from __future__ import annotations

from app.model import Bucket, HeaderStats, ReleaseStats, ScanResult, Stats, SymbolInfo, empty_bucket
from app.posix_ref import POSIX_BY_HEADER, POSIX_HEADERS
from app.sources import version_key
from config import CATEGORIES, WEIGHTS


def _tally(buckets: dict[str, Bucket], categories: dict[str, dict[str, SymbolInfo]], defined: set[str]) -> None:
    """Add the symbols of `categories` to `buckets`, split into implemented / missing."""
    for category, symbols in categories.items():
        bucket = buckets.get(category)
        if bucket is None:
            continue
        for name, info in symbols.items():
            bucket["total"] += 1
            if name in defined:
                bucket["done"] += 1
                bucket["implemented"][name] = info
            else:
                bucket["missing"][name] = info


def _weighted_percent(buckets: dict[str, Bucket]) -> float:
    """percent = Σ(done × weight) / Σ(total × weight) × 100"""
    done = sum(b["done"] * WEIGHTS.get(c, 1.0) for c, b in buckets.items())
    total = sum(b["total"] * WEIGHTS.get(c, 1.0) for c, b in buckets.items())
    return 100.0 * done / total if total else 0.0


def _per_header(defined: set[str], headers_present: set[str]) -> dict[str, HeaderStats]:
    out: dict[str, HeaderStats] = {}
    for header, categories in POSIX_BY_HEADER.items():
        buckets = {c: empty_bucket() for c in CATEGORIES}
        _tally(buckets, categories, defined)
        out[header] = {
            "present": header in headers_present,
            "percent": _weighted_percent(buckets),
            "url": POSIX_HEADERS[header]["url"] if header in POSIX_HEADERS else "",
            "categories": buckets,
        }
    return out


def compute_release_stats(scan: ScanResult) -> ReleaseStats:
    defined = set(scan["defined"])
    totals = {c: empty_bucket() for c in CATEGORIES}
    for categories in POSIX_BY_HEADER.values():
        _tally(totals, categories, defined)
    return {
        "percent": _weighted_percent(totals),
        "totals": totals,
        "per_header": _per_header(defined, set(scan["headers_present"])),
    }


def compute_all_stats(scans: dict[str, ScanResult]) -> Stats:
    versions = sorted(scans, key=version_key)
    return {
        "versions": versions,
        "releases": {v: compute_release_stats(scans[v]) for v in versions},
        "libraries": {v: scans[v]["library"] for v in versions},
    }
