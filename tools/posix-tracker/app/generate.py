"""Static pages of the tracker (Jinja templates -> OUTPUT_DIR)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import TypedDict

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.model import Stats
from app.posix_ref import POSIX_BY_NAME
from app.utils import slug
from config import CATEGORIES, CATEGORY_LABELS, OUTPUT_DIR, STATIC_DIR, TEMPLATES_DIR


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["slug"] = slug
    return env


class ChartPoint(TypedDict):
    version: str
    done: int
    total: int


class ChartData(TypedDict):
    labels: list[str]
    percent: list[float]
    categories: dict[str, list[ChartPoint]]  # per category, one point per version


def _chart_data(stats: Stats) -> ChartData:
    versions = stats["versions"]
    releases = stats["releases"]
    return {
        "labels": versions,
        "percent": [round(releases[v]["percent"], 2) for v in versions],
        "categories": {
            cat: [
                {"version": v, "done": releases[v]["totals"][cat]["done"], "total": releases[v]["totals"][cat]["total"]}
                for v in versions
            ]
            for cat in CATEGORIES
        },
    }

def _write(env: Environment, template: str, out: Path, **ctx: object) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    html = env.get_template(template).render(CATEGORIES=CATEGORIES, CATEGORY_LABELS=CATEGORY_LABELS, **ctx)
    out.write_text(html, encoding="utf-8")


def generate(stats: Stats) -> None:
    env = _env()
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, OUTPUT_DIR / "static")

    versions = stats["versions"]
    latest = versions[-1] if versions else None
    release = stats["releases"][latest] if latest else None
    common: dict[str, object] = {
        "stats": stats,
        "versions": versions,
        "latest": latest,
        "chart_data": _chart_data(stats),
        "release": release,
        "headers": release["per_header"] if release else {},
    }

    # overview, headers, versions, one page per category
    templates = {"index": "index.html", "headers": "headers.html", "versions": "versions.html"}
    for page in [*templates, *CATEGORIES]:
        extra: dict[str, object] = {}
        if page in CATEGORIES:
            extra = {"category": page, "category_label": CATEGORY_LABELS.get(page, page)}
        _write(env, templates.get(page, "category.html"), OUTPUT_DIR / f"{page}.html",
               **common, **extra, active=page, root="")

    # one page per header of the latest release
    if release:
        for name, header in release["per_header"].items():
            _write(env, "header.html", OUTPUT_DIR / "headers" / f"{slug(name)}.html",
                   **common, header=header, header_name=name, active="headers", root="../")

    # one page per POSIX symbol
    for name, info in POSIX_BY_NAME.items():
        _write(env, "symbol.html", OUTPUT_DIR / "symbols" / f"{slug(name)}.html",
               **common, symbol=info, symbol_name=name, active=None, root="../")
