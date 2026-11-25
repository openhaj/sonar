"""Icons of the badges: line drawings on a 16x16 grid, drawn with the
current stroke colour (no fill unless a shape says so).

Add one: a name and its SVG elements, coordinates in 0..16. Keep them
simple: a badge draws them at 12px.
"""
from __future__ import annotations

ICONS: dict[str, str] = {
    # git
    "branch": (
        '<circle cx="4.5" cy="3.5" r="1.8"/><circle cx="4.5" cy="12.5" r="1.8"/>'
        '<circle cx="11.5" cy="4.5" r="1.8"/>'
        '<path d="M4.5 5.3v5.4M11.5 6.3c0 3.6-7 2.4-7 4.4"/>'
    ),
    "tag": (
        '<path d="M2 2.6v4.6c0 .4.2.8.5 1.1l5.6 5.6a1.2 1.2 0 0 0 1.7 0l4.1-4.1a1.2 1.2 0 0 0 0-1.7'
        'L8.3 2.5C8 2.2 7.6 2 7.2 2H2.6a.6.6 0 0 0-.6.6z"/>'
        '<circle cx="5.3" cy="5.3" r="1.1" fill="currentColor"/>'
    ),
    "commit": '<circle cx="8" cy="8" r="2.8"/><path d="M1.5 8h3.7M10.8 8h3.7"/>',
    # quality
    "shield": (
        '<path d="M8 1.6 13.4 3.5v4.1c0 3.2-2.2 5.7-5.4 6.8C4.8 13.3 2.6 10.8 2.6 7.6V3.5z"/>'
        '<path d="m5.6 8 1.7 1.7 3.2-3.4"/>'
    ),
    "flask": (
        '<path d="M6 1.8h4M6.8 1.8v4.3L2.9 12.4a1.3 1.3 0 0 0 1.1 2h8a1.3 1.3 0 0 0 1.1-2L9.2 6.1V1.8"/>'
        '<path d="M4.6 10.2h6.8"/>'
    ),
    "target": (
        '<circle cx="8" cy="8" r="6.2"/><circle cx="8" cy="8" r="3.4"/>'
        '<circle cx="8" cy="8" r="0.9" fill="currentColor"/>'
    ),
    "check": '<circle cx="8" cy="8" r="6.2"/><path d="m5.3 8.2 1.9 1.9 3.6-3.9"/>',
    "cross": '<circle cx="8" cy="8" r="6.2"/><path d="m5.8 5.8 4.4 4.4m0-4.4-4.4 4.4"/>',
    "gauge": '<path d="M2.3 11.5a6 6 0 1 1 11.4 0"/><path d="m8 9.5 2.6-3.6"/><circle cx="8" cy="9.6" r="1"/>',
    # misc
    "book": '<path d="M2 3.2c2-.9 4.1-.9 6 .4 1.9-1.3 4-1.3 6-.4v9.6c-2-.9-4.1-.9-6 .4-1.9-1.3-4-1.3-6-.4zM8 3.6v9.6"/>',
    "package": '<path d="M8 1.8 13.6 4.8v6.4L8 14.2 2.4 11.2V4.8zM2.4 4.8 8 7.8l5.6-3M8 7.8v6.4"/>',
    "terminal": '<rect x="1.8" y="2.6" width="12.4" height="10.8" rx="1.8"/><path d="m4.6 6.2 2 1.8-2 1.8M8.4 10h3"/>',
    "scale": '<path d="M8 2v12M4.5 14h7M3 4.5h10M3 4.5 1.2 9a2 2 0 0 0 3.6 0zM13 4.5 11.2 9a2 2 0 0 0 3.6 0z"/>',
    "heart": '<path d="M8 13.6S2 10.2 2 5.9A3.1 3.1 0 0 1 8 4.4a3.1 3.1 0 0 1 6 1.5c0 4.3-6 7.7-6 7.7z"/>',
    "clock": '<circle cx="8" cy="8" r="6.2"/><path d="M8 4.6V8l2.4 1.5"/>',
}


def icon(name: str) -> str:
    if name not in ICONS:
        raise KeyError(f"no icon '{name}' (known: {', '.join(sorted(ICONS))})")
    return ICONS[name]
