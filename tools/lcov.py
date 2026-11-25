"""Reader of lcov tracefiles (the `.info` files of lcov, genhtml, gcovr ...).

Only the records coverage reports need: SF (source file), FN / FNDA
(functions and their calls), BRDA (branches), DA (lines). Several records of
the same file (a header compiled into several objects) are added up, as
`lcov -a` does. The summary lines (LF, LH, FNF, ...) are recomputed from the
data rather than trusted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SourceRecord:
    """Coverage of one source file."""
    path: str
    lines: dict[int, int] = field(default_factory=lambda: {})              # line -> hits
    functions: dict[str, tuple[int, int]] = field(default_factory=lambda: {})  # name -> (line, calls)
    # (line, block, branch) -> times taken, None when the branch was never reached
    branches: dict[tuple[int, int, int], int | None] = field(default_factory=lambda: {})

    def add_function(self, name: str, line: int | None = None, calls: int = 0) -> None:
        old_line, old_calls = self.functions.get(name, (0, 0))
        self.functions[name] = (line if line is not None and not old_line else old_line, old_calls + calls)

    def add_branch(self, key: tuple[int, int, int], taken: int | None) -> None:
        old = self.branches.get(key)
        self.branches[key] = taken if old is None else old + (taken or 0)


def _int(text: str) -> int:
    try:
        return int(text)
    except ValueError:
        return 0


def parse(path: Path) -> dict[str, SourceRecord]:
    """Every source file of the tracefile at `path`, by its SF path."""
    records: dict[str, SourceRecord] = {}
    cur: SourceRecord | None = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        tag, _, value = raw.strip().partition(":")
        if tag == "SF":
            cur = records.setdefault(value, SourceRecord(value))
        elif cur is None:
            continue
        elif tag == "end_of_record":
            cur = None
        elif tag == "DA":
            parts = value.split(",")
            if len(parts) >= 2:
                line = _int(parts[0])
                cur.lines[line] = cur.lines.get(line, 0) + _int(parts[1])
        elif tag == "FN":
            parts = value.split(",")
            if len(parts) >= 2:                      # FN:<line>,<name> (lcov 2: FN:<line>,<end>,<name>)
                cur.add_function(parts[-1], line=_int(parts[0]))
        elif tag == "FNDA":
            calls, _, name = value.partition(",")
            cur.add_function(name, calls=_int(calls))
        elif tag == "BRDA":
            parts = value.split(",")
            if len(parts) >= 4:
                key = (_int(parts[0]), _int(parts[1]), _int(parts[2]))
                cur.add_branch(key, None if parts[3] == "-" else _int(parts[3]))
    return records


def relocate(path: Path, root: Path, out: Path) -> None:
    """Copy the tracefile at `path` to `out` with the SF paths under `root`
    made relative to it (a published tracefile names no local directory)."""
    prefix = f"SF:{root.resolve()}/"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(("SF:" + line.removeprefix(prefix) if line.startswith(prefix) else line) + "\n"
                           for line in lines), encoding="utf-8")
