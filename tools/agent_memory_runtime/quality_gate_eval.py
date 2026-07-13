# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from .calibration_eval import evaluate_calibration_cases, load_calibration_cases
from .evidence_attribution import evaluate_evidence_attribution, load_cases as load_evidence_cases
from .experience_evidence_eval import evaluate_experience_evidence_cases, load_experience_evidence_cases
from .governance_eval import collect_eval_governance_actions, evaluate_governance_cases, load_governance_cases
from .graph_signal_eval import evaluate_graph_signal_cases, load_graph_signal_cases
from .log_signal_eval import evaluate_log_signal_cases, load_log_signal_cases
from .models import Project
from .records import output
from .retrieval_eval import evaluate_retrieval_cases, load_eval_cases
from .storage import ensure_initialized, now_iso, resolve_project


GateRunner = Callable[[Project, Path], dict[str, Any]]
QUALITY_GATE_SAMPLE_FILE = "last_quality_gate.json"
QUALITY_GATE_HISTORY_FILE = "quality_gate_history.jsonl"


def eval_quality_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    if bool(getattr(args, "list_gates", False)):
        output(list_quality_gates(Path(args.cases_dir)), args.json)
        return
    if bool(getattr(args, "history", False)):
        data = load_quality_gate_history_report(
            project,
            limit=int(getattr(args, "history_limit", 20) or 20),
            gates=selected_gate_names(getattr(args, "gate", None)),
        )
        output(data, args.json)
        return
    previous = load_quality_gate_snapshot(project)
    data = evaluate_quality_gates(
        project,
        Path(args.cases_dir),
        strict=bool(getattr(args, "strict", False)),
        gates=selected_gate_names(getattr(args, "gate", None)),
    )
    data["quality_gate_delta"] = build_quality_gate_delta(previous, data)
    save_quality_gate_snapshot(project, data)
    append_quality_gate_history(project, data)
    output(data, args.json)
    if bool(getattr(args, "fail_on_fail", False)) and data.get("quality_gate") == "fail":
        raise SystemExit(1)


def run_retrieval(project: Project, path: Path) -> dict[str, Any]:
    return evaluate_retrieval_cases(project, load_eval_cases(path))


def run_calibration(project: Project, path: Path) -> dict[str, Any]:
    return evaluate_calibration_cases(project, load_calibration_cases(path))


def run_experience_evidence(project: Project, path: Path) -> dict[str, Any]:
    return evaluate_experience_evidence_cases(project, load_experience_evidence_cases(path))


def run_governance(project: Project, path: Path) -> dict[str, Any]:
    actions = collect_eval_governance_actions(project)
    return evaluate_governance_cases(project.project_id, load_governance_cases(path), actions)


def run_log_signal(project: Project, path: Path) -> dict[str, Any]:
    data = evaluate_log_signal_cases(load_log_signal_cases(path))
    data["project_id"] = project.project_id
    return data


def run_graph_signal(project: Project, path: Path) -> dict[str, Any]:
    return evaluate_graph_signal_cases(project, load_graph_signal_cases(path))


def run_evidence_attribution(project: Project, path: Path) -> dict[str, Any]:
    return evaluate_evidence_attribution(project, load_evidence_cases(path))


GATES: list[tuple[str, str, str, GateRunner]] = [
    ("retrieval", "golden-retrieval.json", "eval-retrieval", run_retrieval),
    ("calibration", "golden-calibration.json", "eval-calibration", run_calibration),
    ("experience_evidence", "golden-experience-evidence.json", "eval-experience-evidence", run_experience_evidence),
    ("governance", "golden-governance.json", "eval-governance", run_governance),
    ("log_signal", "golden-log-signal.json", "eval-log-signal", run_log_signal),
    ("graph_signal", "golden-graph-signal.json", "eval-graph-signal", run_graph_signal),
    ("evidence_attribution", "golden-evidence-attribution.json", "eval-evidence-attribution", run_evidence_attribution),
]
GATE_NAMES = [name for name, _, _, _ in GATES]


def list_quality_gates(cases_dir: Path) -> dict[str, Any]:
    gates = [
        {
            "name": name,
            "case_file": str(cases_dir / filename),
            "command": command_name,
            "command_template": f"python tools/agent_memory.py {command_name} --project . --cases {cases_dir / filename} --json",
            "aggregate_template": f"python tools/agent_memory.py eval-quality --project . --cases-dir {cases_dir} --gate {name} --json",
        }
        for name, filename, command_name, _ in GATES
    ]
    return {
        "gate_count": len(gates),
        "gate_names": [gate["name"] for gate in gates],
        "cases_dir": str(cases_dir),
        "gates": gates,
    }


def evaluate_quality_gates(
    project: Project,
    cases_dir: Path,
    strict: bool = False,
    gates: list[str] | None = None,
) -> dict[str, Any]:
    selected_names = gates or GATE_NAMES
    selected = set(selected_names)
    gate_results = [
        evaluate_gate(project, cases_dir, name, filename, command_name, runner)
        for name, filename, command_name, runner in GATES
        if name in selected
    ]
    passed_names = [str(gate["name"]) for gate in gate_results if gate["status"] == "pass"]
    failed_names = [str(gate["name"]) for gate in gate_results if gate["status"] == "fail"]
    skipped_names = [str(gate["name"]) for gate in gate_results if gate["status"] == "skipped"]
    passed = len([gate for gate in gate_results if gate["status"] == "pass"])
    failed = len([gate for gate in gate_results if gate["status"] == "fail"])
    skipped = len([gate for gate in gate_results if gate["status"] == "skipped"])
    executed = passed + failed
    no_cases_failure = strict and executed == 0
    quality_gate = "fail" if failed or no_cases_failure else "pass"
    summary: dict[str, Any] = {
        "gate_count": executed,
        "passed_gates": passed,
        "failed_gates": failed,
        "skipped_gates": skipped,
        "selected_gate_names": selected_names,
        "passed_gate_names": passed_names,
        "failed_gate_names": failed_names,
        "skipped_gate_names": skipped_names,
    }
    if no_cases_failure:
        summary["failure_reason"] = "no_case_files"
    return {
        "project_id": project.project_id,
        "project_path": str(project.root),
        "quality_gate": quality_gate,
        "summary": summary,
        "gates": gate_results,
        "cases_dir": str(cases_dir),
        "selected_gate_names": selected_names,
        "strict": strict,
    }


def selected_gate_names(values: Any) -> list[str] | None:
    if not values:
        return None
    names = [str(value).strip() for value in values if str(value).strip()]
    unknown = [name for name in names if name not in GATE_NAMES]
    if unknown:
        raise SystemExit(f"unknown quality gate: {', '.join(unknown)}; valid gates: {', '.join(GATE_NAMES)}")
    selected: list[str] = []
    for name in names:
        if name not in selected:
            selected.append(name)
    return selected


def evaluate_gate(
    project: Project,
    cases_dir: Path,
    name: str,
    filename: str,
    command_name: str,
    runner: GateRunner,
) -> dict[str, Any]:
    path = cases_dir / filename
    base = {
        "name": name,
        "case_file": str(path),
        "next_command_template": f"python tools/agent_memory.py {command_name} --project . --cases {path} --json",
    }
    if not path.exists():
        return {**base, "status": "skipped", "reason": "case file not found"}
    try:
        data = runner(project, path)
    except SystemExit as exc:
        return {**base, "status": "fail", "reason": str(exc), "summary": {}}
    status = "pass" if data.get("quality_gate") == "pass" else "fail"
    summary = data.get("summary") or {}
    return {
        **base,
        "status": status,
        "quality_gate": data.get("quality_gate"),
        "summary": summary,
        "thresholds": data.get("thresholds") or {},
        "case_count": int(summary.get("case_count") or 0),
    }


def quality_gate_snapshot_path(project: Project) -> Path:
    return project.runtime_dir / QUALITY_GATE_SAMPLE_FILE


def quality_gate_history_path(project: Project) -> Path:
    return project.runtime_dir / QUALITY_GATE_HISTORY_FILE


def save_quality_gate_snapshot(project: Project, data: dict[str, Any]) -> None:
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    quality_gate_snapshot_path(project).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def append_quality_gate_history(project: Project, data: dict[str, Any]) -> None:
    project.runtime_dir.mkdir(parents=True, exist_ok=True)
    record = compact_quality_gate_history_record(data)
    with quality_gate_history_path(project).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def compact_quality_gate_history_record(data: dict[str, Any]) -> dict[str, Any]:
    summary = data.get("summary") or {}
    gates = [
        {
            "name": gate.get("name"),
            "status": gate.get("status"),
            "case_count": gate.get("case_count"),
            "next_command_template": gate.get("next_command_template"),
        }
        for gate in data.get("gates") or []
        if isinstance(gate, dict)
    ]
    return {
        "timestamp": now_iso(),
        "project_id": data.get("project_id"),
        "quality_gate": data.get("quality_gate"),
        "cases_dir": data.get("cases_dir"),
        "selected_gate_names": list(data.get("selected_gate_names") or []),
        "summary": {
            "gate_count": summary.get("gate_count", 0),
            "passed_gates": summary.get("passed_gates", 0),
            "failed_gates": summary.get("failed_gates", 0),
            "skipped_gates": summary.get("skipped_gates", 0),
            "failed_gate_names": list(summary.get("failed_gate_names") or []),
            "passed_gate_names": list(summary.get("passed_gate_names") or []),
        },
        "gates": gates,
    }


def load_quality_gate_history_report(project: Project, limit: int = 20, gates: list[str] | None = None) -> dict[str, Any]:
    records = load_quality_gate_history(project, limit=limit, gates=gates)
    return {
        "project_id": project.project_id,
        "history_file": str(quality_gate_history_path(project)),
        "limit": limit,
        "gate_filter": gates or [],
        "summary": summarize_quality_gate_history(records),
        "history": records,
    }


def load_quality_gate_history(project: Project, limit: int = 20, gates: list[str] | None = None) -> list[dict[str, Any]]:
    path = quality_gate_history_path(project)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        filtered = filter_history_record(record, gates)
        if filtered:
            records.append(filtered)
    return records[-max(1, limit) :]


def filter_history_record(record: dict[str, Any], gates: list[str] | None) -> dict[str, Any] | None:
    if not gates:
        return record
    allowed = set(gates)
    gate_rows = [gate for gate in record.get("gates") or [] if isinstance(gate, dict) and gate.get("name") in allowed]
    if not gate_rows:
        return None
    failed_names = [str(gate.get("name")) for gate in gate_rows if gate.get("status") == "fail"]
    passed_names = [str(gate.get("name")) for gate in gate_rows if gate.get("status") == "pass"]
    summary = dict(record.get("summary") or {})
    summary.update(
        {
            "gate_count": len([gate for gate in gate_rows if gate.get("status") in {"pass", "fail"}]),
            "passed_gates": len(passed_names),
            "failed_gates": len(failed_names),
            "skipped_gates": len([gate for gate in gate_rows if gate.get("status") == "skipped"]),
            "failed_gate_names": failed_names,
            "passed_gate_names": passed_names,
        }
    )
    quality_gate = "fail" if failed_names else "pass"
    return {**record, "quality_gate": quality_gate, "summary": summary, "gates": gate_rows}


def summarize_quality_gate_history(records: list[dict[str, Any]]) -> dict[str, Any]:
    failed_counts: dict[str, int] = {}
    latest_failed: list[str] = []
    for record in records:
        failed = [str(name) for name in (record.get("summary") or {}).get("failed_gate_names") or []]
        latest_failed = failed
        for name in failed:
            failed_counts[name] = failed_counts.get(name, 0) + 1
    recurring = sorted([name for name, count in failed_counts.items() if count >= 2])
    return {
        "run_count": len(records),
        "failed_run_count": len([record for record in records if record.get("quality_gate") == "fail"]),
        "latest_quality_gate": records[-1].get("quality_gate") if records else None,
        "latest_failed_gate_names": latest_failed,
        "failed_gate_counts": failed_counts,
        "recurring_failed_gate_names": recurring,
    }


def load_quality_gate_snapshot(project: Project) -> dict[str, Any]:
    path = quality_gate_snapshot_path(project)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return compact_quality_gate_snapshot(data)


def compact_quality_gate_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    gates = [
        {
            "name": gate.get("name"),
            "status": gate.get("status"),
            "case_file": gate.get("case_file"),
            "next_command_template": gate.get("next_command_template"),
        }
        for gate in data.get("gates") or []
        if isinstance(gate, dict)
    ]
    return {
        "quality_gate": data.get("quality_gate"),
        "summary": data.get("summary") or {},
        "cases_dir": data.get("cases_dir"),
        "strict": bool(data.get("strict")),
        "gates": gates,
    }


def build_quality_gate_failure_actions(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    if snapshot.get("quality_gate") != "fail":
        return []
    summary = snapshot.get("summary") or {}
    failed_gate_names = [str(item) for item in summary.get("failed_gate_names") or [] if str(item).strip()]
    next_command_templates = [
        str(gate.get("next_command_template") or "")
        for gate in snapshot.get("gates") or []
        if gate.get("status") == "fail" and str(gate.get("next_command_template") or "").strip()
    ]
    return [
        {
            "action": "review_quality_gate_failure",
            "governance_lane": "quality_gate",
            "type": "quality_gate",
            "id": None,
            "reason": "latest aggregate quality gate failed",
            "risk": "medium",
            "requires_confirmation": False,
            "command": None,
            "failed_gate_names": failed_gate_names,
            "next_command_templates": next_command_templates,
            "last_quality_gate": snapshot,
            "suggested_actions": [
                "rerun_failed_eval_gate",
                "inspect_missed_or_unexpected_case",
                "fix_runtime_behavior_or_update_golden_case_deliberately",
            ],
        }
    ]


def build_recurring_quality_gate_failure_actions(history_report: dict[str, Any]) -> list[dict[str, Any]]:
    summary = history_report.get("summary") or {}
    recurring = [str(name) for name in summary.get("recurring_failed_gate_names") or [] if str(name).strip()]
    if not recurring:
        return []
    latest_commands = latest_failed_gate_commands(history_report.get("history") or [], recurring)
    return [
        {
            "action": "review_recurring_quality_gate_failure",
            "governance_lane": "quality_gate",
            "type": "quality_gate_history",
            "id": None,
            "reason": "one or more quality gates failed repeatedly in recent eval-quality history",
            "risk": "high",
            "requires_confirmation": False,
            "command": None,
            "recurring_failed_gate_names": recurring,
            "failed_gate_counts": summary.get("failed_gate_counts") or {},
            "next_command_templates": latest_commands,
            "history_summary": summary,
            "suggested_actions": [
                "rerun_recurring_failed_gate",
                "inspect_recent_failures_before_new_feature_work",
                "fix_runtime_behavior_or_update_golden_case_deliberately",
            ],
        }
    ]


def latest_failed_gate_commands(records: list[dict[str, Any]], names: list[str]) -> list[str]:
    wanted = set(names)
    commands: list[str] = []
    for record in reversed(records):
        for gate in record.get("gates") or []:
            if not isinstance(gate, dict):
                continue
            command = str(gate.get("next_command_template") or "")
            if gate.get("name") in wanted and gate.get("status") == "fail" and command and command not in commands:
                commands.append(command)
        if len(commands) >= len(wanted):
            break
    return commands


def build_quality_gate_delta(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    previous_gate = str(previous.get("quality_gate") or "") if previous else ""
    current_gate = str(current.get("quality_gate") or "")
    selected = [str(item) for item in current.get("selected_gate_names") or [] if str(item).strip()]
    previous_failed = failed_gate_names(previous, selected)
    current_failed = failed_gate_names(current)
    newly_failed = sorted(set(current_failed) - set(previous_failed))
    resolved_failed = sorted(set(previous_failed) - set(current_failed))
    unchanged_failed = sorted(set(previous_failed) & set(current_failed))
    return {
        "previous_quality_gate": previous_gate or None,
        "current_quality_gate": current_gate or None,
        "status_change": quality_gate_status_change(previous_gate, current_gate),
        "newly_failed_gates": newly_failed,
        "resolved_failed_gates": resolved_failed,
        "unchanged_failed_gates": unchanged_failed,
    }


def failed_gate_names(data: dict[str, Any], selected: list[str] | None = None) -> list[str]:
    summary = data.get("summary") or {}
    names = [str(item) for item in summary.get("failed_gate_names") or [] if str(item).strip()]
    if selected:
        allowed = set(selected)
        return [name for name in names if name in allowed]
    return names


def quality_gate_status_change(previous: str, current: str) -> str:
    if not previous:
        return "no_previous"
    if previous == "fail" and current == "pass":
        return "resolved_failure"
    if previous == "pass" and current == "fail":
        return "new_failure"
    if previous == "fail" and current == "fail":
        return "still_failing"
    if previous == "pass" and current == "pass":
        return "still_passing"
    return "changed"
