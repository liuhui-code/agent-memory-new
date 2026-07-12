# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from .calibration_eval import evaluate_calibration_cases, load_calibration_cases
from .evidence_attribution import evaluate_evidence_attribution, load_cases as load_evidence_cases
from .governance_eval import collect_eval_governance_actions, evaluate_governance_cases, load_governance_cases
from .log_signal_eval import evaluate_log_signal_cases, load_log_signal_cases
from .models import Project
from .records import output
from .retrieval_eval import evaluate_retrieval_cases, load_eval_cases
from .storage import ensure_initialized, resolve_project


GateRunner = Callable[[Project, Path], dict[str, Any]]


def eval_quality_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    data = evaluate_quality_gates(
        project,
        Path(args.cases_dir),
        strict=bool(getattr(args, "strict", False)),
    )
    output(data, args.json)
    if bool(getattr(args, "fail_on_fail", False)) and data.get("quality_gate") == "fail":
        raise SystemExit(1)


def run_retrieval(project: Project, path: Path) -> dict[str, Any]:
    return evaluate_retrieval_cases(project, load_eval_cases(path))


def run_calibration(project: Project, path: Path) -> dict[str, Any]:
    return evaluate_calibration_cases(project, load_calibration_cases(path))


def run_governance(project: Project, path: Path) -> dict[str, Any]:
    actions = collect_eval_governance_actions(project)
    return evaluate_governance_cases(project.project_id, load_governance_cases(path), actions)


def run_log_signal(project: Project, path: Path) -> dict[str, Any]:
    data = evaluate_log_signal_cases(load_log_signal_cases(path))
    data["project_id"] = project.project_id
    return data


def run_evidence_attribution(project: Project, path: Path) -> dict[str, Any]:
    return evaluate_evidence_attribution(project, load_evidence_cases(path))


GATES: list[tuple[str, str, str, GateRunner]] = [
    ("retrieval", "golden-retrieval.json", "eval-retrieval", run_retrieval),
    ("calibration", "golden-calibration.json", "eval-calibration", run_calibration),
    ("governance", "golden-governance.json", "eval-governance", run_governance),
    ("log_signal", "golden-log-signal.json", "eval-log-signal", run_log_signal),
    ("evidence_attribution", "golden-evidence-attribution.json", "eval-evidence-attribution", run_evidence_attribution),
]


def evaluate_quality_gates(project: Project, cases_dir: Path, strict: bool = False) -> dict[str, Any]:
    gates = [
        evaluate_gate(project, cases_dir, name, filename, command_name, runner)
        for name, filename, command_name, runner in GATES
    ]
    passed_names = [str(gate["name"]) for gate in gates if gate["status"] == "pass"]
    failed_names = [str(gate["name"]) for gate in gates if gate["status"] == "fail"]
    skipped_names = [str(gate["name"]) for gate in gates if gate["status"] == "skipped"]
    passed = len([gate for gate in gates if gate["status"] == "pass"])
    failed = len([gate for gate in gates if gate["status"] == "fail"])
    skipped = len([gate for gate in gates if gate["status"] == "skipped"])
    executed = passed + failed
    no_cases_failure = strict and executed == 0
    quality_gate = "fail" if failed or no_cases_failure else "pass"
    summary: dict[str, Any] = {
        "gate_count": executed,
        "passed_gates": passed,
        "failed_gates": failed,
        "skipped_gates": skipped,
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
        "gates": gates,
        "cases_dir": str(cases_dir),
        "strict": strict,
    }


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
