"""The POSIX.1-2024 reference (data/posix/), indexed by name and by header."""
from __future__ import annotations

import json
from typing import Any, cast

from app.model import HeaderMeta, SymbolInfo
from config import CATEGORIES, POSIX_DIR

# {header: {category: {name: SymbolInfo}}}
ByHeader = dict[str, dict[str, dict[str, SymbolInfo]]]


def _load(name: str) -> dict[str, Any]:
    """A JSON file of data/posix/ (raw: validated by the code that reads it)."""
    path = POSIX_DIR / name
    if not path.exists():
        return {}
    data: dict[str, Any] = json.loads(path.read_text("utf-8"))
    return data


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [v for v in cast("list[Any]", value) if isinstance(v, str)]


def _empty_categories() -> dict[str, dict[str, SymbolInfo]]:
    return {c: {} for c in CATEGORIES}


class PosixReference:
    def __init__(self) -> None:
        headers_data = _load("release_headers.json")
        docs: dict[str, Any] = _load("release_full.json").get("symbol_docs", {})

        self.by_name: dict[str, SymbolInfo] = {}
        self.by_header: ByHeader = {}
        self.headers: dict[str, HeaderMeta] = {}

        headers: dict[str, Any] = headers_data.get("headers", {})
        for header, meta in headers.items():
            self.headers[header] = {"name": _text(meta.get("name")) or header, "url": _text(meta.get("url"))}
            self.by_header[header] = _empty_categories()

        symbols: dict[str, Any] = headers_data.get("symbols", {})
        for key, sym in symbols.items():
            category, name, header = _text(sym.get("category")), _text(sym.get("name")), _text(sym.get("header"))
            if not name or category not in CATEGORIES:
                continue
            doc: dict[str, Any] = docs.get(key, {})
            info: SymbolInfo = {
                "name": name,
                "category": category,
                "header": header,
                "url": _text(sym.get("url")),
                "synopsis": _text(doc.get("synopsis")),
                "description": _text(doc.get("description")),
                "return_value": _text(doc.get("return_value")),
                "errors": _strings(doc.get("errors")),
                "examples": _strings(doc.get("examples")),
                "see_also": _strings(doc.get("see_also")),
                "application_usage": _text(doc.get("application_usage")),
                "rationale": _text(doc.get("rationale")),
                "future_directions": _text(doc.get("future_directions")),
                "change_history": _text(doc.get("change_history")),
            }
            self.by_name.setdefault(name, info)  # a name may be in two categories: first wins
            if header:
                self.by_header.setdefault(header, _empty_categories())[category][name] = info


POSIX = PosixReference()
POSIX_BY_NAME = POSIX.by_name
POSIX_BY_HEADER = POSIX.by_header
POSIX_HEADERS = POSIX.headers
