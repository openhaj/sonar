"""Drawing of one badge as a standalone SVG.

    ┌──────────────────┬╱─────────┬╱──────────┐
    │ (icon) LABEL     ╱  value  ╱  value 2   │   segments, cut on a slant
    └─────────────────╱─────────╱━━━━━━━━─────┘   optional progress bar

The label side is dark ink with the icon tinted like the first value; each
value segment has its own colour, flat (no gloss, no shadow). Text widths are estimated from Verdana's
metrics and pinned with `textLength`, so the badge looks the same whatever
font the viewer has (as shields.io does).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape

from . import palette
from .icons import icon as icon_svg

H = 22          # height
R = 6           # corner radius
SLANT = 6       # horizontal run of the cut between two parts
PAD = 8         # space around a text
ICON = 12       # icon size
GAP = 5         # icon -> label

FONT = "Verdana,'DejaVu Sans',Geneva,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"

# Verdana advance widths, per 1000 units of font size (ASCII 32..126).
_VERDANA = [
    352, 394, 459, 818, 636, 1076, 727, 269, 454, 454, 636, 818, 364, 454, 364, 454,      # space .. /
    636, 636, 636, 636, 636, 636, 636, 636, 636, 636, 454, 454, 818, 818, 818, 545,       # 0 .. ?
    1000, 684, 686, 698, 771, 632, 575, 775, 751, 421, 455, 693, 557, 843, 748, 787,      # @ .. O
    603, 787, 695, 684, 616, 732, 684, 989, 685, 615, 685, 454, 454, 454, 818, 636,       # P .. _
    636, 601, 623, 521, 623, 596, 352, 623, 633, 274, 344, 592, 274, 973, 633, 607,       # ` .. o
    623, 623, 427, 521, 394, 633, 592, 818, 592, 592, 525, 635, 454, 635, 818,            # p .. ~
]


def text_width(text: str, size: float, bold: bool = False, mono: bool = False, spacing: float = 0) -> float:
    """Estimated width in px (a little generous: a too short textLength
    would squeeze the glyphs together)."""
    if mono:
        w = 0.602 * size * len(text)
    else:
        units = sum(_VERDANA[ord(c) - 32] if 32 <= ord(c) <= 126 else 700 for c in text)
        w = units * size / 1000 * (1.09 if bold else 1.0)
    return w * 1.02 + spacing * max(0, len(text) - 1)


@dataclass(frozen=True)
class Segment:
    """One value of the badge, on its own colour."""
    text: str
    color: str                       # palette name or #rrggbb
    mono: bool = False               # monospaced (commit hashes)


@dataclass(frozen=True)
class Badge:
    label: str
    segments: tuple[Segment, ...]
    icon: str | None = None
    progress: float | None = None    # 0..1: bar under the values
    title: str | None = None         # tooltip / accessible name (default: label + values)
    caps: bool = True                # label in small capitals
    label_color: str = "ink"
    icon_color: str | None = None    # default: a light tint of the first value's colour
    extra: dict[str, str] = field(default_factory=lambda: {})   # metadata, not drawn


def _text(x: float, text: str, color: str, size: float, width: float, *, bold: bool = False,
          mono: bool = False, anchor: str = "middle") -> str:
    weight = ' font-weight="bold"' if bold else ""
    attrs = (f'font-family="{MONO if mono else FONT}" font-size="{size:g}"{weight} text-anchor="{anchor}" '
             f'textLength="{width:.1f}" lengthAdjust="spacing"')
    body = escape(text)
    baseline = 15 if size >= 10.5 else 14.6
    return (f'<text x="{x:.1f}" y="{baseline:g}" {attrs} fill="{color}">{body}</text>')


def _slab(a: float, b: float, fill: str) -> str:
    """The part between the cuts at a and b (a cut is centred on its x)."""
    s = SLANT / 2
    return f'<path d="M{a + s:.1f} 0H{b + s:.1f}L{b - s:.1f} {H}H{a - s:.1f}z" fill="{fill}"/>'


def render(badge: Badge, uid: str = "b") -> str:
    """The badge as an SVG document; `uid` prefixes its ids (several
    badges inlined in one page must not share them)."""
    if not badge.segments:
        raise ValueError(f"badge '{badge.label}': no value")
    label = badge.label.upper() if badge.caps else badge.label
    lsize, lbold, lspacing = (9.5, True, 0.6) if badge.caps else (11, False, 0)
    lw = text_width(label, lsize, bold=lbold, spacing=lspacing) if label else 0

    # x of each cut: label | value 1 | value 2 ...
    x = PAD + ((ICON + (GAP if label else 0)) if badge.icon else 0)
    label_x = x
    cuts = [x + lw + PAD]
    for seg in badge.segments:
        cuts.append(cuts[-1] + PAD + text_width(seg.text, 11, mono=seg.mono) + PAD)
    width = round(cuts[-1])

    ink = palette.resolve(badge.label_color)
    first = palette.resolve(badge.segments[0].color)
    tint = palette.resolve(badge.icon_color) if badge.icon_color else palette.mix(first, "#ffffff", 0.5)
    title = badge.title or f"{badge.label}: {' · '.join(s.text for s in badge.segments)}"

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{H}" viewBox="0 0 {width} {H}" '
        f'role="img" aria-label="{escape(title)}">',
        f"<title>{escape(title)}</title>",
        "<defs>",
        f'<clipPath id="{uid}-round"><rect width="{width}" height="{H}" rx="{R}"/></clipPath>',
        "</defs>",
        f'<g clip-path="url(#{uid}-round)">',
        f'<rect width="{width}" height="{H}" fill="{ink}"/>',
    ]
    for i, seg in enumerate(badge.segments):
        last = i == len(badge.segments) - 1
        out.append(_slab(cuts[i], cuts[i + 1] + (SLANT + 2 if last else 0), palette.resolve(seg.color)))
    if badge.progress is not None:
        p = max(0.0, min(1.0, badge.progress))
        start = cuts[0] - SLANT / 2
        span = width - start
        out.append(f'<rect x="{start:.1f}" y="{H - 3}" width="{span:.1f}" height="3" fill="#000" fill-opacity=".25"/>')
        if p > 0:
            out.append(f'<rect x="{start:.1f}" y="{H - 3}" width="{span * p:.1f}" height="3" '
                       'fill="#fff" fill-opacity=".7"/>')
    out.append("</g>")

    if badge.icon:
        scale = ICON / 16
        out.append(f'<g transform="translate({PAD} {(H - ICON) / 2:g}) scale({scale:g})" color="{tint}" '
                   f'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
                   f'stroke-linejoin="round">{icon_svg(badge.icon)}</g>')
    if label:
        out.append(_text(label_x, label, "#e8f0fa", lsize, lw, bold=lbold, anchor="start"))
    for i, seg in enumerate(badge.segments):
        mid = (cuts[i] + cuts[i + 1]) / 2
        color = palette.text_on(palette.resolve(seg.color))
        out.append(_text(mid, seg.text, color, 11, text_width(seg.text, 11, mono=seg.mono), mono=seg.mono))
    out.append("</svg>")
    return "\n".join(out) + "\n"
