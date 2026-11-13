# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Identity admission for opaque event requests, before graph expansion."""
from __future__ import annotations

from typing import Any
from .log_event_identity import PLACEHOLDER_RE
from .query_code_selection import OPAQUE_IDENTIFIER_RE


def admits_opaque_log(item: dict[str, Any], query: str) -> bool:
    identifiers = {x.casefold() for x in OPAQUE_IDENTIFIER_RE.findall(query)}
    if not identifiers:
        return True
    template = str(item.get('message_template') or '')
    literals = PLACEHOLDER_RE.split(template)
    literal_ids = {x.casefold() for part in literals for x in OPAQUE_IDENTIFIER_RE.findall(part)}
    if identifiers & literal_ids:
        return True
    if len(literals) == 1 or not any(part.strip() for part in literals):
        return False
    return template_contains_identity(literals, query, identifiers)


def template_contains_identity(parts: list[str], query: str, identifiers: set[str]) -> bool:
    """Ordered source literals must surround a requested identity in a value gap.

    Uses bounded string searches rather than a generated wildcard regular
    expression. Literal punctuation is significant; no inferred value binding.
    """
    text = query.casefold()
    parts = [part.casefold() for part in parts]
    for match in OPAQUE_IDENTIFIER_RE.finditer(text):
        if match.group() not in identifiers:
            continue
        for gap in range(1, len(parts)):
            if ordered_literals(parts[:gap], text[:match.start()]) and ordered_literals(
                parts[gap:], text[match.end():]
            ):
                return True
    return False


def ordered_literals(parts: list[str], text: str) -> bool:
    cursor = 0
    for part in parts:
        offset = text.find(part, cursor)
        if offset < 0:
            return False
        cursor = offset + len(part)
    return True


def compatible_opaque_template(item: dict[str, Any], query: str) -> bool:
    """Possible literal/value-gap compatibility, never a proven event binding."""
    identifiers = {value.casefold() for value in OPAQUE_IDENTIFIER_RE.findall(query)}
    parts = PLACEHOLDER_RE.split(str(item.get('message_template') or ''))
    return bool(identifiers and len(parts) > 1 and any(part.strip() for part in parts)
                and template_contains_identity(parts, query, identifiers))
