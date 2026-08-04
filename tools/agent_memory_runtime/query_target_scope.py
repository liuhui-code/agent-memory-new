# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any

from .query_language import positive_retrieval_query


SINGLE_TARGET_RE = re.compile(
    r"\b(?:return|locate|find|identify)\s+(?:only\b|(?:the\s+)?(?:one|single)\b)|"
    r"\b(?:return|locate|find|identify)\s+the\s+"
    r"(?:ability|class|component|controller|coordinator|implementation|method|owner|"
    r"page|policy|repository|service|source|store|view|viewmodel)\b|"
    r"只返回|唯一(?:的)?(?:源码|方法|所有者|组件|页面|服务|协调器)",
    re.IGNORECASE,
)
EXPLICIT_MULTI_TARGET_RE = re.compile(
    r"\b(?:both|owners|two|multiple)\b|"
    r"链|路径|同时|两个|两处|多个|各自",
    re.IGNORECASE,
)
CONJOINED_EVIDENCE_RE = re.compile(
    r"\b(?:return|locate|find|identify|inspect)\b[^.;\n]{0,120}\b(?:and|plus)\b|"
    r"(?:定位|查找|找到|返回|检查)[^。；\n]{0,60}(?:和|及|以及|与)",
    re.IGNORECASE,
)


def classify_target_scope(query: str) -> dict[str, Any]:
    """Classify requested evidence cardinality without inferring a diagnosis."""
    positive = positive_retrieval_query(query)
    if EXPLICIT_MULTI_TARGET_RE.search(positive):
        return {"kind": "multiple", "basis": ["explicit_multi_target_cue"]}
    if CONJOINED_EVIDENCE_RE.search(positive):
        return {"kind": "multiple", "basis": ["conjoined_evidence_cue"]}
    if SINGLE_TARGET_RE.search(positive):
        return {"kind": "single", "basis": ["explicit_single_target_cue"]}
    return {"kind": "unknown", "basis": ["no_explicit_target_scope"]}


def permits_cross_file_portfolio(scope: dict[str, Any]) -> bool:
    return (
        scope.get("kind") == "multiple"
        and "explicit_multi_target_cue" in set(scope.get("basis") or [])
    )
