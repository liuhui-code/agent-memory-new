# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from .query_candidate_recall import recall_focus_terms
from .text import unique_list, weighted_token_matches


def score_query_focus_coverage(
    query: str,
    candidate_text: str,
    score: float,
    reasons: list[str],
) -> tuple[float, list[str]]:
    """Reward candidates that cover several specific concepts in the request."""
    focus_terms = recall_focus_terms(query)
    if not focus_terms:
        return score, reasons
    lowered = candidate_text.casefold()
    matched = [
        term for term in focus_terms
        if weighted_token_matches(term, lowered)
    ]
    if not matched:
        return score, reasons
    coverage = len(matched) / len(focus_terms)
    score += len(matched) * 8.0 + coverage * 12.0
    reasons = [*reasons, "query_focus_coverage"]
    if len(matched) >= 2:
        score += 8.0
        reasons.append("multi_concept_coverage")
    return score, unique_list(reasons)
