"""Petits helpers partagés."""
from __future__ import annotations

import re
from pathlib import Path


def slug(name: str) -> str:
    """`sys/socket.h` -> `sys_socket.h` ; `aio_cancel` -> `aio_cancel`."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name.replace("/", "_"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def truncate(text: str, n: int) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "…"
