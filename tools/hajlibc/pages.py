"""What the generated hajlibc report pages share, and the docs pages.

Every report page renders a template of src/templates/reports/ (or
report.html itself, given a `body`), which extends report.html: a title, a
breadcrumb trail and the page. The tests pages are built by tests_pages.py,
the coverage pages by coverage_pages.py.
"""
from __future__ import annotations

from html import escape as e
from typing import NotRequired, TypedDict

from markupsafe import Markup

from .inputs import slug
from .model import HeaderDoc, RepoInfo

__all__ = ["Crumb", "Report", "report", "slug", "short_date", "source_url", "docs_index_page", "header_doc_page"]


class Crumb(TypedDict):
    href: str
    label: str


class Report(TypedDict):
    """Context of src/templates/report.html."""
    title: str
    crumbs: list[Crumb]
    body: NotRequired[Markup]


def crumbs(*trail: tuple[str, str]) -> list[Crumb]:
    return [{"href": href, "label": label} for href, label in trail]


def report(title: str, body: str, trail: list[Crumb]) -> Report:
    return {"title": title, "body": Markup(body), "crumbs": trail}


def short_date(iso: str | None) -> str:
    return iso[:10] if iso else "-"


def source_url(repo: RepoInfo, path: str, line: int = 0) -> str:
    """Link to a file of `repo` at its commit (GitHub layout), "" without a URL."""
    if not repo["url"] or not repo["commit"]:
        return ""
    return f"{repo['url']}/blob/{repo['commit']}/{path}" + (f"#L{line}" if line > 0 else "")


# A search box filtering the [data-row] elements below it (report.js).
FINDER = """<div class="finder" data-finder>
      <input type="search" data-finder-input placeholder="Filter…" aria-label="Filter">
    </div>"""


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
    <div data-finder-scope>
    {FINDER}
    <div class="grid">{cards}</div>
    <p class="muted" data-finder-empty hidden>Nothing matches.</p>
    </div>"""
    return report("Documentation", body, crumbs(("../", "hajlibc")))


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
    return report(f"<{header}>", body, crumbs(("../", "hajlibc"), ("./", "Documentation")))
