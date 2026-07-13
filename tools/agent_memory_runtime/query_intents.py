# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .models import Project
from .records import row_dict
from .storage import connect
from .text import query_tokens

MEMORY_INTENTS = {
    "code_current",
    "code_location",
    "code_business_semantics",
    "runtime_log_diagnosis",
    "procedure_reuse",
    "correction_guard",
    "semantic_correction",
    "semantic_lookup",
    "memory_maintenance",
    "incident_diagnosis",
    "general_context",
}


MEMORY_INTENT_ALIASES = {
    "code_location": "code_current",
    "code_business_semantics": "semantic_lookup",
    "runtime_log_diagnosis": "incident_diagnosis",
    "semantic_correction": "correction_guard",
    "memory_maintenance": "general_context",
}


REFLECTION_LANE_LIMITS = {
    "correction_guards": 4,
    "semantic_patch_notes": 6,
    "blocked_memory_notes": 8,
    "conflict_notes": 5,
}


MAIN_REFLECTION_BUDGETS = {
    "code_location": 0,
    "code_business_semantics": 1,
    "runtime_log_diagnosis": 2,
    "procedure_reuse": 3,
    "semantic_correction": 0,
    "memory_maintenance": 0,
    "general_context": 2,
}



def infer_memory_intent(query: str) -> str:
    return legacy_memory_intent(infer_memory_intent_v2(query))



def legacy_memory_intent(intent_v2: str) -> str:
    return MEMORY_INTENT_ALIASES.get(intent_v2, intent_v2)



def infer_memory_intent_v2(query: str) -> str:
    lowered = query.lower()
    if any(token in lowered for token in ("误导", "错误经验", "纠错", "冲突", "不要", "避免", "correction", "wrong", "misleading")):
        return "semantic_correction"
    if any(token in lowered for token in ("maintain", "治理", "维护", "淘汰", "刷新", "合并", "stale", "archive", "refresh")):
        return "memory_maintenance"
    if any(token in lowered for token in ("日志", "报错", "错误", "异常", "失败", "崩溃", "incident", "log", "traceback", "exception")):
        return "runtime_log_diagnosis"
    if any(token in lowered for token in ("业务语义", "业务含义", "语义", "semantic", "business meaning", "business_summary", "business_terms", "补充")):
        return "code_business_semantics"
    if any(token in lowered for token in ("如何", "怎么", "步骤", "流程", "方案", "procedure", "playbook", "workflow", "how to")):
        return "procedure_reuse"
    if any(token in lowered for token in ("代码", "函数", "文件", "调用", "当前", "source", "code", "function", "file", "在哪里", "位置", "path")):
        return "code_location"
    return "general_context"



def query_intent_profile(query: str) -> dict[str, Any]:
    intent_v2 = infer_memory_intent_v2(query)
    intent = legacy_memory_intent(intent_v2)
    preferred: dict[str, list[str]] = {
        "code_current": ["wiki_matches", "code_log_matches", "edge_matches", "semantic_patch"],
        "code_location": ["wiki_matches", "code_log_matches", "edge_matches"],
        "code_business_semantics": ["wiki_matches", "semantic_patch", "semantic_facts", "correction_guard"],
        "runtime_log_diagnosis": ["code_log_matches", "incident_trace_matches", "edge_matches", "reusable_procedure", "correction_guard"],
        "incident_diagnosis": ["code_log_matches", "incident_trace_matches", "edge_matches", "reusable_procedure", "correction_guard"],
        "semantic_lookup": ["wiki_matches", "semantic_facts", "semantic_patch", "correction_guard"],
        "semantic_correction": ["correction_guard", "semantic_patch", "semantic_facts", "wiki_matches"],
        "correction_guard": ["correction_guard", "semantic_patch", "semantic_facts"],
        "procedure_reuse": ["reusable_procedure", "incident_trace_matches", "semantic_facts"],
        "memory_maintenance": ["blocked_memory_notes", "semantic_patch", "correction_guard", "semantic_facts"],
        "general_context": ["semantic_facts", "wiki_matches", "reusable_procedure", "historical_reflection"],
    }
    return {
        "intent": intent,
        "intent_v2": intent_v2,
        "legacy_intent": intent,
        "preferred_lanes": preferred.get(intent_v2, preferred.get(intent, preferred["general_context"])),
        "interference_policy": {
            "code_current": "prefer current code/wiki/log anchors over broad procedure memories",
            "code_location": "prefer current code/wiki/log anchors and block broad procedure memories",
            "code_business_semantics": "prefer current business semantics, semantic patches, and correction guards",
            "runtime_log_diagnosis": "prefer logs, incident traces, and verified procedures with source cases",
            "incident_diagnosis": "prefer logs, incident traces, and verified procedures with source cases",
            "semantic_lookup": "prefer current business semantics and semantic patch guardrails",
            "semantic_correction": "prefer correction guardrails and semantic patches; keep procedure advice out of main context",
            "procedure_reuse": "prefer verified reusable procedure experience",
            "memory_maintenance": "prefer governance notes and records needing review",
        }.get(intent_v2, "prefer source-backed and high-quality memories"),
    }



def text_for_reflection_gate(item: dict[str, Any]) -> str:
    fields = [
        "task",
        "summary",
        "mistake",
        "lesson",
        "future_rule",
        "problem",
        "reasoning_summary",
        "context_used",
        "what_worked",
        "what_failed",
        "hidden_assumptions",
        "negative_preconditions",
        "useful_followup_terms",
        "misleading_followup_terms",
        "inspection_targets",
        "final_verification_path",
        "related_cases",
        "verification_method",
        "reuse_feedback",
        "source_cases",
        "skill_candidate",
        "scope",
        "evidence",
        "trigger_condition",
        "anti_pattern",
        "repair_action",
        "applies_to",
        "does_not_apply_to",
        "anchor_type",
        "anchor_key",
        "semantic_field",
        "existing_value",
        "proposed_value",
        "patch_reason",
    ]
    return " ".join(str(item.get(field) or "") for field in fields)



def token_overlap_score(query: str, text: str) -> float:
    query_set = {token for token in query_tokens(query) if len(token) > 1}
    text_set = {token for token in query_tokens(text) if len(token) > 1}
    if not query_set or not text_set:
        return 0.0
    return len(query_set & text_set) / max(1, len(query_set))



def reflection_memory_lane(item: dict[str, Any]) -> str:
    experience_type = str(item.get("experience_type") or "")
    if experience_type == "procedure_experience":
        return "reusable_procedure"
    if experience_type == "correction_experience":
        return "correction_guard"
    if experience_type == "semantic_patch_experience":
        return "semantic_patch"
    return "historical_reflection"



def reflection_gate_decision(query: str, intent: str, item: dict[str, Any], intent_v2: str | None = None) -> dict[str, Any]:
    intent_v2 = intent_v2 or intent
    lane = reflection_memory_lane(item)
    text = text_for_reflection_gate(item)
    overlap = token_overlap_score(query, text)
    base_score = float(item.get("score") or 0)
    quality_score = float(item.get("quality_score") or 0.5)
    confidence = float(item.get("confidence") or 0.8)
    score = min(100.0, base_score * 4.0 + overlap * 40.0 + confidence * 10.0 + quality_score * 15.0)
    reasons: list[str] = []
    interference_penalty = 0.0
    interference_reasons: list[str] = []

    if overlap:
        reasons.append("query_terms_overlap_reflection")
    if confidence >= 0.8:
        reasons.append("confidence_ok")
    if item.get("verification_method"):
        score += 8
        reasons.append("has_verification_method")
    if item.get("source_cases"):
        score += 6
        reasons.append("has_source_cases")
    if item.get("last_outcome") == "misleading":
        score -= 35
        reasons.append("previously_misleading")
    if float(item.get("misleading_score") or 0.0) > 0:
        score -= min(25, float(item.get("misleading_score") or 0.0) * 25)
        reasons.append("explicit_misleading_score")
    feedback_penalty = float(item.get("feedback_penalty") or 0.0)
    if feedback_penalty:
        score -= feedback_penalty
        reasons.append("retrieval_feedback_penalty")
    usage_bonus = float(item.get("usage_feedback_bonus") or 0.0)
    usage_penalty = float(item.get("usage_feedback_penalty") or 0.0)
    if usage_bonus:
        score += usage_bonus * 30.0
        reasons.append("positive_usage_feedback")
    if usage_penalty:
        score -= usage_penalty * 40.0
        reasons.append("negative_usage_feedback")
    if quality_score >= 0.75:
        reasons.append("quality_score_high")
    elif quality_score < 0.45:
        score -= 12
        reasons.append("quality_score_low")

    if lane == "reusable_procedure":
        allowed = intent_v2 in {"procedure_reuse", "general_context", "runtime_log_diagnosis"} or intent in {"procedure_reuse", "general_context", "incident_diagnosis"}
        if allowed:
            score += 18
            reasons.append("procedure_lane_matches_intent")
        else:
            interference_penalty += 20
            reasons.append("procedure_lane_not_primary_for_intent")
    elif lane == "correction_guard":
        allowed = intent_v2 in {"semantic_correction", "runtime_log_diagnosis", "code_business_semantics"} or intent in {"correction_guard", "incident_diagnosis", "semantic_lookup"}
        if allowed:
            score += 12
            reasons.append("correction_guard_matches_intent")
        else:
            reasons.append("correction_guard_kept_out_of_main_context")
    elif lane == "semantic_patch":
        allowed = intent_v2 in {"code_business_semantics", "code_location", "semantic_correction", "memory_maintenance"} or intent in {"semantic_lookup", "code_current", "general_context"}
        if allowed:
            score += 15
            reasons.append("semantic_patch_matches_intent")
        else:
            reasons.append("semantic_patch_not_a_task_procedure")
    else:
        allowed = True
        reasons.append("legacy_reflection_allowed")

    if intent_v2 == "code_location" and lane in {"reusable_procedure", "historical_reflection"}:
        interference_penalty += 28
        interference_reasons.append("code_location_query_prefers_source_anchors")
        interference_reasons.append("code_current_query_prefers_source_anchors")
    elif intent == "code_current" and lane in {"reusable_procedure", "historical_reflection"}:
        interference_penalty += 18
        interference_reasons.append("code_current_query_prefers_source_anchors")
    if intent_v2 == "code_business_semantics" and lane == "reusable_procedure":
        interference_penalty += 18
        interference_reasons.append("code_business_semantics_prefers_semantic_anchors")
    elif intent == "semantic_lookup" and lane == "reusable_procedure":
        interference_penalty += 12
        interference_reasons.append("semantic_lookup_query_prefers_semantic_patch_or_code_wiki")
    if intent_v2 == "semantic_correction" and lane == "reusable_procedure":
        interference_penalty += 24
        interference_reasons.append("semantic_correction_keeps_procedures_out_of_main_context")
    if intent == "procedure_reuse" and lane in {"semantic_patch", "correction_guard"}:
        interference_penalty += 8
        interference_reasons.append("procedure_query_keeps_corrections_as_guardrails")
    if lane == "reusable_procedure" and not item.get("negative_preconditions") and intent_v2 != "procedure_reuse":
        interference_penalty += 12
        interference_reasons.append("procedure_missing_negative_preconditions_for_non_procedure_query")
    if overlap < 0.25 and lane == "reusable_procedure" and intent_v2 != "procedure_reuse":
        interference_penalty += 10
        interference_reasons.append("low_query_overlap_for_reusable_procedure")
    if interference_penalty:
        score -= interference_penalty

    return {
        "lane": lane,
        "allowed": allowed,
        "score": round(max(0.0, score), 2),
        "reasons": reasons,
        "intent_alignment": "aligned" if not interference_penalty and allowed else "guarded" if allowed else "blocked",
        "interference_penalty": round(interference_penalty, 2),
        "interference_reasons": interference_reasons,
    }



def blocked_memory_note(item: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    reasons = [*decision["reasons"], *decision.get("interference_reasons", [])]
    return {
        "id": item.get("id"),
        "experience_type": item.get("experience_type"),
        "memory_lane": decision["lane"],
        "gate_score": decision["score"],
        "intent_alignment": decision.get("intent_alignment"),
        "interference_penalty": decision.get("interference_penalty", 0.0),
        "reason": "; ".join(reasons) or "blocked by memory query firewall",
    }



def semantic_patch_note(item: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "anchor_type": item.get("anchor_type"),
        "anchor_key": item.get("anchor_key"),
        "semantic_field": item.get("semantic_field"),
        "existing_value": item.get("existing_value"),
        "proposed_value": item.get("proposed_value"),
        "patch_reason": item.get("patch_reason") or item.get("reasoning_summary"),
        "confidence": item.get("confidence"),
        "gate_score": decision["score"],
        "gate_reasons": decision["reasons"],
    }



def query_matches_anchor(query: str, item: dict[str, Any]) -> bool:
    anchor = " ".join(str(item.get(key) or "") for key in ("anchor_key", "semantic_field", "proposed_value"))
    return token_overlap_score(query, anchor) > 0



def gate_matches_by_intent(
    project: Project,
    query: str,
    matches: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    intent_v2 = infer_memory_intent_v2(query)
    intent = legacy_memory_intent(intent_v2)
    gated_matches: dict[str, list[dict[str, Any]]] = {
        key: [dict(item) for item in value]
        for key, value in matches.items()
    }
    main_reflections: list[dict[str, Any]] = []
    correction_guards: list[dict[str, Any]] = []
    semantic_patch_notes: list[dict[str, Any]] = []
    blocked_notes: list[dict[str, Any]] = []
    lane_counts: dict[str, int] = {
        "main_reflections": 0,
        "correction_guards": 0,
        "semantic_patch_notes": 0,
        "blocked_memory_notes": 0,
    }

    for item in gated_matches.get("reflections", []):
        decision = reflection_gate_decision(query, intent, item, intent_v2)
        item["memory_lane"] = decision["lane"]
        item["gate_score"] = decision["score"]
        item["gate_reasons"] = decision["reasons"]
        item["intent_alignment"] = decision["intent_alignment"]
        item["interference_penalty"] = decision["interference_penalty"]
        item["interference_reasons"] = decision["interference_reasons"]
        if decision["lane"] == "semantic_patch":
            if decision["allowed"] or query_matches_anchor(query, item):
                semantic_patch_notes.append(semantic_patch_note(item, decision))
                lane_counts["semantic_patch_notes"] += 1
            else:
                blocked_notes.append(blocked_memory_note(item, decision))
                lane_counts["blocked_memory_notes"] += 1
            continue
        if decision["lane"] == "correction_guard":
            if decision["allowed"] and decision["score"] >= 20:
                correction_guards.append(item)
                lane_counts["correction_guards"] += 1
            else:
                blocked_notes.append(blocked_memory_note(item, decision))
                lane_counts["blocked_memory_notes"] += 1
            continue
        if decision["allowed"] and decision["score"] >= 15:
            item["rerank_score"] = round(
                decision["score"]
                + float(item.get("quality_score") or 0.0) * 10.0
                + float(item.get("usage_feedback_bonus") or 0.0) * 30.0
                - float(item.get("usage_feedback_penalty") or 0.0) * 40.0
                - float(item.get("feedback_penalty") or 0.0),
                3,
            )
            main_reflections.append(item)
            lane_counts["main_reflections"] += 1
        else:
            blocked_notes.append(blocked_memory_note(item, decision))
            lane_counts["blocked_memory_notes"] += 1

    main_reflections.sort(key=lambda item: (item.get("gate_score", 0), item.get("score", 0), item.get("id", 0)), reverse=True)
    main_reflection_budget = MAIN_REFLECTION_BUDGETS.get(intent_v2, MAIN_REFLECTION_BUDGETS["general_context"])
    overflow_reflections = main_reflections[main_reflection_budget:]
    if overflow_reflections:
        for item in overflow_reflections:
            blocked_notes.append(
                {
                    "id": item.get("id"),
                    "experience_type": item.get("experience_type"),
                    "memory_lane": item.get("memory_lane"),
                    "gate_score": item.get("gate_score"),
                    "intent_alignment": "budget_overflow",
                    "interference_penalty": item.get("interference_penalty", 0.0),
                    "reason": f"main reflection lane budget for {intent_v2} is {main_reflection_budget}",
                }
            )
        lane_counts["blocked_memory_notes"] += len(overflow_reflections)
        main_reflections = main_reflections[:main_reflection_budget]
    correction_guards.sort(key=lambda item: (item.get("gate_score", 0), item.get("score", 0), item.get("id", 0)), reverse=True)
    semantic_patch_notes.sort(key=lambda item: (item.get("gate_score", 0), item.get("id", 0)), reverse=True)
    gated_matches["reflections"] = main_reflections
    conflict_notes = matching_conflict_notes(project, query, REFLECTION_LANE_LIMITS["conflict_notes"])
    intent_profile = query_intent_profile(query)
    return {
        "matches": gated_matches,
        "memory_intent": intent,
        "memory_intent_v2": intent_v2,
        "retrieval_lanes": {
            "counts": lane_counts,
            "intent_profile": intent_profile,
            "lane_budgets": {
                "main_reflections": main_reflection_budget,
                "correction_guards": REFLECTION_LANE_LIMITS["correction_guards"],
                "semantic_patch_notes": REFLECTION_LANE_LIMITS["semantic_patch_notes"],
                "blocked_memory_notes": REFLECTION_LANE_LIMITS["blocked_memory_notes"],
            },
            "policy": {
                "procedure_experience": "main context only when the query intent can reuse a procedure",
                "correction_experience": "guardrail lane; not injected as the main task direction by default",
                "semantic_patch_experience": "semantic patch lane; used to explain or repair code business semantics",
            },
        },
        "memory_brief": {
            "intent": intent,
            "intent_v2": intent_v2,
            "main_reflection_count": len(main_reflections),
            "correction_guard_count": len(correction_guards),
            "semantic_patch_count": len(semantic_patch_notes),
            "blocked_count": len(blocked_notes),
            "conflict_count": len(conflict_notes),
        },
        "correction_guards": correction_guards[: REFLECTION_LANE_LIMITS["correction_guards"]],
        "semantic_patch_notes": semantic_patch_notes[: REFLECTION_LANE_LIMITS["semantic_patch_notes"]],
        "blocked_memory_notes": blocked_notes[: REFLECTION_LANE_LIMITS["blocked_memory_notes"]],
        "conflict_notes": conflict_notes,
    }



def matching_conflict_notes(project: Project, query: str, limit: int) -> list[dict[str, Any]]:
    tokens = {token for token in query_tokens(query) if len(token) > 1}
    if not tokens:
        return []
    notes: list[dict[str, Any]] = []
    with connect(project) as conn:
        rows = conn.execute(
            """
            SELECT id, entity_type, target, field, existing, incoming, decision_note, replacement_source, observed_at
            FROM semantic_conflicts
            WHERE project_id = ? AND status = 'open'
            ORDER BY observed_at DESC, id DESC
            LIMIT 50
            """,
            (project.project_id,),
        ).fetchall()
    for row in rows:
        item = row_dict(row)
        text = " ".join(str(item.get(key) or "") for key in ("entity_type", "target", "field", "existing", "incoming", "decision_note"))
        if {token for token in query_tokens(text) if len(token) > 1} & tokens:
            notes.append(item)
            if len(notes) >= limit:
                break
    return notes
