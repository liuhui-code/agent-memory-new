# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .context_anchor_selection import (
    path_context_for_log_anchors,
    path_scoped_code_anchors,
    relevant_log_anchors,
)
from .context_source_excerpt import (
    attach_source_excerpts,
    has_source_excerpt_candidate,
)
from .performance_scoring import estimate_payload_tokens
from .source_exploration import assign_anchor_roles, exploration_contract
from .text import ENGLISH_QUERY_STOPWORDS


COMPACT_TOKEN_BUDGET = 1500
SOURCE_EXCERPT_PRE_BUDGET = 1220
MAX_TEXT = 180
KEYWORD_STOPWORDS = ENGLISH_QUERY_STOPWORDS | {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "while", "can", "could",
    "should", "start", "another",
}


def compact_context(data: dict[str, Any]) -> dict[str, Any]:
    handoff = data.get("query_handoff") if isinstance(data.get("query_handoff"), dict) else {}
    compact = compact_handoff(handoff, data)
    payload = {
        "schema_version": "agent-context-compact/v1",
        "project_id": data.get("project_id"),
        "query": str(data.get("query") or "")[:240],
        "memory_intent": data.get("memory_intent_v2") or data.get("memory_intent"),
        "query_handoff": compact,
        "correction_guards": compact_records(data.get("correction_guards"), 2),
        "semantic_patch_notes": compact_records(data.get("semantic_patch_notes"), 2),
        "blocked_memory_notes": compact_records(data.get("blocked_memory_notes"), 2),
        "conflict_notes": compact_records(data.get("conflict_notes"), 2),
        "evidence_gaps": evidence_gaps(compact),
        "expansion": {
            "command": "python tools/agent_memory.py context --project . --query <focused-term> --json",
            "use_when": "inspect ranking audit, full records, or one unresolved candidate",
        },
    }
    excerpt_count = attach_source_excerpts(
        payload, data.get("project_path"), COMPACT_TOKEN_BUDGET
    )
    if not excerpt_count and has_source_excerpt_candidate(payload, data.get("project_path")):
        enforce_budget(payload, SOURCE_EXCERPT_PRE_BUDGET)
        attach_source_excerpts(payload, data.get("project_path"), COMPACT_TOKEN_BUDGET)
    enforce_budget(payload)
    payload["evidence_gaps"] = evidence_gaps(payload["query_handoff"])
    payload["output_budget"] = {
        "estimated_tokens": estimate_payload_tokens(payload),
        "target_tokens": COMPACT_TOKEN_BUDGET,
        "truncated": True,
    }
    return payload


def compact_handoff(handoff: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    path_context = compact_path_context(handoff.get("path_context"))
    log_anchors = (
        relevant_log_anchors(records(handoff.get("log_anchors")), data.get("query"))[:3]
        if path_context["activated"] else []
    )
    path_context = path_context_for_log_anchors(path_context, log_anchors)
    code_candidates = path_scoped_code_anchors(
        records(handoff.get("code_anchors")), path_context
    )
    code_anchors = assign_anchor_roles(
        diverse_code_anchors(code_candidates, path_context["activated"])
    )
    return {
        "schema_version": "agent-query-handoff-compact/v1",
        "log_keywords": compact_keywords(handoff.get("log_keywords")),
        "log_anchors": [clean_record(item, LOG_FIELDS) for item in log_anchors],
        "code_anchors": code_anchors,
        "path_context": path_context,
        "relation_hints": relevant_relations(data.get("edge_matches"), code_anchors, log_anchors),
        "experience_refs": [compact_memory_ref(item) for item in records(handoff.get("experience_refs"))[:2]],
        "semantic_refs": [compact_memory_ref(item) for item in records(handoff.get("semantic_refs"))[:2]],
        "source_exploration": exploration_contract(),
        "next_queries": (
            text_list(data.get("suggested_followup_terms"), 3, 100)
            if path_context["activated"] else []
        ),
        "role_boundary": {
            "runtime": "retrieval_and_current_graph_context_only",
            "agent_cli": "temporary_log_analysis_diagnosis_and_verification",
            "runtime_reads_temporary_logs": False,
            "runtime_selects_root_cause": False,
        },
    }


LOG_FIELDS = (
    "log_id", "message_template", "logger", "business_event", "trigger_stage",
    "process_hint", "file_path", "function", "line",
)
MEMORY_FIELDS = (
    "reflection_id", "semantic_id", "id", "experience_type", "fact", "scope", "task",
    "problem", "trigger_condition", "verification_method", "trust_level", "warnings",
)
GUARD_FIELDS = (
    "id", "reflection_id", "semantic_id", "experience_type", "fact", "scope", "task",
    "problem", "trigger_condition", "lesson", "status", "trust_level", "warnings", "reason",
)
MINIMAL_GUARD_FIELDS = (
    "id", "reflection_id", "semantic_id", "experience_type", "fact", "scope",
    "task", "trigger_condition", "status", "warnings",
)


def compact_path_context(value: Any) -> dict[str, Any]:
    path = value if isinstance(value, dict) else {}
    return {
        "activated": bool(path.get("activated")),
        "activation_reason": path.get("activation_reason"),
        "graph_revision": path.get("graph_revision"),
        "path_candidates": [compact_path(item) for item in records(path.get("path_candidates"))[:3]],
        "gaps": path.get("gaps") if isinstance(path.get("gaps"), dict) else {},
    }


def compact_path(item: dict[str, Any]) -> dict[str, Any]:
    nodes = records(item.get("nodes"))[:6]
    edges = records(item.get("edges"))[:5]
    return {
        "path_id": item.get("path_id"),
        "entry": compact_endpoint(item.get("entry")),
        "emitter": compact_endpoint(item.get("emitter")),
        "nodes": [compact_node(node) for node in nodes],
        "relations": [clean_record(edge, ("relation", "evidence_class", "confidence", "ambiguity")) for edge in edges],
        "expected_logs": [
            clean_record(log, ("message_template", "logger", "event_name", "function", "line"))
            for log in records(item.get("expected_log_anchors"))[:4]
        ],
        "structural_score": item.get("structural_score"),
        "uncertainty": text_list(item.get("uncertainty"), 2, 140),
        "missing_segments": text_list(item.get("missing_segments"), 2, 140),
        "source_revision": item.get("source_revision"),
        "complete": item.get("complete"),
        "truncated": item.get("truncated"),
    }


def compact_endpoint(value: Any) -> dict[str, Any]:
    item = value if isinstance(value, dict) else {}
    node = item.get("node") if isinstance(item.get("node"), dict) else item
    result = compact_node(node)
    if item.get("category"):
        result["category"] = item["category"]
    return result


def compact_node(item: dict[str, Any]) -> dict[str, Any]:
    span = item.get("source_span") if isinstance(item.get("source_span"), dict) else {}
    return clean_record({
        "id": item.get("id"),
        "name": item.get("qualified_name") or item.get("name"),
        "file_path": item.get("file_path"),
        "line": span.get("start_line"),
    }, ("id", "name", "file_path", "line"))


def compact_relation(item: dict[str, Any]) -> dict[str, Any]:
    return clean_record(
        item,
        ("source_type", "source_id", "relation", "target_type", "target_id", "confidence", "evidence_kind"),
    )


def compact_code_anchor(item: dict[str, Any]) -> dict[str, Any]:
    result = clean_record(
        item,
        (
            "source", "record_id", "file_path", "symbol", "symbol_type",
            "start_line", "end_line", "identity_match",
        ),
    )
    record_id = result.get("record_id")
    if isinstance(record_id, int):
        result["record_ids"] = [record_id]
        result.pop("record_id", None)
    source_range = anchor_source_range(result)
    if source_range:
        result["source_ranges"] = [source_range]
        result.pop("start_line", None)
        result.pop("end_line", None)
    if result.get("source") == "wiki":
        result.pop("source", None)
    summary = str(item.get("summary") or "").strip()
    if summary and not generated_anchor_summary(summary, result):
        result["summary"] = summary[:MAX_TEXT]
    return result


def diverse_code_anchors(value: Any, include_log_emitters: bool) -> list[dict[str, Any]]:
    selected = []
    by_file: dict[str, dict[str, Any]] = {}
    values = ordered_code_anchor_candidates(records(value), include_log_emitters)
    for item in values:
        if (
            not include_log_emitters
            and item.get("source") == "log_emitter"
            and not item.get("identity_match")
        ):
            continue
        anchor = compact_code_anchor(item)
        file_path = str(anchor.get("file_path") or "")
        if not file_path:
            continue
        if file_path in by_file:
            merge_anchor_evidence(by_file[file_path], anchor)
            continue
        if len(selected) >= 4:
            continue
        selected.append(anchor)
        by_file[file_path] = anchor
    for anchor in selected:
        anchor.pop("identity_match", None)
        add_read_window(anchor)
    return selected


def ordered_code_anchor_candidates(
    values: list[dict[str, Any]],
    include_log_emitters: bool,
) -> list[dict[str, Any]]:
    wiki = [item for item in values if item.get("source") != "log_emitter"]
    logs = [item for item in values if item.get("source") == "log_emitter"]
    if not include_log_emitters:
        logs = [item for item in logs if item.get("identity_match")]
    return [*wiki[:1], *logs[:1], *wiki[1:], *logs[1:]]


def add_read_window(anchor: dict[str, Any]) -> None:
    ranges = anchor.get("source_ranges") or []
    starts = [item.get("start_line") for item in ranges if isinstance(item.get("start_line"), int)]
    ends = [item.get("end_line") for item in ranges if isinstance(item.get("end_line"), int)]
    if starts and ends and max(ends) - min(starts) < 180:
        anchor["read_window"] = {"start_line": min(starts), "end_line": max(ends)}


def anchor_source_range(anchor: dict[str, Any]) -> dict[str, Any]:
    start = anchor.get("start_line")
    end = anchor.get("end_line")
    if not isinstance(start, int) or not isinstance(end, int) or start <= 0 or end < start:
        return {}
    return clean_record(
        {
            "symbol": anchor.get("symbol"),
            "start_line": start,
            "end_line": end,
        },
        ("symbol", "start_line", "end_line"),
    )


def merge_anchor_evidence(target: dict[str, Any], source: dict[str, Any]) -> None:
    record_ids = target.setdefault("record_ids", [])
    for source_id in source.get("record_ids") or []:
        if isinstance(source_id, int) and source_id not in record_ids and len(record_ids) < 3:
            record_ids.append(source_id)
    ranges = target.setdefault("source_ranges", [])
    for source_range in source.get("source_ranges") or []:
        if source_range not in ranges and len(ranges) < 3:
            ranges.append(source_range)


def generated_anchor_summary(summary: str, anchor: dict[str, Any]) -> bool:
    lowered = summary.casefold()
    file_path = str(anchor.get("file_path") or "").casefold()
    symbol = str(anchor.get("symbol") or "").casefold()
    return bool(file_path and file_path in lowered and (not symbol or symbol in lowered))


def relevant_relations(
    value: Any,
    code_anchors: list[dict[str, Any]],
    log_anchors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    endpoints = {
        ("code_symbol", int(item["record_id"]))
        for item in code_anchors
        if isinstance(item.get("record_id"), int)
    }
    endpoints.update(
        ("code_symbol", int(record_id))
        for item in code_anchors
        for record_id in item.get("record_ids") or []
        if isinstance(record_id, int)
    )
    endpoints.update(
        ("code_log_statement", int(item["log_id"]))
        for item in log_anchors
        if isinstance(item.get("log_id"), int)
    )
    selected = []
    for item in records(value):
        if item.get("relation") == "contains":
            continue
        source = (str(item.get("source_type") or ""), item.get("source_id"))
        target = (str(item.get("target_type") or ""), item.get("target_id"))
        if source in endpoints or target in endpoints:
            selected.append(compact_relation(item))
        if len(selected) >= 4:
            break
    return selected


def compact_memory_ref(item: dict[str, Any]) -> dict[str, Any]:
    return clean_record(item, MEMORY_FIELDS)


def compact_records(value: Any, limit: int) -> list[dict[str, Any]]:
    return [clean_record(item, GUARD_FIELDS) for item in records(value)[:limit]]


def evidence_gaps(handoff: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if not handoff.get("log_anchors"):
        gaps.append("no_log_anchor")
    if not handoff.get("code_anchors"):
        gaps.append("no_code_anchor")
    elif len({
        str(item.get("file_path") or "")
        for item in records(handoff.get("code_anchors"))[:5]
        if item.get("file_path")
    }) < 3:
        gaps.append("limited_code_anchor_diversity")
    path = handoff.get("path_context") if isinstance(handoff.get("path_context"), dict) else {}
    if handoff.get("log_anchors") and not path.get("activated"):
        gaps.append("no_strong_log_anchor")
    if path.get("activated") and not path.get("path_candidates"):
        gaps.append("no_reconstructable_path")
    return gaps


def enforce_budget(
    payload: dict[str, Any],
    token_budget: int = COMPACT_TOKEN_BUDGET,
) -> None:
    handoff = payload["query_handoff"]
    paths = handoff["path_context"]["path_candidates"]
    reductions = (
        lambda: handoff.__setitem__("relation_hints", handoff["relation_hints"][:2]),
        lambda: [path.__setitem__("expected_logs", path["expected_logs"][:2]) for path in paths],
        lambda: [path.__setitem__("uncertainty", path["uncertainty"][:1]) for path in paths],
        lambda: handoff.__setitem__("code_anchors", handoff["code_anchors"][:3]),
        lambda: handoff.__setitem__("log_keywords", handoff["log_keywords"][:8]),
        lambda: handoff.__setitem__("experience_refs", handoff["experience_refs"][:1]),
        lambda: handoff.__setitem__("semantic_refs", handoff["semantic_refs"][:1]),
        lambda: handoff["path_context"].__setitem__("path_candidates", paths[:2]),
        lambda: payload.__setitem__("blocked_memory_notes", payload["blocked_memory_notes"][:1]),
        lambda: payload.__setitem__("conflict_notes", payload["conflict_notes"][:1]),
        lambda: minimize_guards(payload),
        lambda: payload.__setitem__("blocked_memory_notes", []),
        lambda: handoff["path_context"].__setitem__("path_candidates", paths[:1]),
        lambda: hard_trim(payload),
    )
    for reduce_payload in reductions:
        if estimate_payload_tokens(payload) <= token_budget - 60:
            break
        reduce_payload()


def minimize_guards(payload: dict[str, Any]) -> None:
    for key in ("correction_guards", "semantic_patch_notes", "blocked_memory_notes", "conflict_notes"):
        payload[key] = [clean_record(item, MINIMAL_GUARD_FIELDS) for item in payload[key]]


def hard_trim(payload: dict[str, Any]) -> None:
    handoff = payload["query_handoff"]
    handoff["log_keywords"] = handoff["log_keywords"][:6]
    handoff["log_anchors"] = handoff["log_anchors"][:2]
    handoff["code_anchors"] = handoff["code_anchors"][:2]
    handoff["relation_hints"] = []
    handoff["experience_refs"] = []
    handoff["semantic_refs"] = []
    candidates = handoff["path_context"]["path_candidates"][:1]
    for candidate in candidates:
        candidate["nodes"] = candidate["nodes"][:4]
        candidate["relations"] = candidate["relations"][:3]
        candidate["expected_logs"] = candidate["expected_logs"][:1]
        candidate["uncertainty"] = candidate["uncertainty"][:1]
    handoff["path_context"]["path_candidates"] = candidates
    payload["correction_guards"] = shrink_guard_group(payload["correction_guards"])
    payload["semantic_patch_notes"] = shrink_guard_group(payload["semantic_patch_notes"])
    payload["blocked_memory_notes"] = []
    payload["conflict_notes"] = shrink_guard_group(payload["conflict_notes"])


def shrink_guard_group(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return []
    item = items[0]
    keys = (
        "id", "reflection_id", "semantic_id", "experience_type", "fact",
        "scope", "task", "status",
    )
    result = {
        key: str(item[key])[:100] if isinstance(item.get(key), str) else item[key]
        for key in keys
        if item.get(key) not in (None, "")
    }
    warnings = item.get("warnings")
    if isinstance(warnings, list) and warnings:
        result["warnings"] = [str(warnings[0])[:100]]
    return [result]


def clean_record(item: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        key: compact_value(item.get(key))
        for key in fields
        if item.get(key) not in (None, "", [], {})
    }


def compact_value(value: Any) -> Any:
    if isinstance(value, str):
        return value[:MAX_TEXT]
    if isinstance(value, list):
        return [compact_value(item) for item in value[:2]]
    return value


def records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def text_list(value: Any, limit: int, max_length: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:max_length] for item in value if str(item).strip()][:limit]


def compact_keywords(value: Any) -> list[str]:
    return [
        item for item in text_list(value, 20, 80)
        if item.casefold() not in KEYWORD_STOPWORDS
    ][:12]
