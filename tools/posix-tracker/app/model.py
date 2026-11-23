"""Shapes of the data passed between the tracker's stages.

    POSIX reference (data/posix/)  -> SymbolInfo, by name / by header
    scan of a release (analyze)    -> ScanResult
    statistics (stats)             -> Stats > ReleaseStats > HeaderStats > Bucket
"""
from __future__ import annotations

from typing import Literal, TypedDict

# Where the functions of a release were read from (`nm` on a static library):
# built here, the prebuilt library of its GitHub release, only the objects
# that compiled (incomplete), or nothing.
LibrarySource = Literal["local", "release", "partial", "none"]


class SymbolInfo(TypedDict):
    """One POSIX interface and its documentation (data/posix/)."""
    name: str
    category: str
    header: str
    url: str
    synopsis: str
    description: str
    return_value: str
    errors: list[str]
    examples: list[str]
    see_also: list[str]
    application_usage: str
    rationale: str
    future_directions: str
    change_history: str


class HeaderMeta(TypedDict):
    name: str
    url: str


class ScanResult(TypedDict):
    """What a release defines (functions, types, macros, ...) and which headers it has."""
    version: str
    defined: list[str]
    headers_present: list[str]
    library: LibrarySource


class Bucket(TypedDict):
    """Progress of one category: counts and the symbols on each side."""
    done: int
    total: int
    implemented: dict[str, SymbolInfo]
    missing: dict[str, SymbolInfo]


class HeaderStats(TypedDict):
    present: bool
    percent: float
    url: str
    categories: dict[str, Bucket]


class ReleaseStats(TypedDict):
    percent: float
    totals: dict[str, Bucket]
    per_header: dict[str, HeaderStats]


class Stats(TypedDict):
    versions: list[str]
    releases: dict[str, ReleaseStats]
    libraries: dict[str, LibrarySource]


def empty_bucket() -> Bucket:
    return {"done": 0, "total": 0, "implemented": {}, "missing": {}}
