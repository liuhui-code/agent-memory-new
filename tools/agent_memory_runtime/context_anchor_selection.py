# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .text import ENGLISH_QUERY_STOPWORDS, tokenize


NEGATION_CUES = ("without", "ignore", "excluding", "exclude", "不要", "排除", "忽略")
NEGATION_FILLER = {"without", "following", "ignore", "excluding", "exclude", "noise"}


def relevant_log_anchors(logs: list[dict[str, Any]], query: Any) -> list[dict[str, Any]]:
    text = str(query or "")
    lowered = text.casefold()
    positions = [(lowered.find(cue), cue) for cue in NEGATION_CUES if cue in lowered]
    if not positions:
        return logs
    position, cue = min(positions)
    excluded = {
        token.casefold() for token in tokenize(text[position + len(cue):])
        if token.casefold() not in ENGLISH_QUERY_STOPWORDS | NEGATION_FILLER
    }
    if not excluded:
        return logs
    selected = [
        item for item in logs
        if not excluded.intersection(tokenize(log_identity_text(item)))
    ]
    return selected or logs


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
) -> list[dict[str, Any]]:
    candidates = records(path_context.get("path_candidates"))
    if not path_context.get("activated") or not candidates:
        return anchors
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
    return scoped or anchors


def records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
