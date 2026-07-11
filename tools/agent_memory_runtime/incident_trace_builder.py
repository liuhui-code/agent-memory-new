# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .incident_trace_models import INCIDENT_LOG_TEXT_LIMIT
from .models import Project
from .query import recall_candidate_ids
from .records import row_dict
from .storage import connect
from .text import query_tokens, score_weighted_fields, tokenize, unique_list


SCENE_TRIGGERS = {
    "route": ("页面跳转", "跳转", "白屏", "router", "pushurl", "replaceurl", "route", "navigation"),
    "resource": ("图片", "图标", "字符串", "资源", "$r", "app.media", "app.string", "resource"),
    "network": ("请求", "接口", "加载", "fetch", "request", "response", "http", "profile", "data"),
    "permission": ("权限", "permission", "grant", "authorize", "network permission"),
    "ability": ("ability", "want", "startup", "lifecycle", "oncreate", "onforeground"),
    "state": ("session", "token", "login", "auth", "cache", "empty state", "空数据"),
}


def classify_arkts_scene(symptom: str, log_text: str) -> tuple[str, list[str]]:
    text = f"{symptom}\n{log_text}".lower()
    best_scene = "unknown"
    best_reasons: list[str] = []
    for scene, triggers in SCENE_TRIGGERS.items():
        reasons = [f"{scene}:{trigger}" for trigger in triggers if trigger.lower() in text]
        if len(reasons) > len(best_reasons):
            best_scene = scene
            best_reasons = reasons
    return best_scene, best_reasons


def compact_log_text(log_text: str) -> str:
    return " ".join(log_text.strip().split())[:INCIDENT_LOG_TEXT_LIMIT]


def dominant_log_events(log_text: str, limit: int = 5) -> list[str]:
    lines = [line.strip() for line in log_text.splitlines() if line.strip()]
    if not lines and log_text.strip():
        lines = [log_text.strip()]
    events: list[str] = []
    for line in lines:
        cleaned = re.sub(r"\s+", " ", line)
        cleaned = re.sub(r"^\d{2,4}[-/:. T\d]+", "", cleaned).strip()
        if cleaned:
            events.append(cleaned[:160])
    return unique_list(events)[:limit]


def trace_key(symptom: str, scene: str, events: list[str], top_anchor: str) -> str:
    material = "\n".join([symptom.strip().lower(), scene, *(events[:2]), top_anchor.lower()])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def fetch_code_logs(project: Project, query: str, limit: int = 10) -> list[dict[str, Any]]:
    tokens = query_tokens(query)
    expanded_terms = set(tokens) - set(tokenize(query))
    with connect(project) as conn:
        ids = recall_candidate_ids(conn, project, "code_log_statements", query, limit)
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"""
            SELECT *
            FROM code_log_statements
            WHERE project_id = ? AND id IN ({placeholders})
            """,
            (project.project_id, *ids),
        ).fetchall()
    logs: list[dict[str, Any]] = []
    for row in rows:
        text = " ".join(
            str(row[key] or "")
            for key in (
                "file_path",
                "function",
                "level",
                "logger",
                "message_template",
                "raw_statement",
                "business_summary",
                "business_event",
                "trigger_stage",
                "symptom_terms",
                "likely_causes",
                "process_hint",
                "neighbor_terms",
            )
        )
        score, reasons = score_weighted_fields(
            query,
            tokens,
            expanded_terms,
            [("incident_log", text, 1.0)],
            [("exact_log_message", row["message_template"], 8.0)],
        )
        if score:
            item = row_dict(row)
            item["score"] = round(score, 2)
            item["match_reasons"] = reasons
            logs.append(item)
    logs.sort(key=lambda item: (item.get("score", 0), item.get("id", 0)), reverse=True)
    return logs[:limit]


def linked_targets_from_logs(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for log in logs[:5]:
        target_key = f"{log.get('file_path')}::{log.get('message_template')}"
        links.append(
            {
                "target_type": "code_log_statement",
                "target_id": int(log["id"]),
                "target_key": target_key,
                "relation": "matched_log",
                "score": float(log.get("score") or 0.0),
                "evidence": "matched dominant log event",
            }
        )
    return links


def candidate_chain_from_logs(logs: list[dict[str, Any]]) -> list[str]:
    chain: list[str] = []
    for log in logs[:5]:
        function = log.get("function") or "<module>"
        message = log.get("message_template") or log.get("raw_statement") or ""
        chain.append(f"{log.get('file_path')}::{function} emits {message}")
    return chain


def build_incident_trace_draft(project: Project, symptom: str, log_text: str) -> dict[str, Any]:
    compact_log = compact_log_text(log_text)
    scene, scene_reasons = classify_arkts_scene(symptom, compact_log)
    events = dominant_log_events(compact_log)
    search_query = " ".join(unique_list([symptom, scene, *events]))
    matched_logs = fetch_code_logs(project, search_query)
    top_anchor = ""
    if matched_logs:
        top_anchor = f"{matched_logs[0].get('file_path')}::{matched_logs[0].get('message_template')}"
    suggested_terms = unique_list(
        [
            *query_tokens(symptom),
            *query_tokens(" ".join(events[:2])),
            *[str(log.get("function") or "") for log in matched_logs[:3]],
            *[str(log.get("file_path") or "") for log in matched_logs[:3]],
        ]
    )[:12]
    return {
        "trace_key": trace_key(symptom, scene, events, top_anchor),
        "symptom": symptom,
        "arkts_scene": scene,
        "scene_reasons": scene_reasons,
        "entry_log_text": compact_log,
        "normalized_error": events[0] if events else compact_log[:160],
        "dominant_log_events": events,
        "matched_code_logs": matched_logs[:5],
        "linked_targets": linked_targets_from_logs(matched_logs),
        "candidate_chain": candidate_chain_from_logs(matched_logs),
        "inspection_targets": unique_list([str(log.get("file_path") or "") for log in matched_logs[:5]]),
        "suggested_followup_query": " ".join(suggested_terms),
        "suspected_chain": json.dumps(candidate_chain_from_logs(matched_logs), ensure_ascii=False),
    }

