# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .log_event_identity import event_match, select_event_matches
from .text import ENGLISH_QUERY_STOPWORDS, tokenize


NEGATION_CUES = ("without", "ignore", "excluding", "exclude", "不要", "排除", "忽略")
NEGATION_FILLER = {"without", "following", "ignore", "excluding", "exclude", "noise"}
PATH_BOUNDARY_RELATIONS = {"configured_by", "imports"}


def relevant_log_anchors(logs: list[dict[str, Any]], query: Any) -> list[dict[str, Any]]:
    text = str(query or "")
    lowered = text.casefold()
    positions = [(lowered.find(cue), cue) for cue in NEGATION_CUES if cue in lowered]
    selected = logs
    if positions:
        position, cue = min(positions)
        excluded = {
            token.casefold() for token in tokenize(text[position + len(cue):])
            if token.casefold() not in ENGLISH_QUERY_STOPWORDS | NEGATION_FILLER
        }
        if excluded:
            filtered = [
                item for item in logs
                if not excluded.intersection(tokenize(log_identity_text(item)))
            ]
            selected = filtered or logs
    return select_event_matches(selected, text)


def exact_log_identity(item: dict[str, Any], query: Any) -> bool:
    return bool(event_match(item, query)["priority"])


def prioritized_log_anchors(
    logs: list[dict[str, Any]], query: Any, limit: int = 3,
) -> list[dict[str, Any]]:
    relevant = relevant_log_anchors(logs, query)
    wrapped = [
        item for item in relevant
        if str(item.get("evidence_class") or "").endswith("_wrapped")
    ][:2]
    wrapped_ids = {id(item) for item in wrapped}
    return [*wrapped, *(item for item in relevant if id(item) not in wrapped_ids)][:limit]


def has_wrapped_log_anchor(logs: list[dict[str, Any]]) -> bool:
    return any(str(item.get("evidence_class") or "").endswith("_wrapped") for item in logs)


def log_identity_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "").casefold()
        for key in ("message_template", "logger", "business_event", "file_path", "function")
    )


def path_context_for_log_anchors(
    path_context: dict[str, Any],
    log_anchors: list[dict[str, Any]],
) -> dict[str, Any]:
    files = {str(item.get("file_path") or "") for item in log_anchors if item.get("file_path")}
    candidates = records(path_context.get("path_candidates"))
    if not path_context.get("activated") or not files or not candidates:
        return path_context
    selected = [
        item for item in candidates
        if str((item.get("emitter") or {}).get("file_path") or "") in files
    ]
    if not selected or len(selected) == len(candidates):
        return path_context
    return {**path_context, "path_candidates": selected}


def path_scoped_code_anchors(
    anchors: list[dict[str, Any]],
    path_context: dict[str, Any],
    log_anchors: list[dict[str, Any]] | None = None,
    query: Any = "",
) -> list[dict[str, Any]]:
    candidates = records(path_context.get("path_candidates"))
    if path_context.get("activated") and candidates:
        files = {
            str(item.get("file_path"))
            for candidate in candidates
            for item in [
                candidate.get("entry"),
                candidate.get("emitter"),
                *records(candidate.get("nodes")),
            ]
            if isinstance(item, dict) and item.get("file_path")
        }
        scoped = [item for item in anchors if str(item.get("file_path") or "") in files]
        boundary = [
            item for item in anchors
            if item.get("graph_relation") in PATH_BOUNDARY_RELATIONS and item not in scoped
        ]
        boundary.sort(
            key=lambda item: item.get("graph_relation") != "configured_by"
        )
        return [*scoped, *boundary[:2]] or anchors
    exact = [
        item for item in (log_anchors or []) if exact_log_identity(item, query)
    ]
    identities = {
        (str(item.get("file_path") or ""), str(item.get("function") or ""))
        for item in exact if item.get("file_path")
    }
    scoped = [
        {**item, "log_identity_match": True}
        for item in anchors
        if (str(item.get("file_path") or ""), str(item.get("symbol") or "")) in identities
    ]
    return scoped or anchors


def records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
