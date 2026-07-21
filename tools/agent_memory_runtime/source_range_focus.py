# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .arkts_context_markers import extract_arkts_context_markers
from .arkts_source_ranges import arkts_line_ranges
from .arkts_ui_behavior import extract_arkts_operation_names
from .query_behavior_concepts import behavior_marker_terms
from .semantic_ecma import callable_line_ranges


MarkerExtractor = Callable[[str], list[str]]
RangeExtractor = Callable[[list[str]], list[dict[str, Any]]]

def arkts_source_mechanisms(text: str) -> list[str]:
    return [
        *extract_arkts_context_markers(text),
        *[name.casefold() for name in extract_arkts_operation_names(text)],
    ]


MARKER_EXTRACTORS: dict[str, MarkerExtractor] = {
    ".ets": arkts_source_mechanisms,
    ".ts": arkts_source_mechanisms,
}
RANGE_EXTRACTORS: dict[str, RangeExtractor] = {
    ".ets": arkts_line_ranges,
    ".ts": callable_line_ranges,
}


def mechanism_coverage(
    path: Path,
    lines: list[str],
    source_range: dict[str, Any],
    query: str,
) -> int:
    """Score only mechanisms present in both the query and source range."""
    expected = set(behavior_marker_terms(query))
    extractor = MARKER_EXTRACTORS.get(path.suffix.casefold())
    if not expected or extractor is None:
        return 0
    start = max(0, int(source_range["start_line"]) - 1)
    end = min(len(lines), int(source_range["end_line"]))
    observed = set(extractor("".join(lines[start:end])))
    return len(expected & observed)


def mechanism_callable_ranges(
    path: Path,
    lines: list[str],
    query: str,
) -> list[dict[str, Any]]:
    range_extractor = RANGE_EXTRACTORS.get(path.suffix.casefold())
    if range_extractor is None:
        return []
    ranges = range_extractor(lines)
    return [item for item in ranges if mechanism_coverage(path, lines, item, query)]
