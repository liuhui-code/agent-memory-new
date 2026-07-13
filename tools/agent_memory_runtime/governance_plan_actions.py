# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .governance_action_budget import annotate_governance_action_priorities
from .governance_corrections import (
    build_correction_learn_payload_template,
    build_correction_learning_rule,
    build_correction_targets,
    build_experience_conflict_candidates,
    build_retrieval_interference_candidates,
    build_semantic_patch_review_action,
    correction_repair_workflow_steps,
)
from .governance_incidents import build_log_design_gap_candidates
from .governance_learn_actions import (
    build_followup_focus,
    build_learn_business_payload_template_for_paths,
    build_suggested_query_terms,
    find_reflections_linked_to_paths,
    query_followup_workflow_steps,
    semantic_enrichment_workflow_steps,
)
from .governance_review import reflection_experience_type, runtime_feedback_summary
from .governance_skill_artifacts import annotate_skill_pattern_artifacts
from .governance_skill_candidates import build_skill_pattern_candidates, is_complete_experience_candidate
from .governance_utils import (
    EXPERIENCE_CANDIDATE_FIELDS,
    TRACE_CASE_FIELDS,
    infer_governance_lane,
    stable_unique_strings,
)


def build_maintain_plan_actions(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    project = ctx["project"]
    args = ctx["args"]
    review = ctx["review"]
    reflection_quality = ctx["reflection_quality"]
    query_misses = ctx["query_misses"]
    semantic_conflicts = ctx["semantic_conflicts"]
    refresh_drifts = ctx["refresh_drifts"]
    semantic_gap_targets = ctx["semantic_gap_targets"]
    learn_business_payload_template = ctx["learn_business_payload_template"]
    incident_strategy_candidates = ctx["incident_strategy_candidates"]
    recurring_incident_fingerprint_candidates = ctx["recurring_incident_fingerprint_candidates"]
    retrieval_interference_candidates = ctx["retrieval_interference_candidates"]
    experience_conflict_candidates = ctx["experience_conflict_candidates"]
    incident_trace_actions = ctx["incident_trace_actions"]
    graph_quality_actions = ctx["graph_quality_actions"]
    graph_signal_quality_actions = ctx["graph_signal_quality_actions"]
    log_observability_gap_actions = ctx["log_observability_gap_actions"]
    quality_gate_actions = ctx["quality_gate_actions"]
    recurring_quality_gate_actions = ctx["recurring_quality_gate_actions"]
    runtime_performance_actions = ctx["runtime_performance_actions"]
    experience_usage_actions = ctx["experience_usage_actions"]
    memory_tier_actions = ctx["memory_tier_actions"]
    task_trace_actions = ctx["task_trace_actions"]
    active_learning_actions = ctx["active_learning_actions"]
    retrieval_feedback_actions = ctx["retrieval_feedback_actions"]
    calibration_feedback_actions = ctx["calibration_feedback_actions"]
    quality_governance_actions = ctx["quality_governance_actions"]
    weak_evidence_chain_actions = ctx["weak_evidence_chain_actions"]
    maturity_governance_actions = ctx["maturity_governance_actions"]

    actions: list[dict[str, Any]] = []

    for row in review["stale_memories"]:
        kind = "semantic" if "fact" in row else "reflection"
        reason = row.get("stale_reason") or "stale memory should be archived, refreshed, or merged"
        actions.append(
            {
                "action": "archive",
                "type": kind,
                "id": row["id"],
                "reason": reason,
                "risk": "low",
                "requires_confirmation": True,
                "command": (
                    "python tools/agent_memory.py maintain-status "
                    f"--project . --type {kind} --id {row['id']} --status archived "
                    f"--reason {json.dumps(reason, ensure_ascii=False)}"
                ),
            }
        )

    for candidate in review["duplicate_candidates"]:
        actions.append(
            {
                "action": "review",
                "type": candidate["type"],
                "ids": candidate["ids"],
                "reason": candidate["reason"],
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
            }
        )

    for row in review["low_confidence"]:
        kind = "semantic" if "fact" in row else "reflection"
        actions.append(
            {
                "action": "verify",
                "type": kind,
                "id": row["id"],
                "reason": "low-confidence memory needs source verification",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
            }
        )

    for item in reflection_quality["reflections"]:
        if item["suggested_action"] == "mark_stale":
            reason = item["reason"]
            actions.append(
                {
                    "action": "mark_stale",
                    "type": "reflection",
                    "id": item["id"],
                    "reason": reason,
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": (
                        "python tools/agent_memory.py maintain-status "
                        f"--project . --type reflection --id {item['id']} --status stale "
                        f"--reason {json.dumps(reason, ensure_ascii=False)}"
                    ),
                }
            )
        elif item["suggested_action"] == "rewrite":
            actions.append(
                {
                    "action": "rewrite_reflection",
                    "type": "reflection",
                    "id": item["id"],
                    "reason": ", ".join(item["issues"]),
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": None,
                }
            )

    for row in review["unreviewed_reflections"]:
        experience_type = reflection_experience_type(row)
        if experience_type == "semantic_patch_experience":
            actions.append(build_semantic_patch_review_action(row))
            continue
        if is_complete_experience_candidate(row):
            if experience_type == "correction_experience":
                correction_targets = build_correction_targets(row)
                correction_payload_template = build_correction_learn_payload_template(project, row)
                actions.append(
                    {
                        "action": "review_correction_experience",
                        "governance_lane": "learn_semantic_repair",
                        "type": "reflection",
                        "id": row["id"],
                        "experience_type": experience_type,
                        "governance_path": "learn_semantic_repair",
                        "reason": "reflection is a semantic correction candidate for learn governance",
                        "risk": "medium",
                        "requires_confirmation": True,
                        "command": None,
                        "candidate_fields": EXPERIENCE_CANDIDATE_FIELDS,
                        "verification_method": row.get("verification_method"),
                        "source_cases": row.get("source_cases"),
                        "correction_targets": correction_targets,
                        "learning_rule_draft": build_correction_learning_rule(row),
                        "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
                        "learn_business_payload_template": correction_payload_template,
                        "workflow_steps": correction_repair_workflow_steps(),
                        "runtime_feedback_summary": runtime_feedback_summary(row),
                        **{field: row.get(field) for field in TRACE_CASE_FIELDS},
                    }
                )
            else:
                actions.append(
                    {
                        "action": "promote_experience_candidate",
                        "governance_lane": "skill_evolution",
                        "type": "reflection",
                        "id": row["id"],
                        "experience_type": experience_type or "procedure_experience",
                        "reason": "reflection has enough structure to review as an experience candidate",
                        "risk": "medium",
                        "requires_confirmation": True,
                        "command": None,
                        "candidate_fields": EXPERIENCE_CANDIDATE_FIELDS,
                        "skill_candidate": row.get("skill_candidate"),
                        "verification_method": row.get("verification_method"),
                        "source_cases": row.get("source_cases"),
                        "runtime_feedback_summary": runtime_feedback_summary(row),
                        **{field: row.get(field) for field in TRACE_CASE_FIELDS},
                    }
                )
        else:
            actions.append(
                {
                    "action": "promote_or_mark_reviewed",
                    "type": "reflection",
                    "id": row["id"],
                    "experience_type": experience_type,
                    "reason": "unreviewed reflection may contain a durable lesson",
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": None,
                }
            )

    for row in review["unreviewed_episodes"]:
        actions.append(
            {
                "action": "promote_or_archive",
                "type": "episode",
                "id": row["id"],
                "reason": "unreviewed episode may contain durable project knowledge",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
            }
            )

    actions.extend(retrieval_interference_candidates)
    actions.extend(experience_conflict_candidates)
    actions.extend(incident_trace_actions)
    actions.extend(quality_governance_actions)
    actions.extend(weak_evidence_chain_actions)
    actions.extend(maturity_governance_actions)
    actions.extend(graph_quality_actions)
    actions.extend(graph_signal_quality_actions)
    actions.extend(log_observability_gap_actions)
    actions.extend(quality_gate_actions)
    actions.extend(recurring_quality_gate_actions)
    actions.extend(runtime_performance_actions)
    actions.extend(experience_usage_actions)
    actions.extend(memory_tier_actions)
    actions.extend(task_trace_actions)
    actions.extend(active_learning_actions)
    actions.extend(retrieval_feedback_actions)
    actions.extend(calibration_feedback_actions)

    for candidate in build_skill_pattern_candidates(project, review["unreviewed_reflections"]):
        candidate = annotate_skill_pattern_artifacts(project.root, candidate)
        actions.append(
            {
                "action": "review_skill_pattern_candidate",
                "governance_lane": "skill_evolution",
                "type": "skill_pattern",
                "id": None,
                "reason": "multiple procedure experiences point to the same reusable skill pattern",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
                "write_command_template": (
                    "python tools/agent_memory.py maintain-skill-draft "
                    f"--project . --pattern-name {json.dumps(candidate['pattern_name'], ensure_ascii=False)} --json"
                ),
                "package_command_template": (
                    "python tools/agent_memory.py maintain-skill-package "
                    f"--project . --pattern-name {json.dumps(candidate['pattern_name'], ensure_ascii=False)} --json"
                ),
                **candidate,
            }
        )

    for candidate in incident_strategy_candidates:
        actions.append(
            {
                "action": "review_incident_strategy_candidate",
                "governance_lane": "skill_evolution",
                "type": "incident_strategy",
                "id": None,
                "reason": "multiple runtime-log-backed procedure experiences point to the same incident diagnosis strategy",
                "risk": "medium",
                "requires_confirmation": True,
                "command": None,
                "write_command_template": (
                    "python tools/agent_memory.py maintain-incident-strategy-draft "
                    f"--project . --strategy-name {json.dumps(candidate['strategy_name'], ensure_ascii=False)} --json"
                ),
                **candidate,
            }
        )

    for candidate in recurring_incident_fingerprint_candidates:
        actions.append(
            {
                "action": "review_recurring_incident_fingerprint",
                "governance_lane": "incident_recurrence",
                "type": "incident_fingerprint",
                "id": None,
                "reason": "multiple runtime-log-backed reflections share the same lightweight incident fingerprint",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                "write_command_template": (
                    "python tools/agent_memory.py maintain-incident-fingerprint-draft "
                    f"--project . --fingerprint-name {json.dumps(candidate['fingerprint_name'], ensure_ascii=False)} --json"
                ),
                **candidate,
            }
        )

    for candidate in build_log_design_gap_candidates(project, review["unreviewed_reflections"]):
        actions.append(
            {
                "action": "review_log_design_gap",
                "governance_lane": "log_diagnosis",
                "type": "log_design",
                "id": None,
                "reason": "repeated runtime-log-backed diagnosis points to a narrow log design gap worth fixing",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                **candidate,
            }
        )

    for row in query_misses:
        followup_focus = build_followup_focus(project, row["query"])
        suggested_query_terms = build_suggested_query_terms(project, row["query"], learn_business_payload_template)
        actions.append(
            {
                "action": "review_query_miss",
                "governance_lane": "log_diagnosis",
                "type": "query_miss",
                "id": row["id"],
                "query": row["query"],
                "source": row["source"],
                "miss_count": row.get("miss_count") or 1,
                "last_seen_at": row.get("last_seen_at") or row.get("created_at"),
                "reason": "query had no memory or wiki matches",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                "suggested_fixes": [
                    "learn_missing_scope",
                    "add_business_terms",
                    "rewrite_reflection",
                    "ignore_noise",
                ],
                "followup_focus": followup_focus,
                "suggested_query_terms": suggested_query_terms,
                "query_command_template": "python tools/agent_memory.py search --project . --query '<query>' --json",
                "query_workflow_steps": query_followup_workflow_steps(),
                "semantic_gap_targets": semantic_gap_targets,
                "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
                "learn_business_payload_template": learn_business_payload_template,
                "workflow_steps": semantic_enrichment_workflow_steps(),
            }
        )

    for conflict in semantic_conflicts:
        actions.append(
            {
                "action": "review_semantic_conflict",
                "governance_lane": "semantic_conflict",
                "type": "semantic_conflict",
                "id": None,
                "target": conflict["target"],
                "field": conflict["field"],
                "existing": conflict["existing"],
                "incoming": conflict["incoming"],
                "source_command": conflict["source_command"],
                "observed_at": conflict["observed_at"],
                "decision_note": conflict.get("decision_note"),
                "replacement_source": conflict.get("replacement_source"),
                "reason": "incoming semantic summary conflicts with existing stored summary",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                "apply_command_template": f"python tools/agent_memory.py conflict-apply --project . --id {conflict['id']} --resolution \"<decision>\"",
            }
        )

    for drift in refresh_drifts:
        drift_files = stable_unique_strings(
            [
                *(drift.get("added_files") or []),
                *(drift.get("changed_files") or []),
            ]
        )
        payload_template = build_learn_business_payload_template_for_paths(project, drift_files)
        actions.append(
            {
                "action": "review_semantic_drift",
                "governance_lane": "learn_semantic_repair",
                "type": "learn_scope",
                "id": drift["scope_id"],
                "reason": "refreshed learned scope changed and may need business-semantics review",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                **drift,
                "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
                "learn_business_payload_template": payload_template,
                "workflow_steps": semantic_enrichment_workflow_steps(),
            }
        )
        removed_reflection_ids = find_reflections_linked_to_paths(project, drift.get("removed_files") or [])
        if removed_reflection_ids:
            actions.append(
                    {
                        "action": "mark_experience_stale_if_anchor_removed",
                        "governance_lane": "experience_staleness",
                        "type": "reflection",
                    "id": None,
                    "reason": "one or more active reflections reference files removed from a refreshed learned scope",
                    "risk": "medium",
                    "requires_confirmation": True,
                    "command": None,
                    "scope_id": drift["scope_id"],
                    "removed_files": drift.get("removed_files") or [],
                    "linked_reflection_ids": removed_reflection_ids,
                }
            )
            affected_patterns = stable_unique_strings(
                [
                    str(row.get("skill_candidate") or "")
                    for row in review["unreviewed_reflections"]
                    if int(row.get("id") or 0) in removed_reflection_ids and row.get("skill_candidate")
                ]
            )
            for pattern_name in affected_patterns:
                actions.append(
                    {
                        "action": "review_skill_pattern_staleness",
                        "governance_lane": "experience_staleness",
                        "type": "skill_pattern",
                        "id": None,
                        "reason": "a clustered skill pattern depends on reflections anchored to removed files",
                        "risk": "medium",
                        "requires_confirmation": True,
                        "command": None,
                        "pattern_name": pattern_name,
                        "scope_id": drift["scope_id"],
                        "removed_files": drift.get("removed_files") or [],
                        "linked_reflection_ids": removed_reflection_ids,
                    }
                )

    if any(semantic_gap_targets.values()):
        actions.append(
            {
                "action": "add_business_terms",
                "governance_lane": "learn_semantic_repair",
                "type": "code_memory",
                "id": None,
                "reason": "learned code records are missing business summaries or business terms",
                "risk": "low",
                "requires_confirmation": False,
                "command": None,
                "semantic_gap_targets": semantic_gap_targets,
                "command_template": "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
                "learn_business_payload_template": learn_business_payload_template,
                "workflow_steps": semantic_enrichment_workflow_steps(),
            }
        )

    for action in actions:
        action.setdefault("governance_lane", infer_governance_lane(action))
    return actions
