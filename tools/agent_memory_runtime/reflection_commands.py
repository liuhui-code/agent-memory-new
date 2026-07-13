# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .records import output, parse_ids
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .text import reflection_list_text
from .usage_samples import load_task_trace, load_usage_sample, mark_usage_sample_reflected, merge_usage_sample_into_reflection_payload

REFLECTION_PAYLOAD_TASK_TYPES = {"diagnosis", "design", "execution", "workflow"}
REFLECTION_PAYLOAD_OUTCOMES = {"success", "failure", "partial"}
REFLECTION_EXPERIENCE_TYPES = {
    "procedure_experience",
    "correction_experience",
    "semantic_patch_experience",
}
REFLECTION_FOLLOWUP_FOCI = {"route", "resource", "log", "config"}
SEMANTIC_PATCH_ANCHOR_TYPES = {"code_file", "code_symbol", "code_log_statement", "memory_edge"}
SEMANTIC_PATCH_FIELDS = {
    "business_summary",
    "business_terms",
    "business_event",
    "trigger_stage",
    "symptom_terms",
    "likely_causes",
    "process_hint",
    "neighbor_terms",
}



def payload_has_value(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if isinstance(value, list):
        return bool(value)
    return bool(str(value or "").strip())



def validate_reflection_payload_shape(payload: dict[str, Any]) -> None:
    experience_type = payload.get("experience_type")
    if not experience_type:
        return
    if experience_type == "procedure_experience":
        missing = [
            key
            for key in ("repair_action", "verification_method")
            if not payload_has_value(payload, key)
        ]
        has_trigger_evidence = any(
            payload_has_value(payload, key)
            for key in ("trigger_condition", "useful_followup_focus", "source_cases", "context_used")
        )
        if not has_trigger_evidence:
            missing.append("trigger_condition or useful_followup_focus or source_cases")
        if missing:
            raise SystemExit(
                "--payload procedure_experience requires "
                + ", ".join(missing)
            )
    elif experience_type == "correction_experience":
        missing = [
            key
            for key in ("trigger_condition", "repair_action")
            if not payload_has_value(payload, key)
        ]
        if payload_has_value(payload, "skill_candidate"):
            raise SystemExit("--payload correction_experience cannot set skill_candidate")
        has_misleading_signal = any(
            payload_has_value(payload, key)
            for key in ("anti_pattern", "misleading_followup_terms", "what_failed")
        )
        if missing or not has_misleading_signal:
            details = missing
            if not has_misleading_signal:
                details = [*details, "anti_pattern or misleading_followup_terms or what_failed"]
            raise SystemExit(
                "--payload correction_experience requires "
                + ", ".join(details)
            )
    elif experience_type == "semantic_patch_experience":
        missing = [
            key
            for key in ("anchor_type", "anchor_key", "semantic_field", "proposed_value")
            if not payload_has_value(payload, key)
        ]
        if missing:
            raise SystemExit(
                "--payload semantic_patch_experience requires "
                + ", ".join(missing)
            )
        anchor_type = str(payload.get("anchor_type") or "")
        if anchor_type not in SEMANTIC_PATCH_ANCHOR_TYPES:
            raise SystemExit(
                "--payload anchor_type must be code_file, code_symbol, code_log_statement, or memory_edge"
            )
        semantic_field = str(payload.get("semantic_field") or "")
        if semantic_field not in SEMANTIC_PATCH_FIELDS:
            raise SystemExit(
                "--payload semantic_field must be a supported business semantic field"
            )



def load_reflection_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.payload and args.payload_file:
        raise SystemExit("provide only one of --payload or --payload-file")
    if args.payload_file:
        try:
            raw = Path(args.payload_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise SystemExit(f"cannot read --payload-file: {exc}") from exc
    else:
        raw = args.payload
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid reflection payload JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("reflection payload must be a JSON object")
    task_type = payload.get("task_type")
    if task_type and task_type not in REFLECTION_PAYLOAD_TASK_TYPES:
        raise SystemExit(
            "--payload task_type must be one of diagnosis, design, execution, workflow"
        )
    outcome = payload.get("outcome")
    if outcome and outcome not in REFLECTION_PAYLOAD_OUTCOMES:
        raise SystemExit("--payload outcome must be one of success, failure, partial")
    experience_type = payload.get("experience_type")
    if experience_type and experience_type not in REFLECTION_EXPERIENCE_TYPES:
        raise SystemExit(
            "--payload experience_type must be procedure_experience, correction_experience, or semantic_patch_experience"
        )
    useful_followup_focus = payload.get("useful_followup_focus")
    if useful_followup_focus and useful_followup_focus not in REFLECTION_FOLLOWUP_FOCI:
        raise SystemExit("--payload useful_followup_focus must be route, resource, log, or config")
    validate_reflection_payload_shape(payload)
    return payload



def reflection_value(args: argparse.Namespace, payload: dict[str, Any], key: str) -> Any:
    return payload.get(key) if key in payload else getattr(args, key, None)



def reflection_int_value(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise SystemExit(f"--payload {key} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"--payload {key} must be an integer") from exc



def reflect(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    payload = load_reflection_payload(args)
    if bool(getattr(args, "from_last_task", False)):
        trace_template = (load_task_trace(project).get("reflection_payload_template") or {})
        if isinstance(trace_template, dict):
            payload = {**trace_template, **payload}
    usage_sample = load_usage_sample(project)
    payload = merge_usage_sample_into_reflection_payload(payload, usage_sample)
    task = reflection_value(args, payload, "task")
    lesson = reflection_value(args, payload, "lesson")
    if not task or not lesson:
        raise SystemExit("--task and --lesson are required")
    data = {
        "project_id": project.project_id,
        "task": task,
        "summary": reflection_value(args, payload, "summary"),
        "mistake": reflection_value(args, payload, "mistake"),
        "lesson": lesson,
        "future_rule": reflection_value(args, payload, "future_rule"),
        "experience_type": reflection_value(args, payload, "experience_type"),
        "task_type": payload.get("task_type"),
        "outcome": payload.get("outcome"),
        "problem": payload.get("problem"),
        "reasoning_summary": payload.get("reasoning_summary"),
        "context_used": reflection_list_text(payload.get("context_used")),
        "what_worked": reflection_list_text(payload.get("what_worked")),
        "what_failed": reflection_list_text(payload.get("what_failed")),
        "hidden_assumptions": reflection_list_text(payload.get("hidden_assumptions")),
        "negative_preconditions": reflection_list_text(payload.get("negative_preconditions")),
        "query_rounds": reflection_int_value(payload, "query_rounds"),
        "trajectory_summary": payload.get("trajectory_summary"),
        "useful_followup_focus": payload.get("useful_followup_focus"),
        "useful_followup_terms": reflection_list_text(payload.get("useful_followup_terms")),
        "misleading_followup_terms": reflection_list_text(payload.get("misleading_followup_terms")),
        "inspection_targets": reflection_list_text(payload.get("inspection_targets")),
        "final_verification_path": payload.get("final_verification_path"),
        "related_cases": reflection_list_text(payload.get("related_cases")),
        "verification_method": reflection_value(args, payload, "verification_method"),
        "reuse_feedback": reflection_value(args, payload, "reuse_feedback"),
        "source_cases": reflection_list_text(payload.get("source_cases")),
        "skill_candidate": reflection_value(args, payload, "skill_candidate"),
        "scope": reflection_value(args, payload, "scope"),
        "evidence": reflection_value(args, payload, "evidence"),
        "confidence": float(reflection_value(args, payload, "confidence") or args.confidence),
        "trigger_condition": reflection_value(args, payload, "trigger_condition"),
        "anti_pattern": reflection_value(args, payload, "anti_pattern"),
        "repair_action": reflection_value(args, payload, "repair_action"),
        "applies_to": reflection_value(args, payload, "applies_to"),
        "does_not_apply_to": reflection_value(args, payload, "does_not_apply_to"),
        "anchor_type": reflection_value(args, payload, "anchor_type"),
        "anchor_key": reflection_value(args, payload, "anchor_key"),
        "semantic_field": reflection_value(args, payload, "semantic_field"),
        "existing_value": reflection_value(args, payload, "existing_value"),
        "proposed_value": reflection_value(args, payload, "proposed_value"),
        "patch_reason": reflection_value(args, payload, "patch_reason"),
        "applies_to_current_code": 1 if reflection_value(args, payload, "applies_to_current_code") else 0,
        "superseded_by": reflection_int_value(payload, "superseded_by"),
        "misleading_score": float(reflection_value(args, payload, "misleading_score") or 0.0),
        "created_at": now_iso(),
    }
    with connect(project) as conn:
        cur = conn.execute(
            """
            INSERT INTO reflections(
              project_id, task, summary, mistake, lesson, future_rule,
              experience_type, task_type, outcome, problem, reasoning_summary, context_used,
              what_worked, what_failed, hidden_assumptions, negative_preconditions,
              query_rounds, trajectory_summary, useful_followup_focus, useful_followup_terms,
              misleading_followup_terms, inspection_targets, final_verification_path, related_cases,
              verification_method, reuse_feedback, source_cases, skill_candidate,
              scope, evidence, confidence, trigger_condition, anti_pattern,
              repair_action, applies_to, does_not_apply_to,
              anchor_type, anchor_key, semantic_field, existing_value, proposed_value,
              patch_reason, applies_to_current_code, superseded_by, misleading_score,
              created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                data["task"],
                data["summary"],
                data["mistake"],
                data["lesson"],
                data["future_rule"],
                data["experience_type"],
                data["task_type"],
                data["outcome"],
                data["problem"],
                data["reasoning_summary"],
                data["context_used"],
                data["what_worked"],
                data["what_failed"],
                data["hidden_assumptions"],
                data["negative_preconditions"],
                data["query_rounds"],
                data["trajectory_summary"],
                data["useful_followup_focus"],
                data["useful_followup_terms"],
                data["misleading_followup_terms"],
                data["inspection_targets"],
                data["final_verification_path"],
                data["related_cases"],
                data["verification_method"],
                data["reuse_feedback"],
                data["source_cases"],
                data["skill_candidate"],
                data["scope"],
                data["evidence"],
                data["confidence"],
                data["trigger_condition"],
                data["anti_pattern"],
                data["repair_action"],
                data["applies_to"],
                data["does_not_apply_to"],
                data["anchor_type"],
                data["anchor_key"],
                data["semantic_field"],
                data["existing_value"],
                data["proposed_value"],
                data["patch_reason"],
                data["applies_to_current_code"],
                data["superseded_by"],
                data["misleading_score"],
                data["created_at"],
            ),
        )
        data["id"] = cur.lastrowid
        if args.used_reflection_ids:
            ids = parse_ids(args.used_reflection_ids)
            outcome = args.reflection_outcome or "used"
            conn.execute(
                f"""
                UPDATE reflections
                SET applied_count = COALESCE(applied_count, 0) + 1,
                    last_applied_at = ?,
                    last_outcome = ?
                WHERE project_id = ? AND id IN ({','.join('?' for _ in ids)})
                """,
                [data["created_at"], outcome, project.project_id, *ids],
            )
            for reused_reflection_id in ids:
                conn.execute(
                    """
                    INSERT INTO reflection_reuse_events(
                      project_id, reused_reflection_id, applying_reflection_id,
                      outcome, task, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project.project_id,
                        reused_reflection_id,
                        data["id"],
                        outcome,
                        data["task"],
                        data["created_at"],
                    ),
                )
        conn.commit()
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    (project.runtime_dir / "last_reflection.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    mark_usage_sample_reflected(project, data["id"])
    if bool(getattr(args, "json", False)):
        output(data, True)
    else:
        print(f"reflection #{data['id']} written")
