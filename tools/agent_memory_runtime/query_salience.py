# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re

from .text import ENGLISH_QUERY_STOPWORDS, identifier_tokens, tokenize, unique_list


DIAGNOSTIC_MARKERS = {
    "abort", "crash", "denied", "errno", "error", "exception", "fail",
    "failed", "failure", "fatal", "panic", "timeout", "unavailable",
}
MAX_SALIENT_TERMS = 12
GENERIC_TAIL_TERMS = {"control", "controls", "locate", "which"}


def salient_query_tokens(query: str) -> list[str]:
    """Select explicit literals and diagnostic neighborhoods without ranking them."""
    values: list[str] = []
    for literal in re.findall(r"`([^`\n]{2,240})`", query):
        values.extend(tokenize(literal))
        values.extend(identifier_tokens(literal))
    raw = tokenize(query)
    tail = [
        token for token in raw
        if token not in ENGLISH_QUERY_STOPWORDS
        and token not in GENERIC_TAIL_TERMS
        and len(token) > 2
    ][-6:]
    values.extend(tail)
    for index, token in enumerate(raw):
        if token not in DIAGNOSTIC_MARKERS:
            continue
        values.extend(raw[max(0, index - 2):index + 3])
    values.extend(
        match.group(0).casefold()
        for match in re.finditer(
            r"\b(?:[A-Za-z_][A-Za-z0-9_]*[/.:_-])+[A-Za-z0-9_./:-]+\b",
            query,
        )
    )
    return unique_list([
        value for value in values
        if len(value) > 1 and value not in {"reports", "runtime", "inspection"}
    ])[:MAX_SALIENT_TERMS]
