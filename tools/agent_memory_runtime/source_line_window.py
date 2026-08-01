# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceLineWindow:
    start_line: int
    lines: list[str]


def read_source_interval(
    path: Path,
    start_line: int,
    end_line: int,
    limit: int,
) -> SourceLineWindow:
    first = max(1, start_line)
    last = max(first, min(end_line, first + max(1, limit) - 1))
    lines: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line_number < first:
                    continue
                if line_number > last:
                    break
                lines.append(line)
    except OSError:
        return SourceLineWindow(first, [])
    return SourceLineWindow(first, lines)
