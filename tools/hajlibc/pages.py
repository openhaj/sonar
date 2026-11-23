"""HTML of the generated hajlibc report pages (tests, coverage, docs).

Each function returns the context of src/templates/report.html: a title, a
back link and the page body. Every value from the data is escaped.
"""
from __future__ import annotations

import re
from html import escape as e
from typing import TypedDict

from markupsafe import Markup

from .model import CoverageReport, HeaderDoc, RepoInfo, TestReport


class Report(TypedDict):
    """Context of src/templates/report.html."""
    title: str
    body: Markup
    back: str
    back_label: str


def report(title: str, body: str, back: str = "../", back_label: str = "hajlibc") -> Report:
    return {"title": title, "body": Markup(body), "back": back, "back_label": back_label}


def slug(header: str) -> str:
    """sys/mman.h -> sys-mman-h"""
    return re.sub(r"[^a-z0-9]+", "-", header.lower()).strip("-")


def meter(percent: float) -> str:
    return f'<span class="meter"><span style="width:{max(0.0, min(100.0, percent)):.1f}%"></span></span>'


def short_date(iso: str | None) -> str:
    return iso[:10] if iso else "-"


# A search box filtering the rows marked with data-row (lower-case text).
FILTER = """<input class="filter" type="search" placeholder="Filter…" aria-label="Filter rows"
       oninput="for(const r of document.querySelectorAll('[data-row]'))r.hidden=!r.dataset.row.includes(this.value.toLowerCase())">"""

STATUSES = ("pass", "fail", "crash", "timeout", "error", "skip", "unavailable")


def tests_page(report_data: TestReport, repo: RepoInfo) -> Report:
    s = report_data["summary"]
    tiles = "".join(
        f'<div class="tile {k}"><b>{s["summary"].get(k, 0)}</b><span>{k}</span></div>' for k in STATUSES)
    headers = "".join(
        f'<tr data-row="{e(h.lower())}"><td><code>{e(h)}</code></td><td>{c["required"]}</td>'
        f'<td>{c["tested"]}</td><td>{c["verified"]}</td>'
        f'<td>{meter(100 * c["verified"] / c["required"] if c["required"] else 0)}</td></tr>'
        for h, c in s["headers"].items())
    rows = "".join(
        f'<tr data-row="{e(" ".join((t["category"], t["function"], t["test"], t["status"])).lower())}">'
        f'<td>{e(t["category"])}</td><td><code>{e(t["function"])}</code></td><td>{e(t["test"])}</td>'
        f'<td><span class="status {e(t["status"])}">{e(t["status"])}</span></td>'
        f'<td>{t["checks"]}</td><td>{t["ms"]:.1f}</td></tr>'
        for t in report_data["tests"])
    not_built = "".join(
        f'<li><code>{e(u["function"])}</code> ({e(u["category"])}): did not build</li>'
        for u in report_data["unavailable"])

    body = f"""    <h1>Tests</h1>
    <p class="tagline">{s["total"]} tests, {s["checks"]} checks on {s["functions"]} functions, run by
      <a href="../../blasix/">blåsix</a> against hajlibc <code>{e(repo["commit_short"])}</code>
      - target {e(s["target"])}, {short_date(s["generated"])}.</p>
    <div class="tiles">{tiles}</div>
    {f"<h2>Did not build</h2><ul>{not_built}</ul>" if not_built else ""}
    <h2>Conformance per header</h2>
    <p class="muted">Interfaces the target requires, how many have tests, and how many pass all of them.</p>
    <div class="table-wrap"><table>
      <thead><tr><th>Header</th><th>Required</th><th>Tested</th><th>Verified</th><th></th></tr></thead>
      <tbody>{headers}</tbody></table></div>
    <h2>All tests</h2>
    {FILTER}
    <div class="table-wrap"><table>
      <thead><tr><th>Category</th><th>Function</th><th>Test</th><th>Status</th><th>Checks</th><th>ms</th></tr></thead>
      <tbody>{rows}</tbody></table></div>"""
    return report("Tests", body)


def coverage_page(coverage: CoverageReport, repo: RepoInfo) -> Report:
    s = coverage["summary"]
    dirs = "".join(
        f'<tr><td><code>{e(d)}/</code></td><td>{c["hit"]} / {c["lines"]}</td>'
        f'<td>{c["percent"]:.1f}%</td><td>{meter(c["percent"])}</td></tr>'
        for d, c in s["dirs"].items())
    files = "".join(
        f'<tr data-row="{e(f["file"].lower())}"><td><code>{e(f["file"])}</code></td>'
        f'<td>{f["hit"]} / {f["lines"]}</td><td>{f["percent"]:.1f}%</td><td>{meter(f["percent"])}</td></tr>'
        for f in coverage["files"])

    body = f"""    <h1>Coverage</h1>
    <p class="tagline">Lines of hajlibc <code>{e(repo["commit_short"])}</code> executed by the blåsix
      test suite - {short_date(s["generated"])}.</p>
    <div class="big-stat"><b>{s["percent"]:.1f}%</b><span>{s["hit"]} of {s["lines"]} lines
      in {len(coverage["files"])} files</span>{meter(s["percent"])}</div>
    <h2>Per directory</h2>
    <div class="table-wrap"><table>
      <thead><tr><th>Directory</th><th>Lines</th><th>Cover</th><th></th></tr></thead>
      <tbody>{dirs}</tbody></table></div>
    <h2>Per file</h2>
    {FILTER}
    <div class="table-wrap"><table>
      <thead><tr><th>File</th><th>Lines</th><th>Cover</th><th></th></tr></thead>
      <tbody>{files}</tbody></table></div>"""
    return report("Coverage", body)


def docs_index_page(docs: dict[str, HeaderDoc], repo: RepoInfo) -> Report:
    cards = "".join(
        f'<a class="card" href="{slug(h)}.html" data-row="{e((h + " " + d["brief"]).lower())}">'
        f'<div class="card-head"><h3><code>&lt;{e(h)}&gt;</code></h3>'
        f'<span class="badge">{len(d["entries"])}</span></div><p>{e(d["brief"])}</p></a>'
        for h, d in docs.items())
    declarations = sum(len(d["entries"]) for d in docs.values())

    body = f"""    <h1>Documentation</h1>
    <p class="tagline">API reference of hajlibc <code>{e(repo["commit_short"])}</code>: {declarations} documented
      declarations in {len(docs)} headers, extracted from the doc comments of the headers.</p>
    {FILTER}
    <div class="grid">{cards}</div>"""
    return report("Documentation", body)


def header_doc_page(header: str, doc: HeaderDoc) -> Report:
    toc = "".join(f'<a href="#{e(x["name"])}"><code>{e(x["name"])}</code></a>' for x in doc["entries"])
    sections: list[str] = []
    for x in doc["entries"]:
        params = "".join(f"<tr><td><code>{e(name)}</code></td><td>{e(text)}</td></tr>" for name, text in x["params"])
        sections.append(f"""    <section class="api" id="{e(x["name"])}">
      <h3><code>{e(x["name"])}</code></h3>
      <pre><code>{e(x["decl"])}</code></pre>
      {f"<p>{e(x['brief'])}</p>" if x["brief"] else ""}
      {f"<p class='muted'>{e(x['text'])}</p>" if x["text"] else ""}
      {f"<table class='params'><tbody>{params}</tbody></table>" if params else ""}
      {f"<p><b>Returns</b> {e(x['returns'])}</p>" if x["returns"] else ""}
      {"".join(f"<p class='note'>{e(note)}</p>" for note in x["notes"])}
    </section>""")

    body = f"""    <h1><code>&lt;{e(header)}&gt;</code></h1>
    <p class="tagline">{e(doc["brief"])}</p>
    {f"<p>{e(doc['text'])}</p>" if doc["text"] else ""}
    {"".join(f"<p class='note'>{e(note)}</p>" for note in doc["notes"])}
    <nav class="toc">{toc}</nav>
{chr(10).join(sections)}"""
    return report(f"<{header}>", body, back="./", back_label="All headers")
