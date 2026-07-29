# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import re
from typing import Any


PLACEHOLDER_RE = re.compile(
    r"\$\{[^{}]*\}|%\{(?:public|private)\}[A-Za-z]|%[-+0-9.#]*[A-Za-z]|\{[A-Za-z_][\w.]*\}"
)
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
IDENTITY_RE = re.compile(r"\b(?=[A-Za-z0-9_]*[A-Za-z])(?=[A-Za-z0-9_]*\d)[A-Za-z0-9_]{6,}\b")
DYNAMIC_EXPRESSION_RE = re.compile(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*")
MATCH_PRIORITY = {"none": 0, "distinctive_literal": 1, "exact_template": 2}


def event_identity(item: dict[str, Any]) -> dict[str, Any]:
    template = str(item.get("message_template") or "")
    segments = template_literal_segments(template)
    skeleton = canonical_text(PLACEHOLDER_RE.sub(" <value> ", template))
    owner = "#".join((
        str(item.get("file_path") or ""),
        str(item.get("function") or ""),
    ))
    material = "|".join((
        str(item.get("level") or "").casefold(),
        str(item.get("logger") or "").casefold(),
        skeleton,
        owner,
    ))
    return {
        "schema_version": "log-event-identity/v1",
        "fingerprint": hashlib.sha256(material.encode("utf-8")).hexdigest()[:16],
        "template_skeleton": skeleton,
        "literal_segments": segments,
        "owner": owner,
    }


def template_literal_segments(template: str) -> list[str]:
    return [
        segment for segment in (
            canonical_text(part) for part in PLACEHOLDER_RE.split(str(template or ""))
        ) if segment
    ]


def has_literal_event_identity(item: dict[str, Any]) -> bool:
    template = str(item.get("message_template") or "")
    raw = str(item.get("raw_statement") or item.get("raw_call") or "")
    if raw and DYNAMIC_EXPRESSION_RE.fullmatch(template):
        quoted = rf"(['\"`]){re.escape(template)}\1"
        return bool(re.search(quoted, raw))
    return bool(template_literal_segments(template))


def event_match(item: dict[str, Any], query: Any) -> dict[str, Any]:
    template = str(item.get("message_template") or "")
    query_text = canonical_text(str(query or ""))
    canonical_template = canonical_text(template)
    if (
        canonical_template
        and not PLACEHOLDER_RE.search(template)
        and exact_identity_candidate(canonical_template)
        and phrase_in_text(canonical_template, query_text)
    ):
        return match_result(item, "exact_template", canonical_template)
    matched = [
        segment for segment in template_literal_segments(template)
        if distinctive_literal(segment) and phrase_in_text(segment, query_text)
    ]
    if matched:
        return match_result(item, "distinctive_literal", max(matched, key=len))
    return match_result(item, "none", "")


def select_event_matches(
    logs: list[dict[str, Any]], query: Any,
) -> list[dict[str, Any]]:
    matches = [(item, event_match(item, query)) for item in logs]
    strong = [(item, match) for item, match in matches if match["priority"] > 0]
    if not strong:
        return logs
    best = max((match["priority"], len(match["matched_literal"])) for _, match in strong)
    return [
        item for item, match in strong
        if (match["priority"], len(match["matched_literal"])) == best
    ]


def match_result(item: dict[str, Any], band: str, literal: str) -> dict[str, Any]:
    return {
        "band": band,
        "priority": MATCH_PRIORITY[band],
        "matched_literal": literal,
        "identity": event_identity(item),
    }


def canonical_text(value: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", value.casefold())
    return " ".join(text.split())


def phrase_in_text(needle: str, haystack: str) -> bool:
    return bool(needle and haystack and f" {needle} " in f" {haystack} ")


def exact_identity_candidate(value: str) -> bool:
    words = value.split()
    return distinctive_literal(value) or (len(words) >= 3 and len(value) >= 12)


def distinctive_literal(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    if len(CJK_RE.findall(value)) >= 4:
        return True
    if IDENTITY_RE.search(value):
        return True
    words = [word for word in value.split() if len(word) > 2]
    return len(words) >= 3 and len(compact) >= 14
