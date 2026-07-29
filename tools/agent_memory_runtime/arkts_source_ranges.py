# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .ecma_callable_ranges import (
    callback_arrow_line,
    callable_ranges_for_language,
    dedupe_ranges,
    member_callback_ranges,
)


def arkts_line_ranges(lines: list[str]) -> list[dict[str, Any]]:
    """Return named, property, and ArkUI member callback ranges."""
    return callable_ranges_for_language(lines, "ArkTS")


def dsl_callback_ranges(lines: list[str]) -> list[dict[str, Any]]:
    return member_callback_ranges(lines)
