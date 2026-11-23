#!/usr/bin/env python3
"""
hajlibc POSIX tracker.

    python run.py sync                  extract releases from the libc's git tags
    python run.py scan [--force] [--clear-cache]
    python run.py build [--force]
    python run.py all [--force] [--clear-cache]
    python run.py debug <version> [--file <relpath>]
    python run.py clear-cache [<version>|all]
    python run.py help
"""
import argparse

from app import analyze, stats, generate, sources, summary
from app.cache import clear_cache


def _debug(version: str, relpath: str | None) -> None:
    from config import SOURCES_DIR

    root = SOURCES_DIR / version
    if not root.exists():
        print(f"!! release introuvable: {root}")
        return

    if relpath:
        p = root / relpath
        if not p.exists():
            print(f"!! fichier introuvable: {p}")
            return
        inc = root / "include"
        dirs = [d for d in (inc, inc / "bits") if d.exists()]
        names = analyze.scan_c_file(p, dirs)
        print(f"# {relpath} → {len(names)} symboles")
        for n in sorted(names):
            print(f"  {n}")
        return

    scan = analyze.scan_release(version)
    print(f"# {version} → {len(scan['defined'])} symboles définis")
    print(f"# headers présents : {len(scan['headers_present'])}")
    for n in sorted(scan["defined"]):
        print(f"  {n}")


def main() -> None:
    p = argparse.ArgumentParser(description="hajlibc POSIX tracker")
    p.add_argument("cmd", nargs="?", default="all",
                   choices=["sync", "scan", "build", "all", "debug", "clear-cache", "help"])
    p.add_argument("version", nargs="?", default=None,
                   help="debug : release à inspecter ; clear-cache : release à vider (défaut / all = toutes)")
    p.add_argument("--file", default=None,
                   help="Pour 'debug' : chemin relatif dans la release")
    p.add_argument("--force", action="store_true",
                   help="Force le rescan (ignore le cache)")
    args = p.parse_args()

    # --- clear-cache ---
    if args.cmd == "help":
        p.print_help()
        return

    if args.cmd == "clear-cache":
        from config import SOURCES_DIR
        version = None if args.version in (None, "all") else args.version
        if version is not None and not (SOURCES_DIR / version).is_dir():
            print(f"!! release introuvable: {version}")
            return
        clear_cache(version)
        print(f"[cache] cleared {version or 'all'}")
        return

    # --- debug ---
    if args.cmd == "debug":
        if not args.version:
            print("!! 'debug' nécessite une version, ex: python run.py debug v1.0")
            return
        _debug(args.version, args.file)
        return

    releases = None

    # --- sync (git tags -> data/sources) ---
    if args.cmd in ("sync", "all"):
        print("==> Syncing sources from git")
        sources.sync()
        if args.cmd == "sync":
            return

    # --- scan ---
    if args.cmd in ("scan", "all"):
        print("==> Scanning releases")
        releases = analyze.scan_all(force=args.force)

    # --- build ---
    if args.cmd in ("build", "all"):
        if releases is None:
            print("==> Scanning releases")
            releases = analyze.scan_all(force=args.force)

        print("==> Computing statistics")
        s = stats.compute_all_stats(releases)

        print("==> Generating site")
        generate.generate(s)
        summary.export(s)
        from config import OUTPUT_DIR
        print(f"Done -> {OUTPUT_DIR}/index.html")


if __name__ == "__main__":
    main()
