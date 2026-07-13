# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .models import Project
from .usage_samples import load_task_trace


def build_task_trace_actions(project: Project) -> list[dict[str, Any]]:
    trace = load_task_trace(project)
    if not trace or not should_review_task_trace(trace):
        return []
    template = trace.get("reflection_payload_template") if isinstance(trace.get("reflection_payload_template"), dict) else {}
    actions = [
        {
            "action": "review_unreflected_task_trace",
            "governance_lane": "auto_reflection",
            "type": "task_trace",
            "id": trace.get("sample_id"),
            "reason": "latest task trace has bounded context evidence but no reflection has closed it yet",
            "risk": "low",
            "requires_confirmation": False,
            "command": None,
            "task_trace": compact_task_trace(trace),
            "reflection_payload_template": template,
            "command_template": 'python tools/agent_memory.py reflect --project . --from-last-task --task "<task>" --lesson "<lesson>" --json',
            "suggested_actions": [
                "write_reflection_from_last_task",
                "add_verification_method",
                "add_negative_preconditions_if_reusable",
                "ignore_if_task_was_not_useful",
            ],
        }
    ]
    if should_review_low_evidence_auto_summary(trace):
        quality = auto_summary_quality(trace)
        actions.append(
            {
                "action": "review_low_evidence_auto_summary",
                "governance_lane": "auto_reflection",
                "type": "task_trace",
                "id": trace.get("sample_id"),
                "reason": "latest automatic reflection summary is missing evidence, verification, repair, or counter-evidence fields",
                "risk": "medium",
                "requires_confirmation": False,
                "command": None,
                "task_trace": compact_task_trace(trace),
                "auto_summary_quality": quality,
                "reflection_payload_template": template,
                "reflection_payload_placeholders": trace.get("reflection_payload_placeholders") or {},
                "suggested_actions": [
                    "add_missing_template_fields_before_reflect",
                    "add_verification_method",
                    "add_negative_preconditions_or_does_not_apply_to",
                    "discard_if_trace_is_too_weak",
                ],
            }
        )
    return actions


def should_review_task_trace(trace: dict[str, Any]) -> bool:
    if trace.get("reflection_written") or trace.get("closed_at"):
        return False
    if not trace.get("queries") and not trace.get("candidate_evidence"):
        return False
    template = trace.get("reflection_payload_template") if isinstance(trace.get("reflection_payload_template"), dict) else {}
    return bool(template or trace.get("candidate_evidence") or trace.get("context_used"))


def should_review_low_evidence_auto_summary(trace: dict[str, Any]) -> bool:
    if trace.get("reflection_written") or trace.get("closed_at"):
        return False
    quality = auto_summary_quality(trace)
    missing = set(quality.get("missing_fields") or [])
    return float(quality.get("score") or 0.0) < 0.8 or bool(missing & {"evidence", "verification_method", "counter_evidence"})


def auto_summary_quality(trace: dict[str, Any]) -> dict[str, Any]:
    quality = trace.get("auto_summary_quality")
    if isinstance(quality, dict):
        return quality
    template = trace.get("reflection_payload_template") if isinstance(trace.get("reflection_payload_template"), dict) else {}
    missing: list[str] = []
    if not trace.get("candidate_evidence") and not str(template.get("evidence") or "").strip():
        missing.append("evidence")
    if not str(template.get("trigger_condition") or template.get("problem") or "").strip():
        missing.append("trigger_condition")
    if not str(template.get("repair_action") or "").strip():
        missing.append("repair_action")
    if not str(template.get("verification_method") or "").strip():
        missing.append("verification_method")
    if not template.get("negative_preconditions") and not str(template.get("does_not_apply_to") or "").strip():
        missing.append("counter_evidence")
    return {"score": round(max(0.0, 1.0 - (len(missing) / 5.0)), 2), "missing_fields": missing}


def compact_task_trace(trace: dict[str, Any]) -> dict[str, Any]:
    runtime_log = trace.get("runtime_log") if isinstance(trace.get("runtime_log"), dict) else {}
    governance = trace.get("governance") if isinstance(trace.get("governance"), dict) else {}
    return {
        "sample_id": trace.get("sample_id"),
        "intent": trace.get("intent"),
        "reflection_written": bool(trace.get("reflection_written")),
        "closed_at": trace.get("closed_at"),
        "reflection_id": trace.get("reflection_id"),
        "queries": list(trace.get("queries") or [])[:3],
        "commands": list(trace.get("commands") or [])[:8],
        "query_rounds": int(trace.get("query_rounds") or 0),
        "context_used": list(trace.get("context_used") or [])[:6],
        "candidate_evidence": list(trace.get("candidate_evidence") or [])[:8],
        "runtime_log_used": bool(runtime_log.get("used")),
        "governance_used": bool(governance.get("used")),
        "auto_summary": trace.get("auto_summary"),
        "auto_summary_quality": auto_summary_quality(trace),
    }
