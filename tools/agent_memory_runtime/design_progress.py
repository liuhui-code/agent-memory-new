# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .design_check import check_design_proposal, load_proposal
from .design_protocol import load_contract, load_intent, load_rules
from .design_source_delta import collect_source_delta
from .design_verification_evidence import failed_test_count, load_test_evidence, verified_refs
from .impact_scope import resolve_changed_files
from .records import output
from .storage import ensure_initialized, resolve_project


MAX_MANUAL_STEPS = 200
MAX_NEXT_STEPS = 8


def design_progress_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    proposal = load_proposal(Path(args.proposal))
    contract = load_contract(args.contract, proposal["goal"])
    intent = load_intent(args.intent, contract["goal"])
    rules = load_rules(args.rules)
    evaluation = check_design_proposal(project, proposal, contract, rules, intent=intent)
    actual_files = resolve_changed_files(project, args.base, args.files, args.diff_file, allow_empty=True)
    working_additions = present_added_files(project.root, evaluation["change_plan"]["steps"])
    actual_files = sorted(set(actual_files) | set(working_additions))
    source_delta = collect_source_delta(project, args.base, args.diff_file)
    test_evidence = load_test_evidence(args.test_evidence, args.executed_tests, args.test_report)
    payload = build_design_progress(
        project.project_id,
        proposal,
        evaluation,
        actual_files,
        source_delta,
        test_evidence,
        args.completed_step,
        working_additions,
    )
    output(payload, args.json)


def build_design_progress(
    project_id: str,
    proposal: dict[str, Any],
    evaluation: dict[str, Any],
    actual_files: list[str],
    source_delta: dict[str, Any],
    test_evidence: dict[str, Any],
    manual_steps: list[str] | None,
    working_additions: list[str] | None = None,
) -> dict[str, Any]:
    plan = evaluation["change_plan"]
    manual = normalize_manual_steps(manual_steps, plan["steps"])
    verified = verified_refs(test_evidence)
    changed_files = set(actual_files)
    changed_symbols = set(source_delta["changed_symbols"])
    working_additions = working_additions or []
    blockers = progress_blockers(evaluation, plan, test_evidence)
    steps = []
    completed_ids: set[str] = set()
    for step in plan["steps"]:
        evidence = completion_evidence(step, manual, changed_files, changed_symbols, verified)
        if evidence:
            status = "completed"
            completed_ids.add(step["id"])
        elif blockers:
            status = "blocked"
        elif all(dependency in completed_ids for dependency in step["depends_on"]):
            status = "ready"
        else:
            status = "pending"
        steps.append({**step, "status": status, "completion_evidence": evidence})
    counts = {status: sum(item["status"] == status for item in steps) for status in status_names()}
    status = "blocked" if blockers else "complete" if counts["completed"] == len(steps) else "active"
    return {
        "schema_version": "design-progress/v1",
        "project_id": project_id,
        "candidate_id": proposal["id"],
        "baseline_revision": proposal.get("baseline_revision", evaluation["baseline_revision"]),
        "current_revision": evaluation["repository_model"]["snapshot"]["graph_revision"],
        "status": status,
        "counts": counts,
        "steps": steps,
        "next_steps": [item for item in steps if item["status"] == "ready"][:MAX_NEXT_STEPS],
        "blockers": blockers,
        "actual_files": sorted(changed_files),
        "actual_symbols": sorted(changed_symbols),
        "source_delta": source_delta,
        "test_evidence": test_evidence["tests"],
        "evidence_gaps": [
            *source_delta["evidence_gaps"],
            *({"kind": "untracked_planned_file", "path": path} for path in working_additions),
        ],
        "audit": {
            "persisted": False,
            "llm_used": False,
            "tests_executed": False,
            "manual_completion_count": len(manual),
            "bounded": True,
        },
    }


def normalize_manual_steps(values: list[str] | None, steps: list[dict[str, Any]]) -> set[str]:
    raw = list(dict.fromkeys(item.strip() for item in values or [] if item.strip()))
    if len(raw) > MAX_MANUAL_STEPS:
        raise SystemExit(f"completed steps must contain at most {MAX_MANUAL_STEPS} ids")
    by_id = {step["id"]: step for step in steps}
    unknown = sorted(set(raw) - set(by_id))
    if unknown:
        raise SystemExit(f"unknown completed step id: {unknown[0]}")
    invalid = [step_id for step_id in raw if not manually_completable(by_id[step_id])]
    if invalid:
        raise SystemExit(f"step requires automatic implementation or test evidence: {invalid[0]}")
    return set(raw)


def manually_completable(step: dict[str, Any]) -> bool:
    return step["operation"] == "review_consumer" or step["target"].startswith("observe:")


def present_added_files(root: Path, steps: list[dict[str, Any]]) -> list[str]:
    project_root = root.resolve()
    result = []
    for step in steps:
        path = str(step["file_path"])
        if step["operation"] != "add" or not path:
            continue
        source = (project_root / path).resolve()
        try:
            source.relative_to(project_root)
        except ValueError as exc:
            raise SystemExit("planned added file resolves outside the project") from exc
        if source.is_file():
            result.append(path)
    return result


def completion_evidence(
    step: dict[str, Any],
    manual: set[str],
    changed_files: set[str],
    changed_symbols: set[str],
    verified: set[str],
) -> list[str]:
    if step["id"] in manual:
        return ["explicit_review"]
    target = str(step["target"])
    if step["operation"] in {"add", "modify"}:
        if target.startswith("symbol:") and target in changed_symbols:
            return ["git_symbol"]
        if step["file_path"] and step["file_path"] in changed_files:
            return ["git_file"]
    if target.startswith("test:") and target[5:] in verified:
        return ["passed_test_evidence"]
    if target.startswith("observe:") and target[8:] in verified:
        return ["passed_observability_evidence"]
    return []


def progress_blockers(
    evaluation: dict[str, Any],
    plan: dict[str, Any],
    test_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    blockers = [
        {"code": item["code"], "source": "design_evaluation", "message": item["message"]}
        for item in evaluation["errors"]
    ]
    if plan["status"] == "blocked":
        blockers.append({"code": "change_plan_cycle", "source": "change_plan", "message": "Change plan contains a cycle."})
    if failed_test_count(test_evidence):
        blockers.append({"code": "test_failure", "source": "test_evidence", "message": "At least one supplied test failed."})
    return blockers[:50]


def status_names() -> tuple[str, ...]:
    return "completed", "ready", "pending", "blocked"
