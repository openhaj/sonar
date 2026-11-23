"""API reference extracted from the doc comments of hajlibc's headers.

Doxygen-style comments (/** ... */ with @brief, @param, @return, @note) are
paired with the declaration that follows them. The @file comment describes
the header itself; comments inside a struct body document its members and
are left with the struct.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from .model import DocEntry, HeaderDoc

DOC_COMMENT = re.compile(r"/\*\*(.*?)\*/", re.S)
TAG = re.compile(r"\s*@(\w+)\s*(.*)")

# Tags shown as a note, with this label (@note has none).
NOTE_LABELS = {"note": "", "warning": "Warning: ", "deprecated": "Deprecated: ", "todo": "To do: "}

Section = Literal["brief", "text", "param", "return", "note", "skip"]


class _Tags:
    """The parts of one doc comment."""

    def __init__(self) -> None:
        self.brief = ""
        self.text: list[str] = []
        self.params: list[tuple[str, str]] = []
        self.returns = ""
        self.notes: list[str] = []
        self.is_file = False

    def append(self, section: Section, line: str) -> None:
        """Continue `section` with one more line."""
        if section == "brief":
            self.brief += " " + line
        elif section == "param" and self.params:
            name, text = self.params[-1]
            self.params[-1] = (name, f"{text} {line}")
        elif section == "return":
            self.returns += " " + line
        elif section == "note" and self.notes:
            self.notes[-1] += " " + line
        elif section == "text":
            self.text.append(line)


def _comment_lines(body: str) -> list[str]:
    return [re.sub(r"^\s*\*\s?", "", line).rstrip() for line in body.strip("\n").splitlines()]


def _parse_comment(lines: list[str]) -> _Tags:
    tags = _Tags()
    section: Section = "text"
    for line in lines:
        m = TAG.match(line)
        if m:
            name, rest = m.group(1).lower(), m.group(2)
            if name == "brief":
                tags.brief, section = rest, "brief"
            elif name == "param":
                pm = re.match(r"(\[[^\]]*\]\s*)?(\S+)\s*(.*)", rest)
                tags.params.append((pm.group(2), pm.group(3)) if pm else (rest, ""))
                section = "param"
            elif name in ("return", "returns"):
                tags.returns, section = rest, "return"
            elif name in NOTE_LABELS:
                tags.notes.append(NOTE_LABELS[name] + rest)
                section = "note"
            elif name == "details":
                tags.text.append(rest)
                section = "text"
            else:  # @file, @Created, @Updated, @struct, ...
                tags.is_file = tags.is_file or name == "file"
                section = "skip"
        elif not line.strip():
            if section in ("brief", "skip"):
                section = "text"  # a blank line ends the brief / metadata
        else:
            tags.append(section, line.strip())
    return tags


def _next_declaration(src: str, pos: int) -> str:
    """The declaration starting at `pos`, on one line (struct bodies elided)."""
    rest = src[pos:].lstrip()
    if rest.startswith("#"):  # a macro, with its continuation lines
        parts: list[str] = []
        for line in rest.splitlines():
            parts.append(line.rstrip("\\").rstrip())
            if not line.endswith("\\"):
                break
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    depth, end = 0, len(rest)
    for i, ch in enumerate(rest[:4000]):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == ";" and depth == 0:
            end = i + 1
            break
    decl = rest[:end]
    if "{" in decl:  # struct / union / enum: keep the outline only
        head, _, tail = decl.partition("{")
        decl = head.strip() + " { … }" + tail.rpartition("}")[2]
    return re.sub(r"\s+", " ", decl).strip()


def _declared_name(decl: str) -> str:
    m = re.match(r"#\s*define\s+(\w+)", decl)
    if m:
        return m.group(1)
    m = re.match(r"(?:typedef\s+)?(?:struct|union|enum)\s+(\w+)\s*\{ … \}\s*;$", decl)
    if m:
        return m.group(1)
    m = re.search(r"(\w+)\s*\((?:[^()]|\([^()]*\))*\)\s*(?:__\w+(?:\([^)]*\))?\s*)*;?$", decl)
    if m and not decl.startswith("typedef"):
        return m.group(1)
    m = re.search(r"(\w+)\s*(?:\[[^\]]*\])?\s*;?$", decl)
    return m.group(1) if m else decl[:40]


def _blank(m: re.Match[str]) -> str:
    """Replace a match by spaces, keeping its newlines (offsets stay valid)."""
    return re.sub(r"[^\n]", " ", m.group(0))


def _brace_depth(src: str) -> list[int]:
    """Brace depth at every offset, ignoring comments, preprocessor lines and
    the `extern "C" {` wrapper (so a struct member's comment is at depth > 0)."""
    code = re.sub(r"/\*.*?\*/|//[^\n]*", _blank, src, flags=re.S)
    code = re.sub(r"#\s*if(?:def\s+__cplusplus|\s+defined\s*\(?\s*__cplusplus\s*\)?).*?#\s*endif",
                  _blank, code, flags=re.S)
    code = re.sub(r"^[ \t]*#[^\n]*", _blank, code, flags=re.M)
    depths: list[int] = []
    depth = 0
    for ch in code:
        depths.append(depth)
        depth += (ch == "{") - (ch == "}")
    return depths


def parse_header(path: Path) -> HeaderDoc:
    src = path.read_text(errors="replace")
    doc: HeaderDoc = {"brief": "", "text": "", "notes": [], "entries": []}
    depth = _brace_depth(src)
    for m in DOC_COMMENT.finditer(src):
        if depth[m.start()] > 0:
            continue  # documents a struct member
        tags = _parse_comment(_comment_lines(m.group(1)))
        if tags.is_file:
            doc["brief"], doc["text"], doc["notes"] = tags.brief, " ".join(tags.text), tags.notes
            continue
        decl = _next_declaration(src, m.end())
        if not decl or decl.startswith("/*"):
            continue
        entry: DocEntry = {
            "name": _declared_name(decl), "decl": decl, "brief": tags.brief, "text": " ".join(tags.text),
            "params": tags.params, "returns": tags.returns, "notes": tags.notes,
        }
        doc["entries"].append(entry)
    return doc


def load_docs(repo: Path) -> dict[str, HeaderDoc]:
    """{header path: its documentation}, for the public headers (not bits/)."""
    include = repo / "include"
    headers: dict[str, HeaderDoc] = {}
    for path in sorted(include.rglob("*.h")):
        name = path.relative_to(include).as_posix()
        if name.startswith("bits/"):
            continue
        doc = parse_header(path)
        if doc["entries"] or doc["brief"]:
            headers[name] = doc
    return headers
