import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE_ROOT = ROOT.parent.parent          # the sonar repository

# The libc under test: a git repository whose release tags (v*) and current
# HEAD ("dev") are extracted into data/sources/ by `run.py sync`.
HAJLIBC_REPO = Path(os.environ.get("HAJLIBC", SITE_ROOT / "external" / "hajlibc")).resolve()
TAG_PATTERN  = "v*"
DEV_NAME     = "dev"

# POSIX.1-2024 reference data: an archive kept outside git (posix-data.toml),
# extracted by main.py, which sets TRACKER_POSIX_DIR.
POSIX_DIR     = Path(os.environ.get("TRACKER_POSIX_DIR", ROOT / "data" / "posix")).resolve()

TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR    = ROOT / "static"

# Work files (extracted releases, scan cache) and output: set by main.py,
# defaults keep the tool usable on its own.
WORK_DIR      = Path(os.environ.get("TRACKER_WORK", SITE_ROOT / ".build" / "posix-tracker")).resolve()
SOURCES_DIR   = WORK_DIR / "sources"
CACHE_DIR     = WORK_DIR / "cache"
OUTPUT_DIR    = Path(os.environ.get("TRACKER_OUT", SITE_ROOT / "dist" / "projects" / "hajlibc" / "posix")).resolve()

POSIX_BASE = "https://pubs.opengroup.org/onlinepubs/9799919799"

CATEGORIES = (
    "functions",
    "types",
    "constants",
    "macros",
    "structs",
)

CATEGORY_LABELS = {
    "functions":            "Functions",
    "types":                "Types",
    "constants":            "Constants",
    "macros":               "Macros",
    "structs":              "Structs",
}

WEIGHTS: dict[str, float] = {
    "functions":            10.0,
    "structs":               3.0,
    "types":                 2.0,
    "constants":             1.0,
    "macros":                2.0,
}
