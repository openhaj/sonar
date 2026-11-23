# POSIX tracker

Track how much of POSIX your libc implements, per release, with
weighted progress, sortable tables and Chart.js graphs.

## Use

Normally run by the site's `main.py` (step `posix`). On its own:

    python run.py all               # sync + scan + build
    python run.py sync              # extract releases from the libc's git tags
    python run.py scan [--force]    # scan the extracted releases (cached)
    python run.py build             # regenerate the pages + summary.json

Environment: `HAJLIBC` (libc git repository, default `external/hajlibc`),
`TRACKER_WORK` (extracted sources and cache, default `.build/posix-tracker`),
`TRACKER_OUT` (pages, default `dist/projects/hajlibc/posix`),
`TRACKER_POSIX_DIR` (POSIX reference data, default `data/posix`).

Releases are the repository's `v*` tags plus its `HEAD` (as `dev`); each is
extracted with `git archive` and identified by its commit, so an unchanged
release is never rescanned.

Functions and global variables are read with `nm` from the release's static
library, obtained in this order:

1. built here from the release's sources;
2. if that fails (an old tag may no longer build with a newer toolchain or
   without some system headers), the prebuilt library of the release on
   GitHub for this machine, checked against the release's `SHA256SUMS` and
   the digest GitHub reports, and cached in `prebuilt/` of the work dir;
3. as a last resort (offline, no release), the objects that did compile:
   the functions of the files that did not are then missed.

`summary.json` records which one was used for each version (`library`).

The POSIX.1-2024 reference data is not in git: `posix-data.toml` names an
immutable archive (checked by sha256), which the site's `main.py` fetches and
extracts, then passes to the tracker through `TRACKER_POSIX_DIR`.

## Categories and weights

| Category  | Weight |
|-----------|--------|
| functions | 3.0    |
| structs   | 2.5    |
| unions    | 2.5    |
| enums     | 2.0    |
| types     | 2.0    |
| macros    | 1.5    |
| constants | 1.0    |

`percent = Σ(done × weight) / Σ(total × weight) × 100`

## Not tracked (yet)

- Individual struct fields (`sa_family`, `msg_iovlen`…)
- Optional / obsolescent markers (`[ADV]`, `[OB]`…)
- Runtime `_SC_*` constants

## Scripts

The pages' script is TypeScript, in `ts/`: sortable tables (`sort.ts`), the
row filter (`filter.ts`) and the charts (`charts.ts`, with Chart.js pinned
and checked by SRI in `templates/base.html`). The chart data is embedded in
the pages as JSON (`<script type="application/json" id="chart-data">`). The
site's `main.py` type-checks it with the rest of the TypeScript (step
`scripts`) and bundles it into `static/js/tracker.js` (step `posix`).
