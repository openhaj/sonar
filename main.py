#!/usr/bin/env python3
"""sonar: builds the openhaj website into dist/.

    python3 main.py                       build everything
    python3 main.py build [--only S,..]   build some steps only (see `steps`)
    python3 main.py build --skip tests    everything but the slow test runs
    python3 main.py serve [--port 8000]   preview dist/ in a browser
    python3 main.py clean [--all]         remove dist/ and .build/ (--all: downloads too)
    python3 main.py steps                 list the build steps

Layout:
    src/        hand-written site: site.toml (projects), templates/ (layouts),
                pages/ (one template per page), assets/ (css, images),
                ts/ (TypeScript: one bundle per entry in ts/entries/)
    tools/      render.py (templates) and generators (POSIX tracker, hajlibc pages)
    external/   git submodules of the projects the site reports on
    .build/     intermediate files (tool caches, test runs)   - not committed
    dist/       the finished site, ready to publish            - not committed

Overrides (environment): HAJLIBC=/path/to/hajlibc  BLASIX=/path/to/blasix
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import os
import shutil
import subprocess
import sys
import time
import venv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# ============================================================================
# Paths
# ============================================================================

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Paths:
    src: Path = ROOT / "src"
    dist: Path = ROOT / "dist"
    build: Path = ROOT / ".build"
    venv: Path = ROOT / ".venv"
    requirements: Path = ROOT / "requirements.txt"
    ts_entries: Path = ROOT / "src" / "ts" / "entries"

    tracker: Path = ROOT / "tools" / "posix-tracker"
    posix_data: Path = ROOT / "tools" / "posix-tracker" / "posix-data.toml"
    hajlibc: Path = Path(os.environ.get("HAJLIBC", ROOT / "external" / "hajlibc")).resolve()
    blasix: Path = Path(os.environ.get("BLASIX", ROOT / "external" / "blasix")).resolve()

    # where each generated part ends up
    @property
    def hajlibc_out(self) -> Path:
        return self.dist / "projects" / "hajlibc"

    @property
    def tests_run(self) -> Path:          # blåsix, normal run (probes)
        return self.build / "blasix" / "run"

    @property
    def tests_cov(self) -> Path:          # blåsix, coverage run
        return self.build / "blasix" / "coverage"


P = Paths()


# ============================================================================
# Output helpers
# ============================================================================

def log(step: str, msg: str) -> None:
    print(f"  {step.upper():<8} {msg}", flush=True)


def warn(step: str, msg: str) -> None:
    print(f"  {step.upper():<8} warning: {msg}", file=sys.stderr, flush=True)


def run(step: str, cmd: list[str | Path], env: dict[str, str] | None = None, check: bool = True) -> bool:
    """Run a command, streaming its output. Returns True on success."""
    r = subprocess.run([str(c) for c in cmd], env={**os.environ, **(env or {})})
    if r.returncode != 0:
        (warn if not check else log)(step, f"`{Path(str(cmd[0])).name} …` exited with {r.returncode}")
        if check:
            raise SystemExit(r.returncode)
        return False
    return True


# ============================================================================
# Python environment (only the POSIX tracker needs third-party packages)
# ============================================================================

def in_venv() -> bool:
    return Path(sys.prefix).resolve() == P.venv.resolve()


def ensure_venv() -> None:
    """Create .venv with requirements.txt and re-run main.py inside it."""
    if in_venv():
        return
    py = P.venv / "bin" / "python"
    stamp = P.venv / ".requirements.sha256"
    reqs = P.requirements.read_bytes() + (P.tracker / "requirements.txt").read_bytes()
    digest = hashlib.sha256(reqs).hexdigest()

    if not py.exists():
        log("venv", f"creating {P.venv.relative_to(ROOT)}")
        venv.create(P.venv, with_pip=True)
    if not stamp.exists() or stamp.read_text() != digest:
        log("venv", "installing requirements")
        run("venv", [py, "-m", "pip", "install", "-q", "-r", P.requirements])
        stamp.write_text(digest)
    os.execv(py, [str(py), str(Path(__file__).resolve()), *sys.argv[1:]])


# ============================================================================
# Build steps
# ============================================================================

@dataclass
class Step:
    name: str
    help: str
    fn: Callable[[], None]
    needs_venv: bool = False


STEPS: dict[str, Step] = {}


def step(name: str, help: str, needs_venv: bool = False):
    def register(fn: Callable[[], None]) -> Callable[[], None]:
        STEPS[name] = Step(name, help, fn, needs_venv)
        return fn
    return register


@functools.cache
def site():
    """The template renderer (tools/render.py), shared by every step."""
    from tools.render import Site
    return Site(P.src, P.dist)


def require(step_name: str, path: Path, hint: str) -> bool:
    if path.exists():
        return True
    warn(step_name, f"{path} not found ({hint}): skipped")
    return False


@step("static", "render src/pages/ with src/templates/, copy src/assets/ -> dist/", needs_venv=True)
def build_static() -> None:
    shutil.copytree(P.src / "assets", P.dist / "assets", dirs_exist_ok=True)
    rendered, copied = site().build_pages()
    log("static", f"{rendered} pages rendered, {copied} files copied -> {P.dist.relative_to(ROOT)}/")


@step("scripts", "type-check all TypeScript, bundle src/ts/entries/*.ts -> dist/assets/js/")
def build_scripts() -> None:
    # tsc and esbuild are native binaries, fetched once by tools/scripts.py:
    # no Node.js needed.
    from tools import scripts
    cache = P.build / "toolchain"
    say = functools.partial(log, "scripts")
    log("scripts", "type-checking")
    if not scripts.check(ROOT, cache, say):
        raise SystemExit("scripts: type errors (see above)")
    entries = sorted(P.ts_entries.glob("*.ts"))
    out = P.dist / "assets" / "js"
    if not scripts.bundle(entries, out, cache, say):
        raise SystemExit("scripts: bundling failed")
    sizes = ", ".join(f"{e.stem}.js {(out / (e.stem + '.js')).stat().st_size / 1024:.1f} KiB" for e in entries)
    log("scripts", sizes)


@step("posix", "hajlibc POSIX conformance tracker -> dist/projects/hajlibc/posix/", needs_venv=True)
def build_posix() -> None:
    if not require("posix", P.hajlibc / ".git", "git submodule update --init"):
        return
    from tools import datasets
    reference = datasets.ensure(P.posix_data, P.build / "datasets", functools.partial(log, "posix"))
    run("posix", [sys.executable, P.tracker / "run.py", "all"], env={
        "TRACKER_POSIX_DIR": str(reference),
        "HAJLIBC": str(P.hajlibc),
        "TRACKER_WORK": str(P.build / "posix-tracker"),
        "TRACKER_OUT": str(P.hajlibc_out / "posix"),
    })
    # the tracker's TypeScript (tools/posix-tracker/ts/), into its pages
    from tools import scripts
    if not scripts.bundle([P.tracker / "ts" / "tracker.ts"], P.hajlibc_out / "posix" / "static" / "js",
                          P.build / "toolchain", functools.partial(log, "posix")):
        raise SystemExit("posix: bundling the tracker script failed")


@step("tests", "run the blåsix test suite on hajlibc, normal and coverage runs -> .build/blasix/")
def build_tests() -> None:
    if not (require("tests", P.blasix / "Makefile", "git submodule update --init, or BLASIX=")
            and require("tests", P.hajlibc / "Makefile", "git submodule update --init, or HAJLIBC=")):
        return
    common = ["LIBC=hajlibc", f"HAJLIBC={P.hajlibc}"]
    # A failing test is a result, not a build failure: keep going either way.
    log("tests", "normal run (probes every required interface)")
    run("tests", ["make", "--no-print-directory", "-C", P.blasix, "run", *common,
                  f"BUILD_DIR={P.tests_run}"], check=False)
    log("tests", "coverage run (instrumented hajlibc)")
    run("tests", ["make", "--no-print-directory", "-C", P.blasix, "coverage", *common,
                  f"BUILD_DIR={P.tests_cov}"], check=False)


@step("hajlibc", "hajlibc pages: data.js, tests/, coverage/, docs/ -> dist/projects/hajlibc/")
def build_hajlibc() -> None:
    if not require("hajlibc", P.hajlibc / "include", "git submodule update --init"):
        return
    from tools import hajlibc
    written = hajlibc.build(
        site=site(),
        hajlibc=P.hajlibc,
        tests_dir=P.tests_run / "hajlibc",
        coverage_dir=P.tests_cov / "hajlibc",
        posix_dir=P.hajlibc_out / "posix",
        out=P.hajlibc_out,
    )
    log("hajlibc", ", ".join(written))


# ============================================================================
# Commands
# ============================================================================

def parse_steps(value: str | None) -> list[str]:
    if not value:
        return []
    names = [s.strip() for s in value.split(",") if s.strip()]
    unknown = [n for n in names if n not in STEPS]
    if unknown:
        raise SystemExit(f"unknown step(s): {', '.join(unknown)} (see `python3 main.py steps`)")
    return names


def cmd_build(args: argparse.Namespace) -> None:
    only, skip = parse_steps(args.only), parse_steps(args.skip)
    selected = [s for s in STEPS.values() if (not only or s.name in only) and s.name not in skip]

    if any(s.needs_venv for s in selected):
        ensure_venv()  # may re-run this script inside .venv

    if len(selected) == len(STEPS) and P.dist.exists():
        shutil.rmtree(P.dist)  # full build: start from scratch
    P.dist.mkdir(parents=True, exist_ok=True)
    P.build.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    for s in selected:
        print(f"==> {s.name}: {s.help}", flush=True)
        t = time.monotonic()
        s.fn()
        log(s.name, f"done in {time.monotonic() - t:.1f}s")
    print(f"==> built {P.dist.relative_to(ROOT)}/ in {time.monotonic() - started:.1f}s", flush=True)


def cmd_serve(args: argparse.Namespace) -> None:
    if not (P.dist / "index.html").exists():
        raise SystemExit("dist/ is empty: run `python3 main.py` first")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(P.dist))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"serving {P.dist.relative_to(ROOT)}/ on http://localhost:{args.port} (Ctrl-C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


# Downloads checked by hash (tools, data sets) never go stale: `clean` keeps
# them unless --all.
KEPT_DOWNLOADS = ("toolchain", "datasets")


def cmd_clean(args: argparse.Namespace) -> None:
    removed: list[Path] = []
    if P.dist.exists():
        removed.append(P.dist)
    if P.build.exists():
        if args.all:
            removed.append(P.build)
        else:
            removed += [d for d in P.build.iterdir() if d.name not in KEPT_DOWNLOADS]
    for d in removed:
        shutil.rmtree(d) if d.is_dir() else d.unlink()
        print(f"removed {d.relative_to(ROOT)}{'/' if d.suffix == '' else ''}")


def cmd_steps(_: argparse.Namespace) -> None:
    for s in STEPS.values():
        print(f"  {s.name:<8} {s.help}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command")

    b = sub.add_parser("build", help="build the site into dist/ (default)")
    b.add_argument("--only", metavar="STEPS", help="comma-separated steps to run")
    b.add_argument("--skip", metavar="STEPS", help="comma-separated steps to leave out")
    b.set_defaults(fn=cmd_build)

    s = sub.add_parser("serve", help="preview dist/ on localhost")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=cmd_serve)

    c = sub.add_parser("clean", help="remove dist/ and .build/ (keeps downloaded tools and data)")
    c.add_argument("--all", action="store_true", help="also remove the downloaded tools and data sets")
    c.set_defaults(fn=cmd_clean)
    sub.add_parser("steps", help="list the build steps").set_defaults(fn=cmd_steps)

    argv = sys.argv[1:]
    if not argv or (argv[0].startswith("-") and argv[0] not in ("-h", "--help")):
        argv = ["build", *argv]  # `main.py --skip tests` means `main.py build --skip tests`
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
