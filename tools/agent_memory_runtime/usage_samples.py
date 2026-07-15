# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .models import Project
from .storage import now_iso
from .text import unique_list


USAGE_SAMPLE_VERSION = 1
USAGE_SAMPLE_FILE = "last_usage_sample.json"
TASK_TRACE_FILE = "last_task_trace.json"


def usage_sample_path(project: Project):
    return project.runtime_dir / USAGE_SAMPLE_FILE


def task_trace_path(project: Project):
    return project.runtime_dir / TASK_TRACE_FILE


def _empty_usage_sample(project: Project) -> dict[str, Any]:
    ts = now_iso()
    return {
        "version": USAGE_SAMPLE_VERSION,
        "sample_id": ts,
        "project_id": project.project_id,
        "project_path": str(project.root),
        "started_at": ts,
        "updated_at": ts,
        "commands": [],
        "queries": [],
        "query_rounds": 0,
        "followup_focuses": [],
        "suggested_followup_terms": [],
        "context_used": [],
        "matched_anchor_counts": {},
        "query_execution": {},
        "causal_levels": [],
        "runtime_log": {
            "used": False,
            "matched_event_count": 0,
            "slice_count": 0,
            "dominant_signals": [],
            "candidate_chain": [],
            "misleading_followup_terms": [],
            "inspection_targets": [],
            "log_improvement_kinds": [],
        },
        "governance": {
            "used": False,
            "action_count": 0,
            "lanes": [],
            "actions": [],
        },
        "reflect_payload_template": {},
        "feedback_template": {
            "user_outcome": "",
            "best_output": "",
            "noisiest_output": "",
            "next_fix": "",
        },
        "auto_summary": "",
        "reflection_written": False,
        "closed_at": None,
    }


def load_usage_sample(project: Project) -> dict[str, Any]:
    path = usage_sample_path(project)
    if not path.exists():
        return _empty_usage_sample(project)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_usage_sample(project)
    if not isinstance(data, dict):
        return _empty_usage_sample(project)
    return data


def _ensure_open_usage_sample(project: Project, sample: dict[str, Any]) -> dict[str, Any]:
    if sample.get("reflection_written") or sample.get("closed_at"):
        return _empty_usage_sample(project)
    return sample


def save_usage_sample(project: Project, sample: dict[str, Any]) -> None:
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    sample["updated_at"] = now_iso()
    sample["auto_summary"] = build_usage_sample_summary(sample)
    usage_sample_path(project).write_text(
        json.dumps(sample, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    save_task_trace(project, build_task_trace(project, sample))


def save_task_trace(project: Project, trace: dict[str, Any]) -> None:
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    task_trace_path(project).write_text(
        json.dumps(trace, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_task_trace(project: Project) -> dict[str, Any]:
    path = task_trace_path(project)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def build_task_trace(project: Project, sample: dict[str, Any]) -> dict[str, Any]:
    runtime_log = sample.get("runtime_log") or {}
    governance = sample.get("governance") or {}
    candidate_evidence = compact_candidate_evidence(sample)
    reflection_payload_template = reflection_payload_from_trace_parts(sample, candidate_evidence)
    auto_summary_quality = auto_summary_quality_profile(reflection_payload_template, candidate_evidence)
    return {
        "version": 1,
        "project_id": project.project_id,
        "project_path": str(project.root),
        "sample_id": sample.get("sample_id"),
        "started_at": sample.get("started_at"),
        "updated_at": sample.get("updated_at") or now_iso(),
        "reflection_written": bool(sample.get("reflection_written")),
        "closed_at": sample.get("closed_at"),
        "reflection_id": sample.get("reflection_id"),
        "queries": sample.get("queries") or [],
        "intent": trace_intent(sample),
        "commands": sample.get("commands") or [],
        "query_rounds": int(sample.get("query_rounds") or 0),
        "context_used": sample.get("context_used") or [],
        "matched_anchor_counts": sample.get("matched_anchor_counts") or {},
        "query_execution": sample.get("query_execution") or {},
        "causal_levels": sample.get("causal_levels") or [],
        "candidate_evidence": candidate_evidence,
        "runtime_log": {
            "used": bool(runtime_log.get("used")),
            "matched_event_count": int(runtime_log.get("matched_event_count") or 0),
            "slice_count": int(runtime_log.get("slice_count") or 0),
            "dominant_signals": runtime_log.get("dominant_signals") or [],
            "candidate_chain": runtime_log.get("candidate_chain") or [],
            "inspection_targets": runtime_log.get("inspection_targets") or [],
        },
        "governance": {
            "used": bool(governance.get("used")),
            "action_count": int(governance.get("action_count") or 0),
            "lanes": governance.get("lanes") or [],
            "actions": governance.get("actions") or [],
        },
        "auto_summary": sample.get("auto_summary") or build_usage_sample_summary(sample),
        "reflection_payload_template": reflection_payload_template,
        "reflection_payload_placeholders": reflection_payload_placeholders(auto_summary_quality),
        "auto_summary_quality": auto_summary_quality,
    }


def compact_candidate_evidence(sample: dict[str, Any]) -> list[str]:
    runtime_log = sample.get("runtime_log") or {}
    governance = sample.get("governance") or {}
    evidence: list[str] = []
    evidence.extend(str(item) for item in sample.get("context_used") or [])
    evidence.extend(f"runtime_signal:{item}" for item in runtime_log.get("dominant_signals") or [])
    evidence.extend(f"runtime_chain:{item}" for item in runtime_log.get("candidate_chain") or [])
    evidence.extend(f"governance_lane:{item}" for item in governance.get("lanes") or [])
    return unique_list([item for item in evidence if str(item).strip()])[:12]


def trace_intent(sample: dict[str, Any]) -> str:
    runtime_log = sample.get("runtime_log") or {}
    governance = sample.get("governance") or {}
    if runtime_log.get("used"):
        return "runtime_log_diagnosis"
    if governance.get("used"):
        return "memory_maintenance"
    if sample.get("queries"):
        return "memory_query"
    return "unknown"


def reflection_payload_from_trace_parts(sample: dict[str, Any], candidate_evidence: list[str]) -> dict[str, Any]:
    template = dict(sample.get("reflect_payload_template") or {})
    runtime_log = sample.get("runtime_log") or {}
    if sample.get("queries") and not template.get("problem"):
        template["problem"] = str((sample.get("queries") or [])[-1])
    if sample.get("auto_summary") and not template.get("reasoning_summary"):
        template["reasoning_summary"] = str(sample.get("auto_summary") or "")
    if candidate_evidence and not template.get("evidence"):
        template["evidence"] = "; ".join(candidate_evidence[:6])
    if sample.get("context_used") and not template.get("context_used"):
        template["context_used"] = list(sample.get("context_used") or [])
    if sample.get("query_rounds") and not template.get("query_rounds"):
        template["query_rounds"] = int(sample.get("query_rounds") or 0)
    if sample.get("followup_focuses") and not template.get("useful_followup_focus"):
        template["useful_followup_focus"] = str((sample.get("followup_focuses") or [])[-1])
    if sample.get("suggested_followup_terms") and not template.get("useful_followup_terms"):
        template["useful_followup_terms"] = list(sample.get("suggested_followup_terms") or [])
    if runtime_log.get("used"):
        template.setdefault("task_type", "diagnosis")
        template.setdefault("experience_type", "procedure_experience")
        template.setdefault("source_cases", ["runtime_log:last_task_trace"])
        if runtime_log.get("inspection_targets") and not template.get("inspection_targets"):
            template["inspection_targets"] = list(runtime_log.get("inspection_targets") or [])
    return template


def auto_summary_quality_profile(template: dict[str, Any], candidate_evidence: list[str]) -> dict[str, Any]:
    missing: list[str] = []
    if not candidate_evidence and not str(template.get("evidence") or "").strip():
        missing.append("evidence")
    if not str(template.get("trigger_condition") or template.get("problem") or "").strip():
        missing.append("trigger_condition")
    if not str(template.get("repair_action") or "").strip():
        missing.append("repair_action")
    if not str(template.get("verification_method") or "").strip():
        missing.append("verification_method")
    has_counter_boundary = bool(template.get("negative_preconditions") or str(template.get("does_not_apply_to") or "").strip())
    if not has_counter_boundary:
        missing.append("counter_evidence")
    score = max(0.0, 1.0 - (len(missing) / 5.0))
    return {
        "score": round(score, 2),
        "missing_fields": missing,
        "has_evidence": "evidence" not in missing,
        "has_applicability": "trigger_condition" not in missing,
        "has_repair_action": "repair_action" not in missing,
        "has_verification": "verification_method" not in missing,
        "has_counter_evidence": "counter_evidence" not in missing,
    }


def reflection_payload_placeholders(quality: dict[str, Any]) -> dict[str, Any]:
    missing = set(quality.get("missing_fields") or [])
    placeholders: dict[str, Any] = {}
    if "verification_method" in missing:
        placeholders["verification_method"] = "TODO: cite the command, source inspection, log signal, or test that verified the lesson"
    if "counter_evidence" in missing:
        placeholders["negative_preconditions"] = ["TODO: list similar cases where this lesson should not transfer"]
        placeholders["does_not_apply_to"] = "TODO: describe the nearest false-positive scenario"
    if "repair_action" in missing:
        placeholders["repair_action"] = "TODO: write the concrete reusable action, not just the observation"
    return placeholders


def _append_unique(sample: dict[str, Any], key: str, values: list[str]) -> None:
    existing = [str(item) for item in sample.get(key) or []]
    sample[key] = unique_list(existing + [str(value) for value in values if str(value).strip()])


def _append_context_used(sample: dict[str, Any], value: str) -> None:
    _append_unique(sample, "context_used", [value])


def record_query_usage(project: Project, command_name: str, query: str, data: dict[str, Any]) -> dict[str, Any]:
    sample = _ensure_open_usage_sample(project, load_usage_sample(project))
    _append_unique(sample, "commands", [command_name])
    _append_unique(sample, "queries", [query])
    sample["query_rounds"] = int(sample.get("query_rounds") or 0) + 1
    if str(data.get("followup_focus") or "").strip():
        _append_unique(sample, "followup_focuses", [str(data.get("followup_focus") or "")])
    _append_unique(sample, "suggested_followup_terms", [str(item) for item in data.get("suggested_followup_terms") or []])
    matched_counts = {
        "semantic_facts": len(data.get("semantic_facts") or []),
        "reflections": len(data.get("reflections") or []),
        "episodes": len(data.get("episodes") or []),
        "wiki_matches": len(data.get("wiki_matches") or []),
        "code_log_matches": len(data.get("code_log_matches") or []),
        "edge_matches": len(data.get("edge_matches") or []),
    }
    if data.get("returned_counts_by_type"):
        matched_counts.update(
            {
                key: int(value)
                for key, value in (data.get("returned_counts_by_type") or {}).items()
                if isinstance(value, int)
            }
        )
    sample["matched_anchor_counts"] = matched_counts
    if isinstance(data.get("query_execution"), dict):
        sample["query_execution"] = dict(data.get("query_execution") or {})
    _append_unique(sample, "causal_levels", [str(value) for value in data.get("causal_levels") or []])
    _append_context_used(sample, f"{command_name}: {query}")
    save_usage_sample(project, sample)
    return sample


def record_governance_usage(project: Project, command_name: str, data: dict[str, Any]) -> dict[str, Any]:
    sample = _ensure_open_usage_sample(project, load_usage_sample(project))
    _append_unique(sample, "commands", [command_name])
    actions = data.get("actions") or []
    governance = sample.setdefault("governance", {})
    governance.update(
        {
            "used": True,
            "action_count": len(actions),
            "lanes": unique_list([str(item.get("governance_lane") or "") for item in actions if str(item.get("governance_lane") or "").strip()]),
            "actions": unique_list([str(item.get("action") or "") for item in actions if str(item.get("action") or "").strip()])[:12],
        }
    )
    _append_context_used(sample, f"{command_name}: {', '.join(governance.get('lanes') or []) or 'governance'}")
    save_usage_sample(project, sample)
    return sample


def build_usage_sample_summary(sample: dict[str, Any]) -> str:
    commands = " -> ".join(str(item) for item in sample.get("commands") or [])
    followup_focus = ", ".join(str(item) for item in (sample.get("followup_focuses") or [])[:3])
    runtime_log = sample.get("runtime_log") or {}
    governance = sample.get("governance") or {}
    parts = []
    if commands:
        parts.append(f"commands: {commands}")
    if sample.get("queries"):
        parts.append(f"queries: {', '.join(str(item) for item in (sample.get('queries') or [])[:2])}")
    if followup_focus:
        parts.append(f"followup focus: {followup_focus}")
    if runtime_log.get("used"):
        dominant = ", ".join(str(item) for item in (runtime_log.get("dominant_signals") or [])[:4])
        if dominant:
            parts.append(f"dominant runtime signals: {dominant}")
        candidate_chain = " -> ".join(str(item) for item in (runtime_log.get("candidate_chain") or [])[:4])
        if candidate_chain:
            parts.append(f"candidate chain: {candidate_chain}")
    if governance.get("used"):
        lanes = ", ".join(str(item) for item in (governance.get("lanes") or [])[:4])
        if lanes:
            parts.append(f"governance lanes: {lanes}")
    return ". ".join(parts)


def merge_usage_sample_into_reflection_payload(
    payload: dict[str, Any],
    usage_sample: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(payload)
    runtime_template = usage_sample.get("reflect_payload_template") or {}
    if isinstance(runtime_template, dict):
        for key, value in runtime_template.items():
            if key not in merged or merged.get(key) in (None, "", [], {}):
                merged[key] = value

    if not merged.get("problem") and usage_sample.get("queries"):
        merged["problem"] = str((usage_sample.get("queries") or [])[-1])
    if not merged.get("trajectory_summary") and usage_sample.get("auto_summary"):
        merged["trajectory_summary"] = str(usage_sample.get("auto_summary") or "")
    if not merged.get("context_used") and usage_sample.get("context_used"):
        merged["context_used"] = list(usage_sample.get("context_used") or [])
    if not merged.get("query_rounds") and usage_sample.get("query_rounds"):
        merged["query_rounds"] = int(usage_sample.get("query_rounds") or 0)
    if not merged.get("useful_followup_focus") and usage_sample.get("followup_focuses"):
        merged["useful_followup_focus"] = str((usage_sample.get("followup_focuses") or [])[-1])
    if not merged.get("useful_followup_terms") and usage_sample.get("suggested_followup_terms"):
        merged["useful_followup_terms"] = list(usage_sample.get("suggested_followup_terms") or [])
    runtime_log = usage_sample.get("runtime_log") or {}
    if not merged.get("misleading_followup_terms") and runtime_log.get("misleading_followup_terms"):
        merged["misleading_followup_terms"] = list(runtime_log.get("misleading_followup_terms") or [])
    if not merged.get("inspection_targets") and runtime_log.get("inspection_targets"):
        merged["inspection_targets"] = list(runtime_log.get("inspection_targets") or [])
    if not merged.get("task_type"):
        if runtime_log.get("used"):
            merged["task_type"] = "diagnosis"
        elif (usage_sample.get("governance") or {}).get("used"):
            merged["task_type"] = "workflow"
    return merged


def mark_usage_sample_reflected(project: Project, reflection_id: int) -> None:
    sample = load_usage_sample(project)
    sample["reflection_written"] = True
    sample["closed_at"] = now_iso()
    sample["reflection_id"] = reflection_id
    save_usage_sample(project, sample)
