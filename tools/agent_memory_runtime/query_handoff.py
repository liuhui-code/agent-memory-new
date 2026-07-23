# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .text import json_list, tokenize, unique_list


MAX_KEYWORDS = 20
MAX_ANCHORS = 12
CODE_IDENTITY_SCORE_MIN = 6.0
CODE_IDENTITY_REASONS = {"exact_function", "exact_symbol", "exact_identifier"}


def build_query_handoff(query: str, data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    logs = data.get("code_log_matches") or []
    wiki = data.get("wiki_matches") or []
    reflections = data.get("reflections") or []
    semantics = data.get("semantic_facts") or []
    return {
        "schema_version": "agent-query-handoff/v1",
        "input_query": query,
        "log_keywords": log_keywords(query, logs),
        "log_anchors": [compact_log_anchor(item) for item in logs[:MAX_ANCHORS]],
        "code_anchors": code_anchors(wiki, logs),
        "experience_refs": [compact_experience(item) for item in reflections[:MAX_ANCHORS]],
        "semantic_refs": [compact_semantic(item) for item in semantics[:MAX_ANCHORS]],
        "next_query_contract": {
            "command": "python tools/agent_memory.py context --project . --query <agent-extracted-term> --compact --json",
            "accepted_inputs": [
                "exact phrase or identifier observed in the temporary runtime log",
                "one candidate cause produced by the Agent CLI",
                "file, symbol, route, resource, error code, logger, or event name",
            ],
            "one_candidate_per_query": True,
        },
        "role_boundary": {
            "runtime": "retrieve historical memory, code-log keywords, current code anchors, and stored graph edges",
            "agent_cli": "analyze temporary logs, form candidate causes, infer call/causal chains, inspect source, and verify",
            "runtime_reads_temporary_logs": False,
            "runtime_builds_causal_chains": False,
        },
    }


def log_keywords(query: str, logs: list[dict[str, Any]]) -> list[str]:
    values: list[str] = [*tokenize(query)]
    for item in logs[:MAX_ANCHORS]:
        values.extend([
            str(item.get("business_event") or ""),
            str(item.get("trigger_stage") or ""),
            str(item.get("logger") or ""),
            str(item.get("function") or ""),
            str(item.get("process_hint") or ""),
        ])
        values.extend(json_list(item.get("symptom_terms")))
        values.extend(json_list(item.get("neighbor_terms")))
        values.extend(tokenize(str(item.get("message_template") or "")))
        values.extend(tokenize(str(item.get("raw_statement") or "")))
    return unique_list([value for value in values if len(value.strip()) > 1])[:MAX_KEYWORDS]


def compact_log_anchor(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "log_id": item.get("id"),
        "message_template": item.get("message_template"),
        "logger": item.get("logger"),
        "business_event": item.get("business_event"),
        "trigger_stage": item.get("trigger_stage"),
        "symptom_terms": json_list(item.get("symptom_terms")),
        "process_hint": item.get("process_hint"),
        "file_path": item.get("file_path"),
        "function": item.get("function"),
        "line": item.get("line"),
    }


def code_anchors(
    wiki: list[dict[str, Any]],
    logs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    file_counts: dict[str, int] = {}
    for source, values in (("wiki", wiki), ("log_emitter", logs)):
        for item in values:
            file_path = str(item.get("file_path") or "")
            if file_counts.get(file_path, 0) >= 2:
                continue
            if append_code_anchor(anchors, seen, item, source):
                file_counts[file_path] = file_counts.get(file_path, 0) + 1
            if len(anchors) >= MAX_ANCHORS:
                return anchors
    return anchors[:MAX_ANCHORS]


def append_code_anchor(
    anchors: list[dict[str, Any]],
    seen: set[tuple[str, str]],
    item: dict[str, Any],
    source: str,
) -> bool:
    file_path = str(item.get("file_path") or "")
    symbol = str(item.get("symbol") or item.get("function") or "")
    key = (file_path, symbol)
    if not file_path or key in seen:
        return False
    seen.add(key)
    anchors.append({
        "source": source,
        "record_id": item.get("id"),
        "file_path": file_path,
        "symbol": symbol,
        "symbol_type": item.get("symbol_type"),
        "summary": item.get("business_summary") or item.get("summary"),
        "start_line": item.get("start_line") or item.get("line"),
        "end_line": item.get("end_line") or item.get("line"),
        "identity_match": source == "log_emitter" and strong_code_identity(item),
    })
    return True


def strong_code_identity(item: dict[str, Any]) -> bool:
    reasons = {
        str(reason) for reason in item.get("match_reasons") or [] if str(reason).strip()
    }
    try:
        score = float(item.get("score") or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    return bool(reasons & CODE_IDENTITY_REASONS) and score >= CODE_IDENTITY_SCORE_MIN


def compact_experience(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "reflection_id": item.get("id"),
        "experience_type": item.get("experience_type"),
        "task": item.get("task"),
        "problem": item.get("problem"),
        "trigger_condition": item.get("trigger_condition"),
        "verification_method": item.get("verification_method"),
        "trust_level": item.get("trust_level"),
        "warnings": item.get("warnings") or [],
    }


def compact_semantic(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "semantic_id": item.get("id"),
        "fact": item.get("fact"),
        "scope": item.get("scope"),
        "source": item.get("source"),
        "trust_level": item.get("trust_level"),
        "warnings": item.get("warnings") or [],
    }
