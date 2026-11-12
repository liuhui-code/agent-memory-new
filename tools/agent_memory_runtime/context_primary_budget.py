# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Reserve already-projected callable evidence without overruling graph obligations."""
from __future__ import annotations
from typing import Any
from .query_target_scope import classify_target_scope
from .source_exploration import assign_anchor_roles


def bounded_primary_prefix(handoff: dict[str, Any], query: str, limit: int, protected_paths: frozenset[str] = frozenset()) -> list[dict[str, Any]]:
    anchors = handoff.get('code_anchors') or []
    prefix = anchors[:max(0, limit)]
    if limit <= 0 or len(anchors) <= limit:
        return prefix
    path = handoff.get('path_context') or {}
    if path.get('activated') or path.get('path_candidates'):
        return prefix
    if classify_target_scope(query).get('kind') == 'multiple':
        return prefix
    evidence = handoff.get('callable_evidence') or {}
    primary = evidence.get('primary') or {}
    if evidence.get('certainty') != 'bounded' or not isinstance(primary, dict):
        return prefix
    target = primary.get('file_path')
    bounds = primary.get('source_range')
    if not target or any(item.get('file_path') == target for item in prefix):
        return prefix
    candidate = next((item for item in anchors[limit:]
                      if item.get('file_path') == target and covers(item, bounds)), None)
    if candidate is None:
        return prefix
    # Keep existing graph edges and explicit identities. If all slots carry
    # obligations, do not pretend one callable supersedes those obligations.
    replace = next((i for i in range(len(prefix) - 1, -1, -1)
                    if not protected(prefix[i]) and prefix[i].get("file_path") not in protected_paths), None)
    if replace is None:
        return prefix
    selected = list(prefix)
    selected[replace] = candidate
    return assign_anchor_roles(selected)


def protected(anchor: dict[str, Any]) -> bool:
    return bool(anchor.get('graph_relation') or anchor.get('graph_neighbor')
                or anchor.get('identity_match') or anchor.get('log_identity_match'))


def covers(anchor: dict[str, Any], bounds: Any) -> bool:
    if not isinstance(bounds, dict):
        return False
    start, end = bounds.get('start_line'), bounds.get('end_line')
    if type(start) is not int or type(end) is not int or start <= 0 or end < start:
        return False
    windows = [anchor.get('read_window'), *(anchor.get('source_ranges') or [])]
    return any(isinstance(window, dict)
               and type(window.get('start_line')) is int
               and type(window.get('end_line')) is int
               and 0 < window['start_line'] <= start <= end <= window['end_line']
               for window in windows)


def projected_guards(handoff: dict[str, Any]) -> frozenset[str]:
    """Capture internal anchor obligations before compact presentation strips flags."""
    return frozenset(str(item['file_path']) for item in handoff.get('code_anchors') or []
                     if isinstance(item, dict) and item.get('file_path') and protected(item))
