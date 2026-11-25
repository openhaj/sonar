"""Template rendering shared by every page of the site.

    src/site.toml     site metadata and the list of projects
    src/templates/    layouts (base, project, report) and macros
    src/pages/        one template per page; the path is the URL:
                      pages/projects/hajcrypt/index.html -> dist/projects/hajcrypt/index.html
                      (non-HTML files there are copied as they are)

Every template gets:
    site, STATUS, projects   from site.toml
    BADGES                   from badges.toml: each project's badges (tools/badges)
    root                     relative path to the site root ("./", "../../", ...)
    project                  on projects/<slug>/... pages, that project's entry
"""
from __future__ import annotations

import shutil
import tomllib
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from tools import badges

Status = Literal["idea", "wip", "paused", "stable", "archived"]


class SiteInfo(TypedDict):
    name: str
    description: str
    github: str
    license: str
    lang: str


class Project(TypedDict):
    slug: str
    name: str
    status: Status
    tagline: str
    repo: str | None
    featured: bool


def _text(table: dict[str, Any], key: str, where: str) -> str:
    value = table.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"site.toml: {where}.{key} must be a string")
    return value


def _site(table: dict[str, Any]) -> SiteInfo:
    return {
        "name": _text(table, "name", "site"),
        "description": _text(table, "description", "site"),
        "github": _text(table, "github", "site"),
        "license": _text(table, "license", "site"),
        "lang": _text(table, "lang", "site"),
    }


def _project(table: dict[str, Any], statuses: dict[str, str]) -> Project:
    where = f"projects.{table.get('slug', '?')}"
    status = _text(table, "status", where)
    if status not in statuses:
        raise SystemExit(f"site.toml: {where}.status '{status}' is not one of {', '.join(statuses)}")
    repo = table.get("repo")
    return {
        "slug": _text(table, "slug", where),
        "name": _text(table, "name", where),
        "status": cast(Status, status),
        "tagline": _text(table, "tagline", where),
        "repo": repo if isinstance(repo, str) else None,
        "featured": table.get("featured") is True,
    }


class Site:
    def __init__(self, src: Path, dist: Path) -> None:
        self.src, self.dist = src, dist
        self.pages = src / "pages"

        config = tomllib.loads((src / "site.toml").read_text(encoding="utf-8"))
        statuses = {str(k): str(v) for k, v in cast("dict[str, Any]", config["status"]).items()}
        self.site = _site(config["site"])
        self.projects = [_project(p, statuses) for p in cast("list[dict[str, Any]]", config["projects"])]
        self.by_slug = {p["slug"]: p for p in self.projects}

        self.env = Environment(
            loader=FileSystemLoader([src / "templates", self.pages]),
            autoescape=select_autoescape(["html"]),
            undefined=StrictUndefined,       # a typo in a template is an error, not a blank
            keep_trailing_newline=True,
            trim_blocks=True,                # no blank lines left by {% %} tags
            lstrip_blocks=True,
        )
        # available in every template, including imported macros (jinja2 types
        # globals by its default values, hence the cast)
        cast("MutableMapping[str, object]", self.env.globals).update(
            site=self.site, STATUS=statuses, projects=self.projects,
            BADGES=badges.catalog(src / "badges.toml"))

    # ----- paths -----

    def root_for(self, out: Path) -> str:
        """Relative path from the page `out` (in dist/) to the site root."""
        depth = len(out.relative_to(self.dist).parts) - 1
        return "../" * depth or "./"

    def context_for(self, out: Path) -> dict[str, object]:
        parts = out.relative_to(self.dist).parts
        ctx: dict[str, object] = {"root": self.root_for(out)}
        if len(parts) >= 3 and parts[0] == "projects":
            if parts[1] not in self.by_slug:
                raise SystemExit(f"{'/'.join(parts)}: no project '{parts[1]}' in site.toml")
            ctx["project"] = self.by_slug[parts[1]]
        return ctx

    # ----- rendering -----

    def render(self, template: str, out: Path, **ctx: object) -> None:
        """Render `template` to `out` (a path inside dist/)."""
        out.parent.mkdir(parents=True, exist_ok=True)
        html = self.env.get_template(template).render(**self.context_for(out), **ctx)
        out.write_text(html, encoding="utf-8")

    def build_pages(self) -> tuple[int, int]:
        """Render every page of src/pages/ into dist/. Returns (rendered, copied)."""
        rendered = copied = 0
        for path in sorted(self.pages.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(self.pages)
            out = self.dist / rel
            if path.suffix == ".html":
                self.render(rel.as_posix(), out)
                rendered += 1
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, out)
                copied += 1
        return rendered, copied
