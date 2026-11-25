"""Ready-made badges, from plain values: what src/badges.toml's kinds draw,
and usable as they are from Python:

    from tools.badges import kinds, svg
    svg.render(kinds.coverage(87.5))
"""
from __future__ import annotations

from . import palette
from .svg import Badge, Segment


def _pct(value: float, decimals: int) -> str:
    text = f"{value:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text + "%"


def static(label: str, value: str, color: str = "blue", icon: str | None = None) -> Badge:
    return Badge(label, (Segment(value, color),), icon=icon)


def percent(label: str, value: float, icon: str | None = "gauge", decimals: int = 1,
            color: str | None = None, bar: bool = True) -> Badge:
    """A score out of 100, coloured from red to green, with its progress bar."""
    return Badge(label, (Segment(_pct(value, decimals), color or palette.scale(value)),), icon=icon,
                 progress=value / 100 if bar else None)


def coverage(value: float, metric: str = "lines", label: str = "coverage", icon: str = "target",
             decimals: int = 1) -> Badge:
    b = percent(label, value, icon=icon, decimals=decimals)
    return Badge(b.label, b.segments, icon=b.icon, progress=b.progress,
                 title=f"{label}: {_pct(value, decimals)} of {metric}")


def tests(passed: int, failed: int, skipped: int = 0, label: str = "tests", icon: str = "flask") -> Badge:
    """Passed / failed / skipped, each on its colour; zero counts are left out."""
    total = passed + failed + skipped
    if total == 0:
        return Badge(label, (Segment("none", "slate"),), icon=icon)
    if failed == 0 and skipped == 0:
        segments = (Segment(f"all {passed} passed", "green"),)
    else:
        segments = tuple(s for s, n in ((Segment(f"{passed} passed", "green"), passed),
                                        (Segment(f"{failed} failed", "red"), failed),
                                        (Segment(f"{skipped} skipped", "slate"), skipped)) if n)
    title = f"{label}: {passed} passed, {failed} failed, {skipped} skipped ({total})"
    return Badge(label, segments, icon=icon, progress=passed / total, title=title)


def release(tag: str, label: str = "release", color: str = "blue") -> Badge:
    return Badge(label, (Segment(tag, color),), icon="tag", title=f"{label} {tag}")


def revision(branch: str, commit: str, color: str = "violet") -> Badge:
    """Not on a release: the branch, and the commit."""
    return Badge(branch, (Segment(commit, color, mono=True),), icon="branch", caps=False,
                 title=f"branch {branch}, commit {commit}")


def unknown(label: str, icon: str | None, why: str = "not built") -> Badge:
    """When the badge's input is missing: a grey badge rather than a broken image."""
    return Badge(label, (Segment(why, "slate"),), icon=icon)
