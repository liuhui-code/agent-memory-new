# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import sqlite3
import re
from pathlib import Path
from typing import Any

from .active_learning_queue import build_active_learning_actions, build_active_learning_queue
from .code_wiki import semantic_followup_from_db
from .evidence_chain_quality import build_evidence_chain_summary, enrich_reflections_with_evidence_chains
from .graph_quality import (
    build_graph_quality,
    build_graph_quality_actions,
    build_graph_signal_quality,
    build_graph_signal_quality_actions,
    build_log_observability_gap_actions,
)
from .governance_action_budget import (
    annotate_governance_action_priorities,
    build_governance_action_budget,
    compact_maintain_plan_payload,
)
from .incident_trace_governance import build_incident_trace_actions
from .experience_maturity import score_experience_maturity
from .experience_usage import build_experience_usage_actions, fetch_experience_usage_summary
from .memory_tiers import build_memory_tier_actions, build_memory_tiers
from .models import ACTIVE_STATUS, GOVERNANCE_COLUMNS, Project, REVIEW_DUPLICATE_POOL_LIMIT, VALID_MEMORY_STATUSES
from .performance_scoring import (
    append_performance_sample,
    build_performance_sample,
    build_runtime_performance_actions,
    build_runtime_performance_summary,
    estimate_payload_tokens,
    monotonic_ms,
)
from .quality_scoring import build_quality_report
from .quality_gate_eval import (
    build_quality_gate_failure_actions,
    build_recurring_quality_gate_failure_actions,
    load_quality_gate_history_report,
    load_quality_gate_snapshot,
)
from .query import collect_matches, infer_followup_focus, rank_followup_seed_terms, suggested_followup_terms
from .records import output, parse_ids, row_dict, table_for_type
from .retrieval_feedback import fetch_open_retrieval_feedback
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .task_trace_governance import build_task_trace_actions
from .text import json_list, tokenize, unique_list
from .usage_samples import record_governance_usage



from .governance_review import reflection_experience_type
from .governance_utils import (
    extract_path_like_values,
    normalized_text,
    stable_unique_strings,
    token_set,
)

def build_correction_targets(row: dict[str, Any]) -> dict[str, Any]:
    file_paths = extract_path_like_values(
        row.get("source_cases"),
        row.get("inspection_targets"),
        row.get("context_used"),
        row.get("evidence"),
    )
    return {
        "file_paths": file_paths,
        "inspection_targets": json_list(row.get("inspection_targets")),
        "useful_terms": json_list(row.get("useful_followup_terms")),
        "misleading_terms": json_list(row.get("misleading_followup_terms")),
        "source_cases": json_list(row.get("source_cases")),
    }



def build_correction_learning_rule(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_memory_type": "code_wiki_business_semantics",
        "correction_trigger": row.get("trigger_condition") or row.get("problem") or "",
        "incorrect_understanding": stable_unique_strings(
            [*(json_list(row.get("misleading_followup_terms"))), *(json_list(row.get("what_failed")))]
        ),
        "corrected_understanding": stable_unique_strings(
            [
                str(row.get("future_rule") or ""),
                str(row.get("lesson") or ""),
                *(json_list(row.get("what_worked"))),
            ]
        ),
        "correction_reason": row.get("reasoning_summary") or row.get("summary") or "",
        "source_evidence": stable_unique_strings(
            [
                str(row.get("evidence") or ""),
                str(row.get("verification_method") or ""),
                str(row.get("final_verification_path") or ""),
            ]
        ),
        "repair_action": row.get("repair_action") or "",
        "prevention_rule": row.get("future_rule") or "",
    }



def build_correction_learn_payload_template(project: Project, row: dict[str, Any]) -> dict[str, Any]:
    targets = build_correction_targets(row)
    file_paths = targets["file_paths"]
    followup = semantic_followup_from_db(project, file_paths) if file_paths else None
    if followup:
        return followup["followup_payload_template"]

    hint_terms = stable_unique_strings(
        [
            *targets["useful_terms"],
            *targets["misleading_terms"],
            str(row.get("problem") or ""),
            str(row.get("trigger_condition") or ""),
        ]
    )
    hint_context = stable_unique_strings(
        [
            str(row.get("reasoning_summary") or ""),
            str(row.get("evidence") or ""),
            str(row.get("verification_method") or ""),
            *targets["inspection_targets"],
        ]
    )
    return {
        "files": [
            {
                "file_path": file_path,
                "business_summary": "",
                "business_terms": [],
                "hint_terms": hint_terms[:12],
                "hint_context": hint_context[:8],
                "symbols": [],
                "logs": [],
            }
            for file_path in file_paths
        ]
    }



def build_semantic_patch_review_action(row: dict[str, Any]) -> dict[str, Any]:
    anchor_type = str(row.get("anchor_type") or "")
    anchor_key = str(row.get("anchor_key") or "")
    semantic_field = str(row.get("semantic_field") or "")
    proposed_value = str(row.get("proposed_value") or "")
    return {
        "action": "review_semantic_patch",
        "governance_lane": "learn_semantic_repair",
        "type": "reflection",
        "id": row["id"],
        "experience_type": "semantic_patch_experience",
        "reason": "reflection proposes a code business semantic patch tied to a concrete anchor",
        "risk": "medium",
        "requires_confirmation": True,
        "command": None,
        "anchor_type": anchor_type,
        "anchor_key": anchor_key,
        "semantic_field": semantic_field,
        "existing_value": row.get("existing_value"),
        "proposed_value": proposed_value,
        "patch_reason": row.get("patch_reason") or row.get("reasoning_summary") or row.get("summary"),
        "confidence": row.get("confidence"),
        "apply_policy": {
            "empty_target_field": "apply as a learn-business semantic enrichment",
            "different_existing_value": "record or review through semantic_conflicts before replacing",
            "missing_anchor": "keep review-only and refresh the learned code scope first",
        },
        "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
        "learn_business_payload_template": build_semantic_patch_payload_template(row),
        "workflow_steps": [
            "Read the anchored current source record before applying the patch.",
            "Compare existing business semantics with the proposed value and patch reason.",
            "Apply through learn-business when the patch is supported by current source.",
            "Use semantic_conflicts review if the current value is different and non-empty.",
        ],
    }



def build_semantic_patch_payload_template(row: dict[str, Any]) -> dict[str, Any]:
    anchor_type = str(row.get("anchor_type") or "")
    anchor_key = str(row.get("anchor_key") or "")
    semantic_field = str(row.get("semantic_field") or "")
    proposed_value = str(row.get("proposed_value") or "")
    file_path = anchor_key.split("::", 1)[0] if "::" in anchor_key else anchor_key
    file_payload: dict[str, Any] = {
        "file_path": file_path,
        "business_summary": "",
        "business_terms": [],
        "hint_terms": stable_unique_strings(
            [
                proposed_value,
                str(row.get("patch_reason") or ""),
                str(row.get("problem") or ""),
                *json_list(row.get("useful_followup_terms")),
            ]
        )[:12],
        "hint_context": stable_unique_strings(
            [
                str(row.get("evidence") or ""),
                str(row.get("verification_method") or ""),
                str(row.get("patch_reason") or row.get("reasoning_summary") or ""),
            ]
        )[:8],
        "symbols": [],
        "logs": [],
    }
    if anchor_type == "code_file" and semantic_field == "business_summary":
        file_payload["business_summary"] = proposed_value
    elif anchor_type == "code_file" and semantic_field == "business_terms":
        file_payload["business_terms"] = [proposed_value]
    elif anchor_type == "code_symbol":
        symbol = anchor_key.split("::", 1)[1] if "::" in anchor_key else anchor_key
        file_payload["symbols"].append(
            {
                "symbol": symbol,
                "business_summary": proposed_value if semantic_field == "business_summary" else "",
                "business_terms": [proposed_value] if semantic_field == "business_terms" else [],
            }
        )
    elif anchor_type == "code_log_statement":
        message_template = anchor_key.split("::", 1)[1] if "::" in anchor_key else anchor_key
        file_payload["logs"].append(
            {
                "message_template": message_template,
                semantic_field: proposed_value,
            }
        )
    return {"files": [file_payload]}



def correction_repair_workflow_steps() -> list[str]:
    return [
        "Read the affected file, symbol, or log targets in current source.",
        "Compare the stored business meaning against the correction experience evidence and verification method.",
        "Rewrite the learn-business payload for the affected records instead of re-learning a broad directory.",
        "Re-run maintain-plan or query to confirm the semantic misunderstanding is reduced.",
    ]



def build_retrieval_interference_candidates(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in rows:
        experience_type = reflection_experience_type(row)
        if not experience_type:
            continue
        last_outcome = str(row.get("last_outcome") or "")
        use_count = int(row.get("use_count") or 0)
        misleading_score = float(row.get("misleading_score") or 0.0)
        if last_outcome != "misleading" and misleading_score < 0.6 and use_count < 3:
            continue
        candidates.append(
            {
                "action": "review_retrieval_interference",
                "governance_lane": "retrieval_interference",
                "type": "reflection",
                "id": row["id"],
                "experience_type": experience_type,
                "reason": "reflection may be over-retrieved or has evidence of misleading reuse",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
                "last_outcome": last_outcome,
                "use_count": use_count,
                "misleading_score": misleading_score,
                "suggested_actions": [
                    "lower confidence",
                    "mark stale if the misleading signal is confirmed",
                    "tighten trigger_condition",
                    "tighten does_not_apply_to",
                    "move correction content into guardrail-only usage",
                ],
            }
        )
    candidates.sort(key=lambda item: (item["last_outcome"] == "misleading", item["misleading_score"], item["use_count"]), reverse=True)
    return candidates[:limit]



def prepare_conflict_context(row: dict[str, Any]) -> dict[str, Any]:
    inspection_targets = json_list(row.get("inspection_targets"))
    scope = normalized_text(row.get("scope"))
    trigger = normalized_text(row.get("trigger_condition"))
    return {
        "scope": scope,
        "scope_tokens": token_set(str(row.get("scope") or "")) or ({scope} if scope else set()),
        "trigger": trigger,
        "trigger_tokens": token_set(str(row.get("trigger_condition") or "")) or ({trigger} if trigger else set()),
        "inspection_targets": inspection_targets,
        "inspection_target_keys": {normalized_text(value) for value in inspection_targets},
        "future_rule": normalized_text(row.get("future_rule")),
        "repair_action": normalized_text(row.get("repair_action")),
        "repair_tokens": token_set(str(row.get("repair_action") or "")),
        "anchor_key": normalized_text(row.get("anchor_key")),
        "semantic_field": normalized_text(row.get("semantic_field")),
        "proposed_value": normalized_text(row.get("proposed_value")),
    }


def prepared_overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def prepared_shared_context(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {
        "shared_scope": bool(left["scope"] and left["scope"] == right["scope"]),
        "shared_trigger": bool(left["trigger"] and left["trigger"] == right["trigger"]),
        "shared_inspection_targets": stable_unique_strings([
            target for target in left["inspection_targets"]
            if normalized_text(target) in right["inspection_target_keys"]
        ]),
        "scope_overlap": prepared_overlap(left["scope_tokens"], right["scope_tokens"]),
        "trigger_overlap": prepared_overlap(left["trigger_tokens"], right["trigger_tokens"]),
    }


def candidate_conflict_pairs(
    prepared: list[tuple[dict[str, Any], str | None, dict[str, Any]]],
) -> list[tuple[int, int]]:
    semantic_groups: dict[tuple[str, str], list[int]] = {}
    trigger_postings: dict[tuple[str, str], list[int]] = {}
    scope_postings: dict[tuple[str, str], list[int]] = {}
    for index, (_row, experience_type, context) in enumerate(prepared):
        if experience_type == "semantic_patch_experience":
            semantic_groups.setdefault(
                (context["anchor_key"], context["semantic_field"]), []
            ).append(index)
            continue
        if experience_type not in {"procedure_experience", "correction_experience"}:
            continue
        for token in context["trigger_tokens"]:
            trigger_postings.setdefault((experience_type, token), []).append(index)
        for token in context["scope_tokens"]:
            scope_postings.setdefault((experience_type, token), []).append(index)

    pairs: set[tuple[int, int]] = set()
    for indexes in semantic_groups.values():
        for offset, older_index in enumerate(indexes):
            pairs.update((older_index, newer_index) for newer_index in indexes[offset + 1:])
    for older_index, (_row, experience_type, context) in enumerate(prepared):
        if experience_type not in {"procedure_experience", "correction_experience"}:
            continue
        trigger_candidates = {
            index
            for token in context["trigger_tokens"]
            for index in trigger_postings.get((experience_type, token), [])
            if index > older_index
        }
        scope_candidates = {
            index
            for token in context["scope_tokens"]
            for index in scope_postings.get((experience_type, token), [])
            if index > older_index
        }
        pairs.update((older_index, newer_index) for newer_index in trigger_candidates & scope_candidates)
    return sorted(pairs)


def build_experience_conflict_candidates(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    ordered_rows = sorted(rows, key=lambda item: int(item.get("id") or 0))
    prepared = [
        (row, reflection_experience_type(row), prepare_conflict_context(row))
        for row in ordered_rows
    ]
    for older_index, newer_index in candidate_conflict_pairs(prepared):
        older, older_type, older_ctx = prepared[older_index]
        newer, _newer_type, newer_ctx = prepared[newer_index]
        if older_type == "semantic_patch_experience":
            older_value = older_ctx["proposed_value"]
            newer_value = newer_ctx["proposed_value"]
            if not older_value or not newer_value or older_value == newer_value:
                continue
            candidates.append(
                {
                    "action": "review_experience_conflict",
                    "governance_lane": "experience_conflict",
                    "type": "reflection",
                    "id": None,
                    "experience_type": older_type,
                    "conflict_kind": "semantic_patch_conflict",
                    "older_reflection_id": int(older["id"]),
                    "newer_reflection_id": int(newer["id"]),
                    "anchor_type": older.get("anchor_type"),
                    "anchor_key": older.get("anchor_key"),
                    "semantic_field": older.get("semantic_field"),
                    "older_proposed_value": older.get("proposed_value"),
                    "newer_proposed_value": newer.get("proposed_value"),
                    "reason": "newer semantic patch proposes a different value for the same anchor and field",
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": None,
                    "suggested_actions": [
                        "review which semantic summary matches current source and logs",
                        "mark one patch superseded after verification",
                        "record any remaining ambiguity in semantic_conflicts",
                    ],
                }
            )
            continue

        context = prepared_shared_context(older_ctx, newer_ctx)
        if not context["shared_trigger"] and context["trigger_overlap"] < 0.8:
            continue
        if not context["shared_scope"] and context["scope_overlap"] < 0.5:
            continue
        older_rule = older_ctx["future_rule"]
        newer_rule = newer_ctx["future_rule"]
        older_action = older_ctx["repair_action"]
        newer_action = newer_ctx["repair_action"]
        if not older_action or not newer_action:
            continue
        if older_rule == newer_rule and older_action == newer_action:
            continue
        if prepared_overlap(older_ctx["repair_tokens"], newer_ctx["repair_tokens"]) >= 0.75:
            continue
        candidates.append(
            {
                "action": "review_experience_conflict",
                "governance_lane": "experience_conflict",
                "type": "reflection",
                "id": None,
                "experience_type": older_type,
                "conflict_kind": "procedure_rule_conflict" if older_type == "procedure_experience" else "correction_rule_conflict",
                "older_reflection_id": int(older["id"]),
                "newer_reflection_id": int(newer["id"]),
                "shared_trigger_condition": older.get("trigger_condition") or newer.get("trigger_condition"),
                "shared_scope_value": older.get("scope") or newer.get("scope"),
                "shared_inspection_targets": context["shared_inspection_targets"],
                "older_future_rule": older.get("future_rule"),
                "newer_future_rule": newer.get("future_rule"),
                "older_repair_action": older.get("repair_action"),
                "newer_repair_action": newer.get("repair_action"),
                "reason": "newer experience changes the recommended workflow for a similar trigger and scope",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
                "suggested_actions": [
                    "review which trigger boundaries are still valid",
                    "tighten negative_preconditions or does_not_apply_to",
                    "mark the outdated guidance stale if the newer rule is confirmed",
                ],
            }
        )
    candidates.sort(key=lambda item: (item["newer_reflection_id"], item["older_reflection_id"]), reverse=True)
    return candidates[:limit]
