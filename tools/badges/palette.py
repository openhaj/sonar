"""Colours of the badges, taken from the site's palette (style.css).

A colour is a name from COLORS or any "#rrggbb". `scale(percent)` gives the
colour of a score, from red (0) through amber to green (100).
"""
from __future__ import annotations

COLORS: dict[str, str] = {
    "ink":    "#1b2e4b",     # label side
    "blue":   "#3f78b8",     # haj-blue, a little deeper for white text
    "violet": "#6b5cc4",
    "green":  "#2f9a5a",
    "red":    "#d0473b",
    "amber":  "#d39a1c",
    "orange": "#dd7330",
    "lime":   "#7fa53a",
    "slate":  "#6b7f99",     # neutral: skipped, unknown
}

# score -> colour, interpolated between the stops
SCALE: list[tuple[float, str]] = [
    (0, "#c8463e"), (25, "#dd7330"), (50, "#d39a1c"), (75, "#7fa53a"), (90, "#2f9a5a"), (100, "#24845a"),
]


def resolve(color: str) -> str:
    """A COLORS name or a "#rrggbb" literal, as "#rrggbb"."""
    value = COLORS.get(color, color)
    if not (value.startswith("#") and len(value) == 7):
        raise ValueError(f"colour '{color}' is neither #rrggbb nor one of {', '.join(COLORS)}")
    int(value[1:], 16)
    return value.lower()


def _rgb(color: str) -> tuple[int, int, int]:
    c = resolve(color)
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def _hex(r: float, g: float, b: float) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in (r, g, b))


def mix(a: str, b: str, t: float) -> str:
    """`a` moved towards `b` by t (0..1)."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex(*(x + (y - x) * t for x, y in zip(ra, rb)))


def lighten(color: str, t: float) -> str:
    return mix(color, "#ffffff", t)


def darken(color: str, t: float) -> str:
    return mix(color, "#000000", t)


def luminance(color: str) -> float:
    """Relative luminance (WCAG)."""
    def channel(v: int) -> float:
        s = v / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in _rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def text_on(color: str) -> str:
    """White or near-black text, whichever reads best on `color`."""
    return "#ffffff" if 1.05 / (luminance(color) + 0.05) >= 2.9 else "#1f1a10"


def scale(percent: float) -> str:
    p = max(0.0, min(100.0, percent))
    for (p0, c0), (p1, c1) in zip(SCALE, SCALE[1:]):
        if p <= p1:
            return mix(c0, c1, (p - p0) / (p1 - p0) if p1 > p0 else 0)
    return SCALE[-1][1]
