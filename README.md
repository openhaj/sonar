# sonar

Static website of the **openhaj** organization and its projects. Pages are
written by hand in `src/` as Jinja templates sharing one layout; the
data-driven parts (hajlibc's POSIX conformance, tests, coverage and API docs)
are generated. `main.py` assembles everything into `dist/`, plain static
HTML/CSS/JS: the site to publish.

## Layout

```
.
├── main.py                    entry point: builds dist/
├── requirements.txt           Python packages (for the POSIX tracker)
├── src/                       hand-written site
│   ├── site.toml              site metadata + the list of projects
│   ├── templates/             base.html (head, nav, waves, footer),
│   │                          project.html, report.html, macros.html,
│   │                          reports/ (tests and coverage pages)
│   ├── pages/                 one template per page, path = URL
│   │   ├── index.html
│   │   └── projects/<project>/index.html
│   ├── assets/                css/, img/
│   └── ts/                    TypeScript, one bundle per entry in dist/assets/js/
│       ├── entries/           site.ts (every page), hajlibc.ts (hajlibc page only),
│       │                      report.ts (generated reports: search, filters)
│       ├── theme.ts           light/dark toggle
│       ├── sky/               background canvas, one module per layer
│       ├── boats.ts, easter-egg.ts
│       ├── hajlibc/           fills the hajlibc page from data.js
│       └── report/            search boxes, filters, coverage source navigation
├── tools/                     driven by main.py
│   ├── render.py              renders src/pages/ (and reports) with the templates
│   ├── scripts.py             fetches the native tsc / esbuild, type-checks, bundles
│   ├── posix-tracker/         POSIX conformance tracker (Jinja templates;
│   │                          posix-data.toml names its reference data)
│   ├── datasets.py            fetches data sets kept outside git, checked by sha256
│   └── hajlibc/               data.js, tests, coverage and docs pages
│                              (model, inputs, lcov, docs, pages,
│                              tests_pages, coverage_pages)
├── external/                  git submodules: the projects the site reports on
│   ├── hajlibc/               github.com/openhaj/hajlibc (branch dev)
│   └── blasix/                the blåsix conformance test suite
├── .build/                    intermediate files            (not committed)
│   ├── posix-tracker/         releases extracted from git tags, scan cache
│   ├── blasix/                test run/ and coverage/ results
│   ├── datasets/              data sets (POSIX reference), fetched and checked
│   └── toolchain/             tsc and esbuild binaries
└── dist/                      the finished site             (not committed)
```

Every URL is **relative**: `dist/` works opened from disk, served locally,
or published under a sub-path such as `openhaj.github.io/sonar/`.

## Building

```sh
git submodule update --init
python3 main.py                  # full build into dist/
python3 main.py serve            # http://localhost:8000
```

The first build creates `.venv/` and installs `requirements.txt` (then
re-runs itself inside it), and downloads the TypeScript compiler and
esbuild into `.build/toolchain/`; nothing else to set up. **Node.js is not
needed**: TypeScript 7 (`tsc`) and esbuild are native binaries, fetched
from the npm registry at the exact versions pinned in `tools/scripts.py`,
each checked against its sha512. After editing the scripts,
`python3 main.py --only scripts` rebuilds the bundles.

A page that needs its own script gets an entry in `src/ts/entries/` and
loads it from its `head` block, so other pages don't download it.

| Command | |
| --- | --- |
| `python3 main.py` | full build (starts from an empty `dist/`) |
| `python3 main.py --skip tests` | everything but the slow blåsix runs (reuses the last results) |
| `python3 main.py --only static` | re-render the pages after editing `src/` |
| `python3 main.py steps` | list the steps |
| `python3 main.py clean` | remove `dist/` and `.build/`, but keep the downloaded tools and data (`--all`: those too) |

Steps, in order:

| Step | Does | Output |
| --- | --- | --- |
| `static` | renders `src/pages/` with `src/templates/`, copies `src/assets/` | `dist/` |
| `scripts` | type-checks `src/ts/` (`tsc`) and bundles each entry (`esbuild`) | `dist/assets/js/{site,hajlibc}.js` |
| `posix` | fetches the POSIX reference data, extracts every release tag (`v*`) and `HEAD` of hajlibc, scans them against POSIX.1-2024 | `dist/projects/hajlibc/posix/` |
| `tests` | runs blåsix on hajlibc: a normal run (probes) and a coverage run | `.build/blasix/` |
| `hajlibc` | reads the above and the headers' doc comments | `dist/projects/hajlibc/{data.js,tests,coverage,docs}` |

The reports, under `dist/projects/hajlibc/`:

- `tests/`: a recap (verdict on each required interface, per header, the
  failing tests, a search over every interface) and one page per header,
  grouped like blåsix's suites, with every test, its spec reference, its
  source, and why it failed (failed check, expected and actual values,
  output) or did not run (skipped, not implemented, build log of a unit
  that did not build). Statuses and verdicts are blåsix's own
  (`results.json`): nothing is recomputed, only arranged;
- `coverage/`: line, function and branch coverage per category
  (`src/<category>/`, public headers), one page per category, one per
  source file with every line marked run or not (as genhtml), and the
  lcov tracefile itself (`lcov.info`). Every file compiled into the
  library counts, run by the tests or not.

Search boxes and filters follow the URL: `tests/?q=strlen`,
`tests/string-h.html?verdict=failing`.

Nothing on the hajlibc pages is written by hand: numbers, versions, commit,
headers and documentation all come from the repository and the tools. To
follow a newer hajlibc: `git submodule update --remote external/hajlibc`
then `python3 main.py`.

Overrides: `HAJLIBC=/path/to/hajlibc`, `BLASIX=/path/to/blasix` (for
example a local working copy).

### The POSIX reference data

The tracker's POSIX.1-2024 reference (headers, symbols and their pages) is
not in git. It is an immutable archive, published as a release asset,
and described by `tools/posix-tracker/posix-data.toml`: its sha256 and the
URLs it can be fetched from. The build downloads it once into
`.build/datasets/`, refuses any file whose sha256 differs, and extracts it
there. A given commit of the repository therefore always builds with exactly
the same data.

- Offline, or before the archive is published: `POSIX_DATA_ARCHIVE=/path/to/posix-2024.tar.gz python3 main.py`.
- New version of the data: build a new archive (`tools.datasets.make_archive`
  is reproducible: same files, same bytes), publish it under a new name, and
  update `sha256` and `urls` in the manifest.

Requirements: Python 3.12+, `git`, `make`, a C compiler (GCC 12 or later
for coverage), `gcov` and `gcov-tool`.

All the Python is typed and checked in strict mode (`pyrightconfig.json`,
with `type: ignore` comments disabled): run `pyright` (or `basedpyright`)
at the root. `typings/` holds stubs for the part of pycparser used.

## Templates

Every page extends `src/templates/base.html` (head, navigation, waves,
footer), so the shared markup exists once. Templates get `site`, `projects`
and `STATUS` from `site.toml`, `root` (relative path to the site root) and,
under `projects/<slug>/`, that `project`.

A project page only holds what is specific to it:

```jinja
{% extends "project.html" %}
{% block content %}
    <article>…</article>
{% endblock %}
```

Optional blocks: `actions` (buttons after "Source code"), `head` (extra
scripts), `main_class`. Cards come from `macros.html` (`ui.cards(...)`).

## Adding a project

1. Add a `[[projects]]` entry to `src/site.toml` (`featured = true` to show
   it on the home page): its card appears everywhere automatically.
2. Create `src/pages/projects/<slug>/index.html` extending `project.html`.

Badge statuses: `idea`, `wip`, `paused`, `stable`, `archived`.

If the project has generated reports: add it under `external/` as a
submodule, its generator under `tools/`, and a `@step` in `main.py`.
