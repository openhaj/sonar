"""Badges for the projects' READMEs, as SVG images: dist/assets/<project>/<name>.svg.

Configured by src/badges.toml, one table per badge:

    [<project>.<name>]          # -> dist/assets/<project>/<name>.svg
    kind  = "coverage"          # what it shows and where it reads it (see KINDS)
    label = "coverage"          # optional: text of the label side
    icon  = "target"            # optional: an icon of icons.py ("" for none)
    color = "green"             # optional: fixed value colour (palette.py name or #rrggbb)
    link  = "projects/x/cov/"   # optional: where the badge leads on the site (relative to its root)

Paths may use {root} {build} {dist} and the projects' checkouts ({hajlibc},
{blasix}...: main.py's Paths), and globs: the most recent match is read.
A JSON field is a dotted path, list indexes allowed: "versions.-1.percent".
When an input is missing the badge is still written, grey, "not built".

From Python, kinds.py builds badges from plain values and svg.render()
draws them, without any configuration.
"""
from __future__ import annotations

import json
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypedDict, cast

from tools import lcov

from . import kinds
from .svg import Badge, render

__all__ = ["BadgeLink", "Badge", "build", "catalog", "kinds", "render"]


class MissingInput(Exception):
    """An input of a badge is not there (yet): the badge is drawn grey."""


class BadgeLink(TypedDict):
    """A configured badge, for the pages (src/templates/project.html)."""
    name: str
    src: str        # relative to the site root
    alt: str
    link: str | None


# ----- configuration -----


@dataclass(frozen=True)
class Spec:
    project: str
    name: str
    kind: str
    options: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.options.get(key, default)

    def text(self, key: str, default: str | None = None) -> str:
        value = self.options.get(key, default)
        if not isinstance(value, str):
            raise SystemExit(f"badges.toml: {self.project}.{self.name}.{key} must be a string")
        return value

    @property
    def file(self) -> str:
        return f"assets/{self.project}/{self.name}.svg"


def load(config: Path) -> list[Spec]:
    data = tomllib.loads(config.read_text(encoding="utf-8"))
    specs: list[Spec] = []
    for project, table in data.items():
        if not isinstance(table, dict):
            raise SystemExit(f"badges.toml: '{project}' must be a table of badges")
        for name, options in cast("dict[str, Any]", table).items():
            if not isinstance(options, dict):
                raise SystemExit(f"badges.toml: {project}.{name} must be a table")
            opts = cast("dict[str, Any]", options)
            kind = opts.get("kind")
            if kind not in KINDS:
                raise SystemExit(f"badges.toml: {project}.{name}.kind must be one of {', '.join(KINDS)}")
            specs.append(Spec(project, name, kind, opts))
    return specs


def catalog(config: Path) -> dict[str, list[BadgeLink]]:
    """The configured badges of each project, without computing them."""
    out: dict[str, list[BadgeLink]] = {}
    if not config.exists():
        return out
    for s in load(config):
        link = s.get("link")
        out.setdefault(s.project, []).append({
            "name": s.name, "src": s.file, "link": link if isinstance(link, str) else None,
            "alt": s.text("alt", s.get("label") or s.name)})
    return out


# ----- inputs -----


@dataclass
class Inputs:
    vars: dict[str, str]

    def path(self, spec: Spec, key: str) -> Path:
        """The file named by option `key` (placeholders expanded, a glob
        resolved to its most recent match)."""
        pattern = spec.text(key).format(**self.vars)
        if not any(c in pattern for c in "*?["):
            p = Path(pattern)
            if not p.exists():
                raise MissingInput(f"{p} not found")
            return p
        anchor = Path(pattern)
        while any(c in anchor.name for c in "*?[") or any(c in str(anchor.parent) for c in "*?["):
            anchor = anchor.parent
        rest = Path(pattern).relative_to(anchor).as_posix()
        found = sorted(anchor.glob(rest), key=lambda p: p.stat().st_mtime) if anchor.exists() else []
        if not found:
            raise MissingInput(f"nothing matches {pattern}")
        return found[-1]

    def json(self, spec: Spec, key: str = "source") -> Any:
        return json.loads(self.path(spec, key).read_text(encoding="utf-8"))


def field(data: Any, path: str) -> Any:
    """`data` at the dotted `path` ("versions.-1.percent")."""
    cur = data
    for part in path.split("."):
        if isinstance(cur, list):
            items = cast("list[Any]", cur)
            try:
                cur = items[int(part)]
            except (ValueError, IndexError):
                raise MissingInput(f"no item '{part}' in '{path}'") from None
        elif isinstance(cur, dict) and part in cur:
            cur = cast("dict[str, Any]", cur)[part]
        else:
            raise MissingInput(f"no field '{part}' in '{path}'")
    return cur


def number(data: Any, paths: Any) -> float:
    """The number at a path, or the sum of the numbers at a list of paths."""
    total = 0.0
    for p in ([paths] if isinstance(paths, str) else cast("list[str]", paths)):
        value = field(data, p)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise MissingInput(f"'{p}' is not a number")
        total += value
    return total


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


# ----- kinds -----

def _label(spec: Spec, default: str) -> str:
    return spec.text("label", default)


def _icon(spec: Spec, default: str | None) -> str | None:
    icon = spec.get("icon", default)
    return icon or None


def _static(spec: Spec, _: Inputs) -> Badge:
    return kinds.static(_label(spec, spec.name), spec.text("value"), spec.text("color", "blue"),
                        _icon(spec, None))


def _git_ref(spec: Spec, inputs: Inputs) -> Badge:
    """A release when the checkout is on a tag (matching `tags`, default
    "v*"), otherwise its branch and commit."""
    repo = inputs.path(spec, "repo")
    if not (repo / ".git").exists():
        raise MissingInput(f"{repo} is not a git checkout")
    tag = _git(repo, "describe", "--tags", "--exact-match", "--match", spec.text("tags", "v*"), "HEAD")
    if tag:
        return kinds.release(tag, _label(spec, "release"), spec.text("color", "blue"))
    commit = _git(repo, "rev-parse", "--short", "HEAD")
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if branch in ("", "HEAD"):   # detached (a submodule): a branch that points there
        refs = _git(repo, "for-each-ref", "--points-at", "HEAD", "--format=%(refname:short)",
                    "refs/heads", "refs/remotes").split()
        refs = [r.split("/", 1)[1] if r.startswith("origin/") else r for r in refs if not r.endswith("/HEAD")]
        branch = refs[0] if refs else "detached"
    return kinds.revision(branch, commit, spec.text("color", "violet"))


def _percent(spec: Spec, inputs: Inputs) -> Badge:
    """`value` (a score out of `max`, default 100), or `done` / `total`."""
    data = inputs.json(spec)
    if "done" in spec.options:
        total = number(data, spec.get("total"))
        value = 100 * number(data, spec.get("done")) / total if total else 0.0
    else:
        value = 100 * number(data, spec.get("value")) / float(spec.get("max", 100))
    color = spec.get("color")
    return kinds.percent(_label(spec, spec.name), value, _icon(spec, "gauge"), int(spec.get("decimals", 1)),
                         color if isinstance(color, str) else None, bar=spec.get("bar", True) is True)


def _coverage(spec: Spec, inputs: Inputs) -> Badge:
    """From an lcov tracefile (`lcov`): `metric` lines, functions or
    branches; only the files under `under` when given."""
    metric = spec.text("metric", "lines")
    if metric not in ("lines", "functions", "branches"):
        raise SystemExit(f"badges.toml: {spec.project}.{spec.name}.metric: lines, functions or branches")
    records = list(lcov.parse(inputs.path(spec, "lcov")).values())
    if "under" in spec.options:
        root = Path(spec.text("under").format(**inputs.vars)).resolve()
        records = [r for r in records if Path(r.path).is_relative_to(root)]
    found = hit = 0
    for r in records:
        if metric == "lines":
            found, hit = found + len(r.lines), hit + sum(1 for h in r.lines.values() if h > 0)
        elif metric == "functions":
            found, hit = found + len(r.functions), hit + sum(1 for _, c in r.functions.values() if c > 0)
        else:
            found, hit = found + len(r.branches), hit + sum(1 for t in r.branches.values() if t)
    if not found:
        raise MissingInput("the tracefile has no " + metric)
    return kinds.coverage(100 * hit / found, metric, _label(spec, "coverage"), _icon(spec, "target") or "",
                          int(spec.get("decimals", 1)))


def _tests(spec: Spec, inputs: Inputs) -> Badge:
    """Counts from a JSON report (`source`): `passed`, `failed`, `skipped`,
    each a path or a list of paths added up."""
    data = inputs.json(spec)
    count: Callable[[str], int] = lambda key: int(number(data, spec.get(key))) if key in spec.options else 0
    return kinds.tests(count("passed"), count("failed"), count("skipped"), _label(spec, "tests"),
                       _icon(spec, "flask") or "")


KINDS: dict[str, Callable[[Spec, Inputs], Badge]] = {
    "static": _static,
    "git": _git_ref,
    "percent": _percent,
    "coverage": _coverage,
    "tests": _tests,
}

DEFAULT_ICONS = {"git": "branch", "percent": "gauge", "coverage": "target", "tests": "flask"}


# ----- build -----


def build(config: Path, dist: Path, variables: dict[str, Path], warn: Callable[[str], None]) -> list[str]:
    """Write every badge of `config` under dist/; returns their paths."""
    inputs = Inputs({k: str(v) for k, v in variables.items()})
    written: list[str] = []
    for spec in load(config):
        try:
            badge = KINDS[spec.kind](spec, inputs)
        except MissingInput as e:
            warn(f"{spec.project}/{spec.name}: {e}: drawn as not built")
            badge = kinds.unknown(_label(spec, spec.name), _icon(spec, DEFAULT_ICONS.get(spec.kind)))
        out = dist / spec.file
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(badge, uid=f"{spec.project}-{spec.name}"), encoding="utf-8")
        written.append(spec.file)
    return written
