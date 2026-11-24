"""The coverage pages, from blåsix's lcov tracefile:

    coverage/index.html             total, and per category (src/<category>/, include/)
    coverage/<category>.html        its files
    coverage/files/<path>.html      one file: its functions and its source,
                                    every line marked run or not (as genhtml)

Arranges the data for src/templates/reports/coverage*.html.
"""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from .model import CategoryCoverage, CoverageReport, CoverageSummary, FileCoverage, FunctionCoverage, RepoInfo
from .pages import Crumb, crumbs, short_date, source_url

CATEGORY_LABELS = {"include": "public headers (inline functions)"}


class FileRow(TypedDict):
    file: FileCoverage
    name: str           # path inside the category
    href: str


class CategoryView(TypedDict):
    category: CategoryCoverage
    label: str
    href: str


class SourceLine(TypedDict):
    n: int
    text: str
    hits: str           # "" for a line that is not code
    cls: str            # hit / miss / ""
    branches: list[str]  # "+" taken, "-" not taken, "#" never reached


class FunctionRow(TypedDict):
    fn: FunctionCoverage
    cls: str


class CoverageIndex(TypedDict):
    title: str
    crumbs: list[Crumb]
    summary: CoverageSummary
    repo: RepoInfo
    date: str
    categories: list[CategoryView]


class CoverageCategory(TypedDict):
    title: str
    crumbs: list[Crumb]
    category: CategoryCoverage
    label: str
    files: list[FileRow]


class CoverageFile(TypedDict):
    title: str
    crumbs: list[Crumb]
    file: FileCoverage
    functions: list[FunctionRow]
    lines: list[SourceLine]
    missing_source: bool
    href: str           # the file in the repository
    uncovered: int      # executable lines never run


def label(category: str) -> str:
    return CATEGORY_LABELS.get(category, f"src/{category}/")


def file_page(path: str) -> str:
    """Page of a source file, relative to coverage/."""
    return f"files/{path}.html"


def coverage_index(cov: CoverageReport, repo: RepoInfo) -> CoverageIndex:
    s = cov["summary"]
    return {
        "title": "Coverage",
        "crumbs": crumbs(("../", "hajlibc")),
        "summary": s, "repo": repo, "date": short_date(s["generated"]),
        "categories": [{"category": c, "label": label(c["name"]), "href": f"{c['slug']}.html"}
                       for c in s["categories"]],
    }


def coverage_category(cov: CoverageReport, category: CategoryCoverage) -> CoverageCategory:
    prefix = "include/" if category["name"] == "include" else f"src/{category['name']}/"
    return {
        "title": f"Coverage of {label(category['name'])}",
        "crumbs": crumbs(("../", "hajlibc"), ("./", "Coverage")),
        "category": category,
        "label": label(category["name"]),
        "files": [{"file": f, "name": f["path"].removeprefix(prefix), "href": file_page(f["path"])}
                  for f in cov["files"] if f["category"] == category["name"]],
    }


def _hits(n: int) -> str:
    if n >= 10_000_000:
        return f"{n / 1_000_000:.0f}M"
    if n >= 10_000:
        return f"{n / 1000:.0f}k"
    return str(n)


def coverage_file(f: FileCoverage, repo: Path, info: RepoInfo, category_slug: str) -> CoverageFile:
    up = "../" * (f["path"].count("/") + 1)          # from coverage/files/<path>.html to coverage/
    source = repo / f["path"]
    text = source.read_text(encoding="utf-8", errors="replace").splitlines() if source.is_file() else []
    last = max([len(text), *f["hits"].keys()], default=0)
    lines: list[SourceLine] = []
    for n in range(1, last + 1):
        hits = f["hits"].get(n)
        lines.append({
            "n": n,
            "text": text[n - 1] if n <= len(text) else "",
            "hits": "" if hits is None else _hits(hits),
            "cls": "" if hits is None else ("hit" if hits else "miss"),
            "branches": ["#" if b is None else "+" if b else "-" for b in f["branch_hits"].get(n, [])],
        })
    return {
        "title": f["path"],
        "crumbs": crumbs((up + "../", "hajlibc"), (up, "Coverage"),
                         (f"{up}{category_slug}.html", f["category"])),
        "file": f,
        "functions": [{"fn": fn, "cls": "hit" if fn["calls"] else "miss"} for fn in f["function_list"]],
        "lines": lines,
        "missing_source": not text,
        "href": source_url(info, f["path"]),
        "uncovered": sum(1 for h in f["hits"].values() if h == 0),
    }
