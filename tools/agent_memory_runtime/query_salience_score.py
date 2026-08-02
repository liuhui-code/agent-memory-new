# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from .text import tokenize, unique_list


MAX_SALIENCE_BONUS = 18.0


def apply_salience_score(
    salient_terms: list[str],
    evidence: str,
    score: float,
    reasons: list[str],
    lane_present: bool,
) -> tuple[float, list[str], int]:
    if not lane_present or not salient_terms:
        return score, reasons, 0
    evidence_terms = set(tokenize(evidence))
    matched = [
        term for term in salient_terms
        if any(prefix_match(term, candidate) for candidate in evidence_terms)
    ]
    coverage = len(set(matched))
    if not coverage:
        return score, reasons, 0
    bonus = min(MAX_SALIENCE_BONUS, coverage * 4.0)
    return score + bonus, unique_list([*reasons, "salient_query_evidence"]), coverage


def prefix_match(left: str, right: str) -> bool:
    if min(len(left), len(right)) < 3:
        return left == right
    return left.startswith(right) or right.startswith(left)
