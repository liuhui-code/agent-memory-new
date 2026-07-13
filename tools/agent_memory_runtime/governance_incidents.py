# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import Any

from .governance_incident_artifacts import (
    build_incident_strategy_markdown,
    build_recurring_incident_fingerprint_markdown,
    incident_strategy_draft_path,
    recurring_incident_fingerprint_draft_path,
)
from .governance_skill_candidates import is_complete_experience_candidate
from .governance_utils import stable_unique_strings
from .models import Project
from .text import json_list, unique_list

def is_runtime_log_backed_procedure(row: dict[str, Any]) -> bool:
    if str(row.get("experience_type") or "") != "procedure_experience":
        return False
    if str(row.get("useful_followup_focus") or "") == "log":
        return True
    source_cases = [str(item).lower() for item in json_list(row.get("source_cases"))]
    return any(item.startswith("runtime_log:") or item.startswith("session:") for item in source_cases)



def slug_words(text: str) -> list[str]:
    normalized = text.lower()
    normalized = normalized.replace("资料", "profile").replace("个人中心", "profile").replace("登录", "login")
    return [token for token in re.findall(r"[a-z0-9]+", normalized) if token]



def classify_incident_domain(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("session invalid", "401", "auth", "login", "token", "session")):
        return "auth-session"
    if any(token in lowered for token in ("route", "router", "pushurl", "navigation")):
        return "route"
    if any(token in lowered for token in ("resource", "$r", "media", "image")):
        return "resource"
    if any(token in lowered for token in ("permission", "config", "module", "ability")):
        return "config"
    return "runtime"



def classify_incident_goal(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("profile", "资料", "个人中心")) and any(token in lowered for token in ("blank", "空白", "没数据", "no data")):
        return "profile-blank"
    if any(token in lowered for token in ("blank", "空白", "white screen")):
        return "blank-screen"
    if any(token in lowered for token in ("permission", "权限")):
        return "permission"
    if any(token in lowered for token in ("retry", "重试", "network", "网络")):
        return "network-retry"
    return "incident"



def incident_strategy_name(row: dict[str, Any]) -> str:
    text = " ".join(
        [
            str(row.get("problem") or ""),
            " ".join(json_list(row.get("useful_followup_terms"))),
            " ".join(json_list(row.get("source_cases"))),
        ]
    )
    return f"log-{classify_incident_domain(text)}-{classify_incident_goal(text)}-diagnosis"



def recurring_incident_fingerprint_name(goal_area: str, common_log_events: list[str]) -> str:
    suffix = "-".join(slug_words(" ".join(common_log_events[:3]))[:6]) or "generic"
    return f"incident-{goal_area.replace('_', '-')}-{suffix}"



def evaluate_incident_fingerprint_quality(candidate: dict[str, Any]) -> tuple[int, str, list[str]]:
    score = 0
    reasons: list[str] = []
    supporting_count = int(candidate.get("supporting_count") or 0)
    if supporting_count >= 3:
        score += 3
        reasons.append("has_three_or_more_supporting_incidents")
    elif supporting_count >= 2:
        score += 2
        reasons.append("has_repeated_supporting_incidents")
    if candidate.get("common_log_events"):
        score += 2
        reasons.append("has_common_log_events")
    if candidate.get("dominant_failure_signals"):
        score += 1
        reasons.append("has_dominant_failure_signals")
    if candidate.get("misleading_signals"):
        score += 1
        reasons.append("captures_misleading_signals")
    helped = int(candidate.get("helped_reuse_count") or 0)
    misleading = int(candidate.get("misleading_reuse_count") or 0)
    if helped >= 1:
        score += 1
        reasons.append("has_helped_reuse_signal")
    if misleading >= 1:
        score -= 1
        reasons.append("has_misleading_reuse_signal")
    readiness = "promotion_candidate" if score >= 7 else "review_candidate" if score >= 4 else "needs_more_evidence"
    return score, readiness, reasons



def evaluate_incident_strategy_quality(candidate: dict[str, Any]) -> tuple[int, str, list[str]]:
    score = 0
    reasons: list[str] = []
    if int(candidate.get("supporting_count") or 0) >= 2:
        score += 2
        reasons.append("has_repeated_runtime_incidents")
    if candidate.get("common_log_events"):
        score += 2
        reasons.append("has_common_log_events")
    if candidate.get("recommended_steps"):
        score += 2
        reasons.append("has_recommended_steps")
    if candidate.get("verification_paths"):
        score += 1
        reasons.append("has_verification_paths")
    if candidate.get("misleading_signals"):
        score += 1
        reasons.append("captures_misleading_signals")
    helped = int(candidate.get("helped_reuse_count") or 0)
    if helped >= 1:
        score += 2
        reasons.append("has_helped_reuse_signal")
    if int(candidate.get("misleading_reuse_count") or 0) >= 1:
        score -= 1
        reasons.append("has_misleading_reuse_signal")
    readiness = "promotion_candidate" if score >= 7 else "review_candidate" if score >= 4 else "needs_more_evidence"
    return score, readiness, reasons



def incident_goal_area(strategy_name: str) -> str:
    area = str(strategy_name or "").strip().lower()
    if area.startswith("log-"):
        area = area[4:]
    if area.endswith("-diagnosis"):
        area = area[: -len("-diagnosis")]
    return area.replace("-", "_")



def infer_log_design_kinds(feedback: list[str]) -> list[str]:
    kinds: list[str] = []
    lowered = " ".join(str(item).lower() for item in feedback)
    if "decision checkpoint" in lowered or "decision checkpoints" in lowered:
        kinds.append("decision_checkpoint")
    if "request_id" in lowered or "session_id" in lowered or "correlation" in lowered:
        kinds.append("request_correlation")
    if "start marker" in lowered or "start log" in lowered:
        kinds.append("start_marker")
    if not kinds:
        kinds.append("anchor_alignment")
    return stable_unique_strings(kinds)



def build_incident_strategy_candidates(project: Project, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not is_runtime_log_backed_procedure(row):
            continue
        if not is_complete_experience_candidate(row):
            continue
        name = incident_strategy_name(row)
        groups.setdefault(name, []).append(row)

    candidates: list[dict[str, Any]] = []
    for strategy_name, grouped_rows in groups.items():
        if len(grouped_rows) < 2:
            continue
        grouped_rows.sort(key=lambda item: int(item.get("id") or 0))
        common_followup_focus = unique_list(
            [str(row.get("useful_followup_focus") or "") for row in grouped_rows if row.get("useful_followup_focus")]
        )
        goal_symptoms = stable_unique_strings(
            [str(row.get("problem") or "") for row in grouped_rows if row.get("problem")]
        )[:6]
        common_log_events = stable_unique_strings(
            [
                term
                for row in grouped_rows
                for term in json_list(row.get("useful_followup_terms"))
                if len(term.strip()) > 1
            ]
        )[:10]
        recommended_steps = stable_unique_strings(
            [
                step
                for row in grouped_rows
                for step in json_list(row.get("what_worked"))
            ]
        )[:8]
        verification_paths = stable_unique_strings(
            [
                str(row.get("final_verification_path") or "")
                for row in grouped_rows
                if str(row.get("final_verification_path") or "").strip()
            ]
        )[:6]
        misleading_signals = stable_unique_strings(
            [
                signal
                for row in grouped_rows
                for signal in json_list(row.get("what_failed")) + json_list(row.get("misleading_followup_terms"))
            ]
        )[:8]
        supporting_cases = stable_unique_strings(
            [
                case
                for row in grouped_rows
                for case in json_list(row.get("related_cases")) + json_list(row.get("source_cases"))
            ]
        )[:10]
        log_design_feedback = stable_unique_strings(
            [
                "Add decision checkpoints around auth/session or fallback branches.",
                "Prefer request_id/session_id correlation in runtime logs.",
            ]
        )
        helped_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "helped" or row.get("reuse_feedback") == "helped"
        )
        partial_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "partial" or row.get("reuse_feedback") == "partial"
        )
        misleading_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "misleading" or row.get("reuse_feedback") == "misleading"
        )
        candidate = {
            "strategy_name": strategy_name,
            "experience_type": "procedure_experience",
            "supporting_reflection_ids": [int(row["id"]) for row in grouped_rows],
            "supporting_count": len(grouped_rows),
            "common_followup_focus": common_followup_focus,
            "goal_symptoms": goal_symptoms,
            "common_log_events": common_log_events,
            "recommended_steps": recommended_steps,
            "verification_paths": verification_paths,
            "misleading_signals": misleading_signals,
            "supporting_cases": supporting_cases,
            "log_design_feedback": log_design_feedback,
            "helped_reuse_count": helped_count,
            "partial_reuse_count": partial_count,
            "misleading_reuse_count": misleading_count,
            "draft_path": incident_strategy_draft_path(strategy_name),
            "related_skill_candidates": stable_unique_strings(
                [str(row.get("skill_candidate") or "") for row in grouped_rows if str(row.get("skill_candidate") or "").strip()]
            )[:4],
        }
        quality_score, promotion_readiness, quality_reasons = evaluate_incident_strategy_quality(candidate)
        candidate["quality_score"] = quality_score
        candidate["promotion_readiness"] = promotion_readiness
        candidate["quality_reasons"] = quality_reasons
        candidate["draft_markdown"] = build_incident_strategy_markdown(candidate)
        candidates.append(candidate)
    candidates.sort(key=lambda item: (-int(item["supporting_count"]), item["strategy_name"]))
    return candidates



def build_recurring_incident_fingerprint_candidates(project: Project, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not is_runtime_log_backed_procedure(row):
            continue
        goal_area = incident_goal_area(incident_strategy_name(row))
        common_terms = stable_unique_strings(json_list(row.get("useful_followup_terms")))[:3]
        fingerprint_name = recurring_incident_fingerprint_name(goal_area, common_terms)
        groups.setdefault(fingerprint_name, []).append(row)

    candidates: list[dict[str, Any]] = []
    for fingerprint_name, grouped_rows in groups.items():
        if len(grouped_rows) < 2:
            continue
        grouped_rows.sort(key=lambda item: int(item.get("id") or 0))
        goal_symptoms = stable_unique_strings(
            [str(row.get("problem") or "") for row in grouped_rows if str(row.get("problem") or "").strip()]
        )[:6]
        common_log_events = stable_unique_strings(
            [
                term
                for row in grouped_rows
                for term in json_list(row.get("useful_followup_terms"))
                if len(term.strip()) > 1
            ]
        )[:10]
        misleading_signals = stable_unique_strings(
            [
                signal
                for row in grouped_rows
                for signal in json_list(row.get("misleading_followup_terms")) + json_list(row.get("what_failed"))
            ]
        )[:8]
        supporting_cases = stable_unique_strings(
            [
                case
                for row in grouped_rows
                for case in json_list(row.get("source_cases")) + json_list(row.get("related_cases"))
            ]
        )[:10]
        dominant_failure_signals = stable_unique_strings(
            [
                *common_log_events[:4],
                *[
                    str(row.get("final_verification_path") or "")
                    for row in grouped_rows
                    if str(row.get("final_verification_path") or "").strip()
                ],
            ]
        )[:6]
        helped_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "helped" or row.get("reuse_feedback") == "helped"
        )
        partial_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "partial" or row.get("reuse_feedback") == "partial"
        )
        misleading_count = sum(
            1
            for row in grouped_rows
            if row.get("last_outcome") == "misleading" or row.get("reuse_feedback") == "misleading"
        )
        candidate = {
            "fingerprint_name": fingerprint_name,
            "goal_area": incident_goal_area(incident_strategy_name(grouped_rows[-1])),
            "supporting_reflection_ids": [int(row["id"]) for row in grouped_rows],
            "supporting_count": len(grouped_rows),
            "goal_symptoms": goal_symptoms,
            "common_log_events": common_log_events,
            "dominant_failure_signals": dominant_failure_signals,
            "misleading_signals": misleading_signals,
            "supporting_cases": supporting_cases,
            "helped_reuse_count": helped_count,
            "partial_reuse_count": partial_count,
            "misleading_reuse_count": misleading_count,
            "draft_path": recurring_incident_fingerprint_draft_path(fingerprint_name),
        }
        quality_score, promotion_readiness, quality_reasons = evaluate_incident_fingerprint_quality(candidate)
        candidate["quality_score"] = quality_score
        candidate["promotion_readiness"] = promotion_readiness
        candidate["quality_reasons"] = quality_reasons
        candidate["draft_markdown"] = build_recurring_incident_fingerprint_markdown(candidate)
        candidates.append(candidate)
    candidates.sort(key=lambda item: (-int(item["supporting_count"]), item["fingerprint_name"]))
    return candidates



def build_log_design_gap_candidates(project: Project, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not is_runtime_log_backed_procedure(row):
            continue
        goal_area = incident_goal_area(incident_strategy_name(row))
        groups.setdefault(goal_area, []).append(row)

    candidates: list[dict[str, Any]] = []
    for goal_area, grouped_rows in groups.items():
        if len(grouped_rows) < 2:
            continue
        grouped_rows.sort(key=lambda item: int(item.get("id") or 0))
        feedback = stable_unique_strings(
            [
                "Add decision checkpoints around auth/session or fallback branches.",
                "Prefer request_id/session_id correlation in runtime logs.",
                *[
                    str(row.get("repair_action") or "")
                    for row in grouped_rows
                    if "runtime slice" in str(row.get("repair_action") or "").lower()
                ],
            ]
        )[:6]
        candidates.append(
            {
                "strategy_name": incident_strategy_name(grouped_rows[-1]),
                "goal_area": goal_area,
                "goal_symptoms": stable_unique_strings([str(row.get("problem") or "") for row in grouped_rows if str(row.get("problem") or "").strip()])[:6],
                "supporting_reflection_ids": [int(row["id"]) for row in grouped_rows],
                "supporting_count": len(grouped_rows),
                "high_value_log_anchor_targets": stable_unique_strings(
                    [
                        *[
                            term
                            for row in grouped_rows
                            for term in json_list(row.get("useful_followup_terms"))
                        ],
                        *[
                            target
                            for row in grouped_rows
                            for target in json_list(row.get("inspection_targets"))
                        ],
                    ]
                )[:8],
                "suggested_log_kinds": infer_log_design_kinds(feedback),
                "log_design_feedback": feedback,
            }
        )
    candidates.sort(key=lambda item: (-int(item["supporting_count"]), item["goal_area"]))
    return candidates
