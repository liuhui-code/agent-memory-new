# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any, Callable

from .performance_scoring import estimate_payload_tokens


MINIMAL_GUARD_FIELDS = (
    "id", "reflection_id", "semantic_id", "experience_type", "fact", "scope",
    "task", "trigger_condition", "status", "warnings",
)
MIN_FINAL_EXCERPT_CHARS = 64


def bounded_log_evidence(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or not items:
        return []
    if len(items) <= limit:
        return items
    emitter = next(
        (item for item in items if item.get("evidence_class") == "direct"),
        None,
    )
    if emitter is None:
        return items[:limit]
    log_id = emitter.get("log_id")
    linked = [
        item for item in items
        if item is not emitter and log_id is not None and item.get("log_id") == log_id
    ]
    remaining = [item for item in items if item is not emitter and item not in linked]
    return [emitter, *linked, *remaining][:limit]


def enforce_budget(
    payload: dict[str, Any],
    token_budget: int,
    reserve_tokens: int = 60,
) -> None:
    handoff = payload["query_handoff"]
    paths = handoff["path_context"]["path_candidates"]
    reductions: tuple[Callable[[], Any], ...] = (
        lambda: handoff.__setitem__("relation_hints", handoff["relation_hints"][:2]),
        lambda: [path.__setitem__("expected_logs", path["expected_logs"][:2]) for path in paths],
        lambda: [path.__setitem__("uncertainty", path.get("uncertainty", [])[:1]) for path in paths],
        lambda: handoff.__setitem__("code_anchors", handoff["code_anchors"][:3]),
        lambda: handoff.__setitem__("log_keywords", handoff["log_keywords"][:8]),
        lambda: handoff.__setitem__("experience_refs", handoff["experience_refs"][:1]),
        lambda: handoff.__setitem__("semantic_refs", handoff["semantic_refs"][:1]),
        lambda: handoff.__setitem__("callable_evidence", {}),
        lambda: handoff["path_context"].__setitem__("path_candidates", paths[:2]),
        lambda: payload.__setitem__("blocked_memory_notes", payload["blocked_memory_notes"][:1]),
        lambda: payload.__setitem__("conflict_notes", payload["conflict_notes"][:1]),
        lambda: minimize_guards(payload),
        lambda: payload.__setitem__("blocked_memory_notes", []),
        lambda: trim_excerpt_for_path_diversity(handoff),
        lambda: compress_primary_path_duplicates(handoff),
        lambda: compress_alternate_path_branches(handoff),
        lambda: handoff["path_context"].__setitem__("path_candidates", paths[:1]),
        lambda: hard_trim(payload),
    )
    for reduce_payload in reductions:
        if estimate_payload_tokens(payload) <= token_budget - reserve_tokens:
            break
        reduce_payload()


def finalize_budget(payload: dict[str, Any], token_budget: int) -> None:
    payload["output_budget"] = {
        "estimated_tokens": 0,
        "target_tokens": token_budget,
        "truncated": True,
    }
    for _ in range(80):
        synchronize_estimate(payload)
        if estimate_payload_tokens(payload) <= token_budget:
            return
        if not reduce_final_payload(payload):
            break
    synchronize_estimate(payload)


def synchronize_estimate(payload: dict[str, Any]) -> None:
    budget = payload["output_budget"]
    for _ in range(3):
        estimate = estimate_payload_tokens(payload)
        if budget.get("estimated_tokens") == estimate:
            break
        budget["estimated_tokens"] = estimate


def reduce_final_payload(payload: dict[str, Any]) -> bool:
    handoff = payload["query_handoff"]
    if handoff.get("next_queries"):
        handoff["next_queries"] = []
        return True
    if payload.pop("expansion", None) is not None:
        return True
    excerpt = longest_excerpt(handoff, owner=False) or longest_excerpt(handoff, owner=True)
    if excerpt and trim_excerpt(excerpt):
        update_excerpt_policy(handoff)
        return True
    for key in ("relation_hints", "semantic_refs", "experience_refs"):
        if handoff.get(key):
            handoff[key] = handoff[key][:-1]
            return True
    if len(handoff.get("log_keywords", [])) > 4:
        handoff["log_keywords"] = handoff["log_keywords"][:-1]
        return True
    for anchor in reversed(handoff.get("code_anchors", [])):
        if anchor.pop("summary", None) is not None:
            return True
    query = str(payload.get("query") or "")
    if len(query) > 100:
        payload["query"] = query[: max(100, len(query) - 80)]
        return True
    if reduce_redundant_source_metadata(handoff):
        return True
    return reduce_empty_or_optional_groups(payload)


def longest_excerpt(handoff: dict[str, Any], owner: bool) -> dict[str, Any] | None:
    excerpts = [
        excerpt
        for anchor in handoff.get("code_anchors", [])
        for excerpt in anchor.get("source_excerpts", [])
        if isinstance(excerpt, dict)
        and (excerpt.get("selection_reason") == "selected_log_event_owner") is owner
    ]
    return max(excerpts, key=lambda item: len(str(item.get("content") or "")), default=None)


def trim_excerpt(excerpt: dict[str, Any]) -> bool:
    content = str(excerpt.get("content") or "")
    if len(content) <= MIN_FINAL_EXCERPT_CHARS:
        return False
    target = max(MIN_FINAL_EXCERPT_CHARS, len(content) - 240)
    lines = content.splitlines()
    focus = excerpt.get("focus_line")
    start = excerpt.get("start_line")
    focus_index = int(focus) - int(start) if isinstance(focus, int) and isinstance(start, int) else 0
    focus_index = min(max(0, focus_index), max(0, len(lines) - 1))
    selected = [lines[focus_index]] if lines else []
    left, right = focus_index - 1, focus_index + 1
    while (left >= 0 or right < len(lines)) and len("\n".join(selected)) < target:
        if left >= 0:
            selected.insert(0, lines[left])
            left -= 1
        if right < len(lines) and len("\n".join(selected)) < target:
            selected.append(lines[right])
            right += 1
    excerpt["content"] = "\n".join(selected)[:target]
    excerpt["start_line"] = int(start or 1) + left + 1
    excerpt["end_line"] = excerpt["start_line"] + max(0, len(selected) - 1)
    excerpt["truncated"] = True
    return True


def reduce_empty_or_optional_groups(payload: dict[str, Any]) -> bool:
    for key in ("blocked_memory_notes", "conflict_notes", "semantic_patch_notes"):
        if payload.get(key):
            payload[key] = payload[key][:-1]
            return True
    freshness = payload.get("source_freshness")
    if isinstance(freshness, dict) and freshness:
        payload["source_freshness"] = {}
        return True
    return False


def reduce_redundant_source_metadata(handoff: dict[str, Any]) -> bool:
    for anchor in handoff.get("code_anchors", []):
        excerpts = anchor.get("source_excerpts")
        if not excerpts:
            continue
        for key in ("read_window", "source_ranges"):
            if anchor.pop(key, None) is not None:
                return True
        for excerpt in excerpts:
            if not isinstance(excerpt, dict):
                continue
            for key in ("source", "symbol", "truncated"):
                if excerpt.pop(key, None) is not None:
                    return True
    return False


def trim_excerpt_for_path_diversity(handoff: dict[str, Any]) -> None:
    paths = handoff["path_context"]["path_candidates"]
    if len(paths) < 2:
        return
    emitter_files = {
        str(path.get("emitter", {}).get("file_path") or "") for path in paths[:2]
    }
    anchors = [
        anchor for anchor in reversed(handoff["code_anchors"])
        if anchor.get("source_excerpts")
        and str(anchor.get("file_path") or "") not in emitter_files
    ]
    if anchors:
        anchors[0].pop("source_excerpts", None)
        update_excerpt_policy(handoff)


def compress_primary_path_duplicates(handoff: dict[str, Any]) -> None:
    paths = handoff["path_context"]["path_candidates"]
    if not paths:
        return
    primary = paths[0]
    primary["entry"] = compact_projected_endpoint(primary.get("entry"))
    primary["emitter"] = compact_projected_endpoint(primary.get("emitter"))
    primary["relations"] = compact_projected_relations(primary.get("relations"))
    nodes = primary.get("nodes") or []
    if len(nodes) == 2 and endpoints_match_nodes(primary, nodes):
        primary.pop("nodes", None)
    log_keys = {
        log_identity(item) for item in handoff.get("log_anchors") or []
    }
    expected = primary.get("expected_logs") or []
    if expected and all(log_identity(item) in log_keys for item in expected):
        primary.pop("expected_logs", None)
    if primary.get("source_revision") == handoff["path_context"].get("graph_revision"):
        primary.pop("source_revision", None)
    if primary.get("complete") is True:
        primary.pop("complete", None)
    if primary.get("truncated") is False:
        primary.pop("truncated", None)
    primary.pop("uncertainty", None)


def compact_projected_endpoint(value: Any) -> dict[str, Any]:
    item = value if isinstance(value, dict) else {}
    return {
        key: item[key] for key in ("name", "file_path", "line", "category")
        if item.get(key) not in (None, "", [], {})
    }


def compact_projected_relations(value: Any) -> list[dict[str, str]]:
    items = value if isinstance(value, list) else []
    return [
        {"relation": str(item["relation"])}
        for item in items if isinstance(item, dict) and item.get("relation")
    ][:5]


def endpoints_match_nodes(path: dict[str, Any], nodes: list[dict[str, Any]]) -> bool:
    return (
        endpoint_identity(path.get("entry")) == endpoint_identity(nodes[0])
        and endpoint_identity(path.get("emitter")) == endpoint_identity(nodes[-1])
    )


def endpoint_identity(value: Any) -> tuple[str, str]:
    item = value if isinstance(value, dict) else {}
    return str(item.get("file_path") or ""), str(item.get("name") or "")


def log_identity(value: Any) -> tuple[str, str, int]:
    item = value if isinstance(value, dict) else {}
    return (
        str(item.get("message_template") or ""),
        str(item.get("function") or ""),
        int(item.get("line") or 0),
    )


def compress_alternate_path_branches(handoff: dict[str, Any]) -> None:
    paths = handoff["path_context"]["path_candidates"]
    if len(paths) < 2:
        return
    alternate = paths[1]
    entry = compact_projected_endpoint(alternate.get("entry"))
    relations = compact_projected_relations(alternate.get("relations"))[:2]
    paths[1:] = [{
        key: value for key, value in {
            "path_id": alternate.get("path_id"),
            "entry": entry,
            "relations": relations,
            "projection": "alternate_entry",
        }.items() if value not in (None, "", [], {})
    }]


def update_excerpt_policy(handoff: dict[str, Any]) -> None:
    excerpts = [
        excerpt for anchor in handoff["code_anchors"]
        for excerpt in anchor.get("source_excerpts") or []
    ]
    policy = handoff.get("source_excerpt_policy")
    if isinstance(policy, dict):
        policy["excerpt_count"] = len(excerpts)
        policy["excerpt_chars"] = sum(len(str(item.get("content") or "")) for item in excerpts)


def minimize_guards(payload: dict[str, Any]) -> None:
    keys = ("correction_guards", "semantic_patch_notes", "blocked_memory_notes", "conflict_notes")
    for key in keys:
        payload[key] = [clean_record(item, MINIMAL_GUARD_FIELDS) for item in payload[key]]


def hard_trim(payload: dict[str, Any]) -> None:
    handoff = payload["query_handoff"]
    handoff["log_keywords"] = handoff["log_keywords"][:6]
    handoff["log_anchors"] = bounded_log_evidence(handoff["log_anchors"], 2)
    handoff["code_anchors"] = handoff["code_anchors"][:2]
    handoff["relation_hints"] = []
    handoff["experience_refs"] = []
    handoff["semantic_refs"] = []
    candidates = handoff["path_context"]["path_candidates"][:1]
    for candidate in candidates:
        if candidate.get("nodes"):
            candidate["nodes"] = candidate["nodes"][:4]
        if candidate.get("relations"):
            candidate["relations"] = candidate["relations"][:3]
        if candidate.get("expected_logs"):
            candidate["expected_logs"] = candidate["expected_logs"][:1]
        candidate["uncertainty"] = candidate.get("uncertainty", [])[:1]
    handoff["path_context"]["path_candidates"] = candidates
    payload["correction_guards"] = shrink_guard_group(payload["correction_guards"])
    payload["semantic_patch_notes"] = shrink_guard_group(payload["semantic_patch_notes"])
    payload["blocked_memory_notes"] = []
    payload["conflict_notes"] = shrink_guard_group(payload["conflict_notes"])


def shrink_guard_group(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return []
    item = items[0]
    keys = ("id", "reflection_id", "semantic_id", "experience_type", "fact", "scope", "task", "status")
    result = {
        key: str(item[key])[:100] if isinstance(item.get(key), str) else item[key]
        for key in keys if item.get(key) not in (None, "")
    }
    warnings = item.get("warnings")
    if isinstance(warnings, list) and warnings:
        result["warnings"] = [str(warnings[0])[:100]]
    return [result]


def clean_record(item: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {key: item[key] for key in fields if item.get(key) not in (None, "", [], {})}
