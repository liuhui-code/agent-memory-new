# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "agent-context-sufficiency/v1"


def diagnosis_sufficiency(
    handoff: dict[str, Any],
    evidence_gaps: list[str],
    source_freshness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe whether retrieval can begin Agent inspection, never diagnosis."""
    code_anchors = records(handoff.get("code_anchors"))
    log_anchors = records(handoff.get("log_anchors"))
    paths = records(record(handoff.get("path_context")).get("path_candidates"))
    source_locatable = any(str(item.get("file_path") or "").strip() for item in code_anchors)
    freshness = str(record(source_freshness).get("status") or "unknown")
    reasons = freshness_reasons(freshness)
    if reasons:
        status, action = "refresh_required", "refresh_learned_scope"
    elif source_locatable:
        status, action = "ready_for_agent_inspection", "inspect_primary_source_anchor"
    elif code_anchors or log_anchors or paths:
        status, action = "needs_focused_expansion", "request_one_source_locatable_anchor"
        reasons.append("no_source_locatable_code_anchor")
    else:
        status, action = "insufficient_evidence", "narrow_query_or_learn_relevant_scope"
        reasons.append("no_inspectable_retrieval_evidence")
    return response(
        "diagnosis", status, action, reasons, evidence_gaps,
        {
            "source_locatable_code_anchor": source_locatable,
            "log_anchor_count": len(log_anchors),
            "path_candidate_count": len(paths),
        },
        "Read anchored source or compare real logs; Agent determines hypotheses and diagnosis.",
    )


def design_sufficiency(payload: dict[str, Any]) -> dict[str, Any]:
    """Describe whether context can orient a design conversation, not select it."""
    request = record(payload.get("request"))
    repository = record(payload.get("current_repository"))
    anchors = records(repository.get("source_anchors"))
    constraints = records(record(payload.get("project_context")).get("task_constraints"))
    gaps = strings(payload.get("evidence_gaps"))
    freshness = str(record(repository.get("snapshot")).get("freshness") or "unknown")
    reasons = freshness_reasons(freshness)
    if reasons:
        status, action = "refresh_required", "refresh_or_confirm_current_source"
    elif anchors:
        status = "ready_for_agent_directed_refinement" if request.get("query_stage") == "agent_directed_expansion" else "ready_for_orientation"
        action = "inspect_source_and_confirm_design_constraints"
    else:
        status, action = "needs_anchor_confirmation", "supply_or_retrieve_current_source_anchor"
        reasons.append("no_repository_source_anchor")
    return response(
        "design", status, action, reasons, gaps,
        {
            "repository_source_anchor_count": len(anchors),
            "explicit_constraint_count": len(constraints),
            "agent_directed_stage": request.get("query_stage") == "agent_directed_expansion",
        },
        "Agent inspects source, compares alternatives, selects a design, and plans verification.",
    )


def impact_sufficiency(payload: dict[str, Any]) -> dict[str, Any]:
    """Describe coverage of a static change scope, never an impact decision."""
    summary = record(payload.get("impact_summary"))
    learned = strings(summary.get("learned_changed_files"))
    unlearned = strings(summary.get("unlearned_changed_files"))
    direct_evidence = sum(len(records(value)) for value in record(payload.get("evidence")).values())
    checks = records(payload.get("verification_checklist"))
    reasons: list[str] = []
    if unlearned:
        status, action = "refresh_required", "learn_uncovered_changed_files"
        reasons.append("unlearned_changed_files")
    elif learned and direct_evidence:
        status, action = "ready_for_agent_verification", "inspect_changed_source_and_validate_dependents"
    else:
        status, action = "limited_scope", "confirm_changed_files_and_refresh_scope"
        reasons.append("no_direct_change_evidence")
    gaps = strings(payload.get("evidence_gaps"))
    return response(
        "impact", status, action, reasons, gaps,
        {
            "learned_changed_file_count": len(learned),
            "unlearned_changed_file_count": len(unlearned),
            "direct_evidence_count": direct_evidence,
            "verification_check_count": len(checks),
        },
        "Agent validates actual callers, tests, and runtime behavior before accepting an impact conclusion.",
    )


def response(
    kind: str,
    status: str,
    next_action: str,
    reasons: list[str],
    gaps: list[str],
    coverage: dict[str, Any],
    boundary: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "status": status,
        "next_action": next_action,
        "reason_codes": unique([*reasons, *gaps])[:8],
        "coverage": coverage,
        "scope": "retrieval_readiness_only_not_agent_reasoning",
        "agent_ownership": boundary,
    }


def freshness_reasons(status: str) -> list[str]:
    return [f"source_freshness:{status}"] if status in {"stale", "boundary_drift"} else []


def record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def strings(value: Any) -> list[str]:
    return [str(item) for item in value if str(item).strip()] if isinstance(value, list) else []


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
