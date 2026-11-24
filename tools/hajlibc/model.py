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


# ----- tests (blåsix's results.json, normal run) -----


class TestRecord(TypedDict):
    """One test and its result."""
    category: str
    function: str           # the interface it is attached to
    test: str
    unit: str               # <category>[/<group>...]/<function>, or <category>/defs
    file: str               # source of the test, relative to blåsix
    line: int
    status: str             # pass fail skip unimplemented crash timeout error
    checks: int
    failed: int             # failed checks
    ms: float
    signal: int
    exit: int
    messages: str           # failed checks, skip / not implemented reason, logs
    output: str             # captured stdout + stderr
    spec_ref: str
    since: str
    until: str


class UnitFailure(TypedDict):
    """A test unit that did not build against the libc."""
    category: str
    function: str
    unit: str
    reason: str             # "unimplemented" (its interface is missing) or "build"
    error: str              # the error lines of the build log
    log: str                # the build log (start)


class Interface(TypedDict):
    """A required interface of the target, as blåsix judges it."""
    header: str
    category: str
    name: str
    kind: str               # function macro type either var
    since: str
    option: str             # option group when only required by one
    requirement: str
    obsolescent: bool
    probe: str              # present undeclared unlinked broken unprobed
    unit: str               # the unit that tests it ("" when none)
    group: str              # its folder in the suites ("" for <category>/defs or none)
    built: bool | None      # did its unit build (None: no unit)
    tests: int
    passed: int
    failed: int
    skipped: int
    unimplemented: int
    verdict: str            # missing broken failing verified unbuilt untested


class HeaderRow(TypedDict):
    """blåsix's conformance table, one row per header."""
    header: str
    slug: str
    category: str
    required: int
    option: int
    obsolescent: int
    present: int
    undeclared: int
    unlinked: int
    broken: int
    unprobed: int
    tested: int
    verified: int
    failing: int
    missing: int            # interfaces whose verdict is "missing" (not implemented)
    unbuilt: int
    untested: int
    leaked: int
    nodiag: int


class Leak(TypedDict):
    header: str
    name: str


class HeaderSummary(TypedDict):
    """One header, as written to data.js."""
    header: str
    slug: str
    required: int
    present: int
    verified: int
    failing: int
    missing: int
    untested: int
    unbuilt: int


class TestSummary(TypedDict):
    """Tests, as written to data.js."""
    target: str
    libc: str
    mode: str
    generated: str
    summary: dict[str, int]         # tests per status
    total: int
    checks: int
    functions: int                  # interfaces with at least one test
    interfaces: int                 # required by the target
    verdicts: dict[str, int]        # interfaces per verdict
    headers: list[HeaderSummary]


class TestReport(TypedDict):
    summary: TestSummary
    tests: list[TestRecord]
    unavailable: list[UnitFailure]
    interfaces: list[Interface]
    conformance: list[HeaderRow]
    leaks: list[Leak]


# ----- coverage (lcov tracefile of blåsix's coverage run) -----


class Ratio(TypedDict):
    found: int
    hit: int
    percent: float


class FunctionCoverage(TypedDict):
    name: str
    line: int
    calls: int


class FileCoverage(TypedDict):
    """One source file compiled into the library."""
    path: str                       # relative to the hajlibc repository
    category: str                   # src/<category>/..., or "include"
    lines: Ratio
    functions: Ratio
    branches: Ratio
    hits: dict[int, int]            # executable line -> times run
    branch_hits: dict[int, list[int | None]]   # line -> each branch: taken (None: never reached)
    function_list: list[FunctionCoverage]


class CategoryCoverage(TypedDict):
    """A category, as written to data.js."""
    name: str
    slug: str
    files: int
    lines: Ratio
    functions: Ratio
    branches: Ratio


class CoverageSummary(TypedDict):
    """Coverage, as written to data.js."""
    generated: str
    files: int
    lines: Ratio
    functions: Ratio
    branches: Ratio
    categories: list[CategoryCoverage]


class CoverageReport(TypedDict):
    summary: CoverageSummary
    files: list[FileCoverage]
    tracefile: str                  # the lcov tracefile read


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
