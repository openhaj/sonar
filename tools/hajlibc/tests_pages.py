"""The tests pages: a recap (tests/index.html) and one page per header
(tests/<header>.html) with each interface, its tests and why they fail.

Everything shown is what blåsix says (results.json): its statuses, its
verdict on each interface and its conformance table. This module only
arranges it for src/templates/reports/tests*.html.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import TypedDict

from .inputs import FAILED
from .model import HeaderRow, Interface, Leak, RepoInfo, TestRecord, TestReport, TestSummary, UnitFailure
from .pages import Crumb, crumbs, short_date, source_url

# ----- vocabulary -----

STATUS_LABELS = {
    "pass": "pass", "fail": "fail", "crash": "crash", "timeout": "timeout", "error": "error",
    "skip": "skipped", "unimplemented": "not implemented",
}
STATUS_HELP = {
    "pass": "every check passed",
    "fail": "a check failed",
    "crash": "killed by a signal",
    "timeout": "killed after its time limit",
    "error": "the process ended inside the test",
    "skip": "could not run here (environment: no other locale installed, ...)",
    "unimplemented": "could not run: the libc lacks what it needs (setlocale(), ...)",
}
VERDICT_LABELS = {
    "verified": "verified", "failing": "failing", "missing": "not implemented",
    "broken": "link error", "unbuilt": "build error", "untested": "untested",
}
VERDICT_HELP = {
    "verified": "present, tests ran and every one passed",
    "failing": "a test failed",
    "missing": "the header does not declare it or the library does not define it",
    "broken": "declared, but its probe did not link (compiler crash, ...)",
    "unbuilt": "its tests did not build against the libc",
    "untested": "present, no test ran (none written yet, or all skipped)",
}
PROBE_LABELS = {
    "present": "declared and defined",
    "undeclared": "not declared by the header",
    "unlinked": "declared, not defined by the library",
    "broken": "declared, the link failed",
    "unprobed": "not probed",
}

# ----- view models -----


class Message(TypedDict):
    """One line of what a test reported."""
    kind: str           # check skip unimplemented log note
    text: str           # the whole line (kind note / log / skip ...)
    where: str          # file:line of a failed check
    href: str           # link to it
    check: str          # EXPECT_EQ(a, b)
    detail: str         # what was wrong: "2 == 3 is false"


class TestView(TypedDict):
    name: str
    anchor: str         # <interface>--<test>
    status: str
    label: str
    failed: bool
    checks: int
    failed_checks: int
    ms: float
    spec: str
    since: str
    until: str
    where: str
    href: str
    messages: list[Message]
    output: str
    signal: int


class InterfaceView(TypedDict):
    iface: Interface
    anchor: str
    verdict_label: str
    verdict_help: str
    probe_label: str
    tests: list[TestView]
    failure: UnitFailure | None     # its unit did not build
    unit_href: str


class GroupView(TypedDict):
    name: str
    anchor: str
    label: str
    interfaces: list[InterfaceView]
    counts: dict[str, int]          # interfaces per verdict


class Tile(TypedDict):
    key: str
    label: str
    value: int
    help: str


class FinderRow(TypedDict):
    name: str
    header: str
    kind: str
    verdict: str
    label: str
    tests: int
    passed: int
    failed: int
    href: str
    search: str


class FailureRow(TypedDict):
    interface: str
    test: str
    status: str
    label: str
    href: str
    summary: str


class TestsIndex(TypedDict):
    title: str
    crumbs: list[Crumb]
    run: TestSummary
    repo: RepoInfo
    blasix: RepoInfo
    date: str
    tiles: list[Tile]
    verdicts: list[Tile]
    headers: list[HeaderRow]
    finder: list[FinderRow]
    failures: list[FailureRow]
    unbuilt: dict[str, int]          # units that did not build: "unimplemented", "build"


class TestsHeader(TypedDict):
    title: str
    crumbs: list[Crumb]
    run: TestSummary
    row: HeaderRow
    groups: list[GroupView]
    verdicts: list[Tile]
    tiles: list[Tile]
    leaks: list[Leak]
    blasix: RepoInfo


# ----- messages -----

# "src/suites/string/copy/strcpy.c:33: EXPECT_MEMEQ(dst, "abc\0xxx", 8): differ at byte 4: 0x00 vs 0x78"
CHECK = re.compile(r"^(?P<file>[^\s:]+):(?P<line>\d+): (?P<rest>[A-Z][A-Z_]*\(.*)$")


def _split_check(rest: str) -> tuple[str, str]:
    """EXPECT_EQ(f(), 3): 2 == 3 is false -> ("EXPECT_EQ(f(), 3)", "2 == 3 is false"):
    the call ends at its closing parenthesis (quotes and nesting followed)."""
    depth, quote, i = 0, "", 0
    while i < len(rest):
        c = rest[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = ""
        elif c in "\"'":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return rest[:i + 1], rest[i + 1:].removeprefix(":").strip()
        i += 1
    return rest, ""


def _message(line: str, blasix: RepoInfo) -> Message:
    msg: Message = {"kind": "note", "text": line, "where": "", "href": "", "check": "", "detail": ""}
    m = CHECK.match(line)
    if m:
        check, detail = _split_check(m["rest"])
        msg.update(kind="check", where=f"{m['file']}:{m['line']}",
                   href=source_url(blasix, m["file"], int(m["line"])), check=check, detail=detail)
        return msg
    for prefix, kind in (("skipped: ", "skip"), ("not implemented: ", "unimplemented"), ("log: ", "log")):
        if line.startswith(prefix):
            msg.update(kind=kind, text=line.removeprefix(prefix))
            return msg
    return msg


def _test_view(t: TestRecord, blasix: RepoInfo) -> TestView:
    return {
        "name": t["test"], "anchor": f"{_anchor(t['function'])}--{_anchor(t['test'])}", "status": t["status"], "label": STATUS_LABELS.get(t["status"], t["status"]),
        "failed": t["status"] in FAILED, "checks": t["checks"], "failed_checks": t["failed"], "ms": t["ms"],
        "spec": t["spec_ref"], "since": t["since"], "until": t["until"],
        "where": f"{t['file']}:{t['line']}" if t["file"] else "",
        "href": source_url(blasix, t["file"], t["line"]),
        "messages": [_message(line, blasix) for line in t["messages"].splitlines() if line.strip()],
        "output": t["output"], "signal": t["signal"],
    }


# ----- pages -----

GROUP_DEFS = "Types and constants"
GROUP_NONE = "Without tests yet"


def _tiles(summary: dict[str, int]) -> list[Tile]:
    keys = ("pass", "fail", "crash", "timeout", "error", "skip", "unimplemented")
    return [{"key": k, "label": STATUS_LABELS[k], "value": summary.get(k, 0), "help": STATUS_HELP[k]}
            for k in keys if k in ("pass", "fail", "skip", "unimplemented") or summary.get(k, 0)]


def _verdict_tiles(verdicts: Counter[str] | dict[str, int]) -> list[Tile]:
    keys = ("verified", "failing", "missing", "broken", "unbuilt", "untested")
    return [{"key": k, "label": VERDICT_LABELS[k], "value": verdicts.get(k, 0), "help": VERDICT_HELP[k]}
            for k in keys if k in ("verified", "failing", "missing", "untested") or verdicts.get(k, 0)]


def _anchor(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", name)


def tests_index(report: TestReport, repo: RepoInfo, blasix: RepoInfo) -> TestsIndex:
    s = report["summary"]
    slugs = {r["header"]: r["slug"] for r in report["conformance"]}
    finder: list[FinderRow] = [
        {"name": i["name"], "header": i["header"], "kind": i["kind"], "verdict": i["verdict"],
         "label": VERDICT_LABELS.get(i["verdict"], i["verdict"]),
         "tests": i["tests"], "passed": i["passed"], "failed": i["failed"],
         "href": f"{slugs.get(i['header'], '')}.html#{_anchor(i['name'])}",
         "search": f"{i['name']} {i['header']} {i['kind']}".lower()}
        for i in sorted(report["interfaces"], key=lambda i: (i["name"], i["header"]))
    ]
    failures: list[FailureRow] = []
    for t in report["tests"]:
        if t["status"] not in FAILED:
            continue
        header = next((i["header"] for i in report["interfaces"]
                       if i["category"] == t["category"] and i["name"] == t["function"]), "")
        first = next((m for m in (_message(line, blasix) for line in t["messages"].splitlines()) if m["kind"] == "check"), None)
        failures.append({
            "interface": t["function"], "test": t["test"], "status": t["status"],
            "label": STATUS_LABELS.get(t["status"], t["status"]),
            "href": f"{slugs.get(header, '')}.html#{_anchor(t['function'])}--{_anchor(t['test'])}",
            "summary": (f"{first['check']}: {first['detail']}" if first else t["messages"].strip().split("\n")[0]),
        })
    return {
        "title": "Tests",
        "crumbs": crumbs(("../", "hajlibc")),
        "run": s, "repo": repo, "blasix": blasix, "date": short_date(s["generated"]),
        "tiles": _tiles(s["summary"]),
        "verdicts": _verdict_tiles(s["verdicts"]),
        "headers": report["conformance"],
        "finder": finder,
        "failures": failures,
        "unbuilt": {"unimplemented": sum(1 for u in report["unavailable"] if u["reason"] == "unimplemented"),
                    "build": sum(1 for u in report["unavailable"] if u["reason"] != "unimplemented")},
    }


def tests_header(report: TestReport, row: HeaderRow, blasix: RepoInfo) -> TestsHeader:
    interfaces = [i for i in report["interfaces"] if i["header"] == row["header"]]
    tests: dict[str, list[TestRecord]] = defaultdict(list)
    for t in report["tests"]:
        if t["category"] == row["category"]:
            tests[t["function"]].append(t)
    failures = {u["unit"]: u for u in report["unavailable"]}

    by_group: dict[str, list[InterfaceView]] = defaultdict(list)
    for i in interfaces:
        group = (i["group"] or GROUP_DEFS) if i["unit"] else GROUP_NONE
        by_group[group].append({
            "iface": i,
            "anchor": _anchor(i["name"]),
            "verdict_label": VERDICT_LABELS.get(i["verdict"], i["verdict"]),
            "verdict_help": VERDICT_HELP.get(i["verdict"], ""),
            "probe_label": PROBE_LABELS.get(i["probe"], i["probe"]),
            "tests": [_test_view(t, blasix) for t in tests.get(i["name"], [])],
            "failure": failures.get(i["unit"]) if i["built"] is False else None,
            "unit_href": source_url(blasix, f"src/suites/{i['unit']}.c") if i["unit"] else "",
        })
    order = sorted(by_group, key=lambda g: (g == GROUP_NONE, g == GROUP_DEFS, g))
    groups: list[GroupView] = [
        {"name": g, "anchor": "group-" + _anchor(g.lower()), "label": g,
         "interfaces": sorted(by_group[g], key=lambda v: v["iface"]["name"]),
         "counts": dict(Counter(v["iface"]["verdict"] for v in by_group[g]))}
        for g in order
    ]
    statuses = Counter(t["status"] for i in interfaces for t in tests.get(i["name"], []))
    return {
        "title": f"<{row['header']}>",
        "crumbs": crumbs(("../", "hajlibc"), ("./", "Tests")),
        "run": report["summary"],
        "row": row,
        "groups": groups,
        "verdicts": _verdict_tiles(Counter(i["verdict"] for i in interfaces)),
        "tiles": _tiles(dict(statuses)),
        "leaks": [x for x in report["leaks"] if x["header"] == row["header"]],
        "blasix": blasix,
    }
