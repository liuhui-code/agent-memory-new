# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Retain a verified small callable's trailing lines without removing context."""
from pathlib import Path
from typing import Any
from .source_range_focus import RANGE_EXTRACTORS


def retain_callable_tail(path: Path, original: dict[str, Any], focused: dict[str, Any],
                         lines: list[str], line_offset: int, max_lines: int) -> dict[str, Any]:
    # Parsing a clipped interval cannot certify the complete callable identity.
    extractor = RANGE_EXTRACTORS.get(path.suffix.casefold())
    if line_offset or extractor is None or not original.get('symbol'):
        return focused
    start, end = int(original['start_line']), int(original['end_line'])
    first, last = int(focused['start_line']), int(focused['end_line'])
    # Never prepend: consuming budget with earlier text could displace old lines.
    if first > start or last >= end or end - first + 1 > max_lines:
        return focused
    matches = [r for r in extractor(lines) if r.get('symbol') == original['symbol']
               and r.get('start_line') == start and r.get('end_line') == end]
    if len(matches) != 1:
        return focused
    return {**focused, 'end_line': end, 'selection_reason': 'query_window_with_callable_tail'}
