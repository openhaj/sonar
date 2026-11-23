"""Shapes of the hajlibc data. What goes into data.js matches the TypeScript
types of src/ts/hajlibc/types.ts."""
from __future__ import annotations

from typing import TypedDict

# ----- repository -----


class SourceCounts(TypedDict):
    c: int
    asm: int
    headers: int


class RepoInfo(TypedDict):
    url: str
    commit: str
    commit_short: str
    commit_date: str
    commit_subject: str
    branch: str
    latest_release: str | None
    latest_release_date: str | None
    releases: int
    commits: int
    sources: SourceCounts


# ----- tests -----


class TestRecord(TypedDict):
    """One blåsix test (results.json)."""
    category: str
    function: str
    test: str
    status: str
    checks: int
    ms: float


class Unavailable(TypedDict):
    """A test unit that did not build."""
    category: str
    function: str


class HeaderConformance(TypedDict):
    required: int
    present: int
    tested: int
    verified: int


class TestSummary(TypedDict):
    """Tests, as written to data.js."""
    target: str
    libc: str
    generated: str
    summary: dict[str, int]
    total: int
    checks: int
    functions: int
    interfaces: int
    probes: dict[str, int]
    headers: dict[str, HeaderConformance]


class TestReport(TypedDict):
    summary: TestSummary
    tests: list[TestRecord]
    unavailable: list[Unavailable]


# ----- coverage -----


class FileCoverage(TypedDict):
    file: str
    lines: int
    hit: int
    percent: float


class LineCounts(TypedDict):
    lines: int
    hit: int
    percent: float


class CoverageSummary(TypedDict):
    """Coverage, as written to data.js."""
    generated: str
    lines: int
    hit: int
    percent: float
    dirs: dict[str, LineCounts]


class CoverageReport(TypedDict):
    summary: CoverageSummary
    files: list[FileCoverage]


# ----- docs -----


class DocEntry(TypedDict):
    """One documented declaration of a header."""
    name: str
    decl: str
    brief: str
    text: str
    params: list[tuple[str, str]]
    returns: str
    notes: list[str]


class HeaderDoc(TypedDict):
    brief: str
    text: str
    notes: list[str]
    entries: list[DocEntry]


class DocsHeader(TypedDict):
    name: str
    slug: str
    brief: str
    count: int


class DocsSummary(TypedDict):
    """Docs, as written to data.js."""
    headers: list[DocsHeader]
    declarations: int


# ----- POSIX (tracker) -----


class Counts(TypedDict):
    done: int
    total: int


class HeaderCounts(TypedDict):
    total: int
    present: int
    complete: int


class PosixVersion(TypedDict):
    name: str
    commit: str | None
    percent: float
    totals: dict[str, Counts]
    headers: HeaderCounts


class PosixSummary(TypedDict):
    """The tracker's summary.json, passed through to data.js."""
    generated: str
    weights: dict[str, float]
    categories: dict[str, str]
    versions: list[PosixVersion]


# ----- output -----


class HajlibcData(TypedDict):
    """window.HAJLIBC_DATA (data.js). A section is None when its input is missing."""
    generated: str
    repo: RepoInfo
    posix: PosixSummary | None
    tests: TestSummary | None
    coverage: CoverageSummary | None
    docs: DocsSummary | None
