# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from typing import Any

from .models import Project
from .storage import now_iso
from .text import unique_list


USAGE_SAMPLE_VERSION = 1
USAGE_SAMPLE_FILE = "last_usage_sample.json"


def usage_sample_path(project: Project):
    return project.runtime_dir / USAGE_SAMPLE_FILE


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
    _append_context_used(sample, f"{command_name}: {query}")
    save_usage_sample(project, sample)
    return sample


def record_runtime_log_usage(project: Project, query: str, log_file: str, data: dict[str, Any]) -> dict[str, Any]:
    sample = _ensure_open_usage_sample(project, load_usage_sample(project))
    _append_unique(sample, "commands", ["analyze-runtime-log"])
    _append_unique(sample, "queries", [query])
    sample["query_rounds"] = max(int(sample.get("query_rounds") or 0), 1)
    if str(data.get("log_search_plan", {}).get("focus") or "").strip():
        _append_unique(sample, "followup_focuses", [str(data.get("log_search_plan", {}).get("focus") or "")])
    runtime_log = sample.setdefault("runtime_log", {})
    runtime_log.update(
        {
            "used": True,
            "log_file": log_file,
            "normalized_event_count": int(data.get("normalized_event_count") or 0),
            "matched_event_count": len(data.get("matched_events") or []),
            "slice_count": len(data.get("slices") or []),
            "dominant_signals": unique_list([str(item) for item in data.get("runtime_episode_candidate", {}).get("dominant_signals") or []]),
            "candidate_chain": unique_list([str(item) for item in data.get("runtime_episode_candidate", {}).get("candidate_chain") or []]),
            "misleading_followup_terms": unique_list(
                [str(item) for item in data.get("reflect_payload_template", {}).get("misleading_followup_terms") or []]
            ),
            "inspection_targets": unique_list(
                [str(item) for item in data.get("reflect_payload_template", {}).get("inspection_targets") or []]
            ),
            "log_improvement_kinds": unique_list(
                [str(item.get("kind") or "") for item in data.get("log_improvement_suggestions") or [] if str(item.get("kind") or "").strip()]
            ),
        }
    )
    reflect_template = data.get("reflect_payload_template") or {}
    sample["reflect_payload_template"] = reflect_template if isinstance(reflect_template, dict) else {}
    _append_unique(sample, "suggested_followup_terms", [str(item) for item in reflect_template.get("useful_followup_terms") or []])
    _append_context_used(sample, f"analyze-runtime-log: {query}")
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
    if not merged.get("reasoning_summary") and usage_sample.get("auto_summary"):
        merged["reasoning_summary"] = str(usage_sample.get("auto_summary") or "")
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
