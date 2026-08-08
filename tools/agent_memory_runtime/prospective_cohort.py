# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .prospective_cohort_contract import (
    load_protocol,
    validate_completion,
    validate_enrollment,
    validate_task_id,
)
from .prospective_cohort_metrics import (
    build_cohort_report,
    sanitize_benchmark_result,
    sanitize_usage_trace,
)
from .prospective_cohort_snapshot import (
    canonical_digest,
    memory_manifest,
    source_snapshot,
    task_digest,
    verify_evidence_refs,
)
from .prospective_cohort_store import (
    complete_task,
    get_cohort,
    get_task,
    insert_cohort,
    insert_task,
    list_tasks,
)
from .records import output
from .storage import connect, ensure_initialized, now_iso, resolve_project
from .usage_samples import (
    begin_cohort_usage_sample,
    close_cohort_usage_sample,
    ensure_cohort_usage_ready,
    load_task_trace,
)


def eval_cohort_create_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    protocol = load_protocol(Path(args.protocol).expanduser())
    digest = canonical_digest(protocol)
    with connect(project) as conn:
        conn.execute("BEGIN IMMEDIATE")
        cohort = insert_cohort(conn, project.project_id, protocol, digest, now_iso())
        conn.commit()
    output(cohort_projection(cohort), args.json)


def eval_cohort_enroll_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    task_id = validate_task_id(args.task_id)
    path = Path(args.task_file).expanduser()
    digest = task_digest(path)
    if args.eligibility == "eligible":
        ensure_cohort_usage_ready(project)
    enrolled_at = now_iso()
    with connect(project) as conn:
        conn.execute("BEGIN IMMEDIATE")
        cohort = get_cohort(conn, project.project_id, args.cohort_id)
        require_open_cohort(cohort)
        enrollment = validate_enrollment(
            cohort["protocol"], args.eligibility, args.opportunity,
            args.evidence_ref, args.exclusion_reason,
        )
        tasks = list_tasks(conn, int(cohort["id"]))
        if len(tasks) >= int(cohort["target_presented_tasks"]):
            raise SystemExit("prospective cohort already reached its fixed presented count")
        if any(item["status"] == "active" for item in tasks):
            raise SystemExit("complete the active cohort task before enrolling the next task")
        evidence = verify_evidence_refs(
            conn, project.project_id, enrollment["evidence_refs"], enrolled_at,
        )
        manifest, manifest_digest = memory_manifest(conn, project.project_id, enrolled_at)
        source = source_snapshot(project.root)
        sequence = len(tasks) + 1
        previous = str(cohort["chain_head_digest"])
        sample_id = (
            f"cohort:{args.cohort_id}:{task_id}"
            if args.eligibility == "eligible" else None
        )
        immutable = entry_payload(
            args.cohort_id, sequence, task_id, digest, enrollment,
            evidence, enrolled_at, manifest, manifest_digest, source, previous, sample_id,
        )
        entry_digest = canonical_digest(immutable)
        task = insert_task(conn, {
            **immutable,
            "project_id": project.project_id,
            "cohort_pk": int(cohort["id"]),
            "entry_digest": entry_digest,
            "status": "active" if args.eligibility == "eligible" else "excluded",
            "replay_eligible": int(bool(source["replay_eligible"])),
            "usage_sample_id": sample_id,
        })
        conn.execute(
            """
            UPDATE prospective_cohorts
            SET status = 'running', presented_count = presented_count + 1,
                eligible_count = eligible_count + ?, excluded_count = excluded_count + ?,
                chain_head_digest = ?, started_at = COALESCE(started_at, ?)
            WHERE id = ?
            """,
            (
                int(args.eligibility == "eligible"), int(args.eligibility == "excluded"),
                entry_digest, enrolled_at, cohort["id"],
            ),
        )
        if sample_id:
            begin_cohort_usage_sample(project, sample_id)
        conn.commit()
    output(task_projection(task), args.json)


def eval_cohort_complete_command(args: argparse.Namespace) -> None:
    validate_completion(args.outcome, args.verification)
    task_id = validate_task_id(args.task_id)
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    with connect(project) as conn:
        conn.execute("BEGIN IMMEDIATE")
        cohort = get_cohort(conn, project.project_id, args.cohort_id)
        require_open_cohort(cohort)
        task = get_task(conn, int(cohort["id"]), task_id)
        if task["status"] != "active":
            raise SystemExit("prospective cohort task is not active")
        usage = sanitize_usage_trace(load_task_trace(project), str(task["usage_sample_id"]))
        if not usage["reported"]:
            raise SystemExit("prospective cohort usage trace is missing or belongs to another task")
        benchmark_path = Path(args.benchmark_result).expanduser() if args.benchmark_result else None
        benchmark = sanitize_benchmark_result(benchmark_path, args.case_id)
        if benchmark and not task["replay_eligible"]:
            raise SystemExit("dirty or unversioned cohort task cannot bind a paired benchmark")
        completion_digest = canonical_digest({
            "task_entry_digest": task["entry_digest"],
            "outcome": args.outcome,
            "verification": args.verification,
            "usage": usage,
            "benchmark": benchmark,
        })
        completed = complete_task(
            conn, int(task["id"]), args.outcome, args.verification, usage,
            benchmark, completion_digest, now_iso(),
        )
        close_cohort_usage_sample(project, str(task["usage_sample_id"]))
        conn.commit()
    output(task_projection(completed), args.json)


def eval_cohort_report_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    with connect(project) as conn:
        cohort = get_cohort(conn, project.project_id, args.cohort_id)
        tasks = list_tasks(conn, int(cohort["id"]))
    output(build_cohort_report(cohort, tasks, chain_valid(cohort, tasks)), args.json)


def eval_cohort_finalize_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    with connect(project) as conn:
        conn.execute("BEGIN IMMEDIATE")
        cohort = get_cohort(conn, project.project_id, args.cohort_id)
        require_open_cohort(cohort)
        tasks = list_tasks(conn, int(cohort["id"]))
        completed_cohort = {**cohort, "status": "completed"}
        report = build_cohort_report(
            completed_cohort, tasks, chain_valid(cohort, tasks),
        )
        if report["data_quality"]["status"] != "pass":
            raise SystemExit("prospective cohort cannot finalize before fixed-count data quality passes")
        finalized_at = now_iso()
        report_digest = canonical_digest(report)
        conn.execute(
            """
            UPDATE prospective_cohorts
            SET status = 'completed', finalized_at = ?, report_json = ?, report_digest = ?
            WHERE id = ? AND status != 'completed'
            """,
            (
                finalized_at,
                json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                report_digest,
                cohort["id"],
            ),
        )
        conn.commit()
    output(report, args.json)


def require_open_cohort(cohort: dict[str, Any]) -> None:
    if cohort["status"] == "completed":
        raise SystemExit("prospective cohort is finalized and immutable")


def entry_payload(
    cohort_id: str,
    sequence_no: int,
    task_id: str,
    digest: str,
    enrollment: dict[str, Any],
    evidence: list[dict[str, Any]],
    enrolled_at: str,
    manifest: dict[str, Any],
    manifest_digest: str,
    source: dict[str, Any],
    previous: str,
    sample_id: str | None,
) -> dict[str, Any]:
    return {
        "cohort_id": cohort_id,
        "sequence_no": sequence_no,
        "task_id": task_id,
        "task_digest": digest,
        "eligibility": enrollment["eligibility"],
        "exclusion_reason": enrollment["exclusion_reason"],
        "opportunity": enrollment["opportunity"],
        "evidence_refs": evidence,
        "memory_available_at": enrolled_at,
        "memory_manifest": manifest,
        "memory_manifest_digest": manifest_digest,
        "source_snapshot": source,
        "previous_entry_digest": previous,
        "usage_sample_id": sample_id,
        "enrolled_at": enrolled_at,
    }


def chain_valid(cohort: dict[str, Any], tasks: list[dict[str, Any]]) -> bool:
    previous = str(cohort["protocol_digest"])
    for sequence, task in enumerate(tasks, 1):
        if int(task["sequence_no"]) != sequence or task["previous_entry_digest"] != previous:
            return False
        immutable = entry_payload(
            cohort["cohort_id"], sequence, task["task_id"], task["task_digest"],
            task, task["evidence_refs"] or [], task["enrolled_at"],
            task["memory_manifest"], task["memory_manifest_digest"],
            task["source_snapshot"], previous, task.get("usage_sample_id"),
        )
        if canonical_digest(immutable) != task["entry_digest"]:
            return False
        previous = task["entry_digest"]
    return previous == cohort["chain_head_digest"]


def cohort_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "prospective-agent-cohort-state/v1",
        "cohort_id": value["cohort_id"],
        "status": value["status"],
        "task_type": value["task_type"],
        "target_presented_tasks": int(value["target_presented_tasks"]),
        "protocol_digest": value["protocol_digest"],
        "registered_at": value["registered_at"],
    }


def task_projection(value: dict[str, Any]) -> dict[str, Any]:
    result = {
        "schema_version": "prospective-agent-cohort-task/v1",
        "task_id": value["task_id"],
        "sequence_no": int(value["sequence_no"]),
        "status": value["status"],
        "eligibility": value["eligibility"],
        "opportunity": value["opportunity"],
        "task_digest": value["task_digest"],
        "memory_available_at": value["memory_available_at"],
        "memory_manifest_digest": value["memory_manifest_digest"],
        "entry_digest": value["entry_digest"],
        "replay_eligible": bool(value["replay_eligible"]),
    }
    if value.get("usage_metrics") is not None:
        result["usage_metrics"] = value["usage_metrics"]
    if value.get("benchmark_metrics") is not None:
        result["benchmark_metrics"] = value["benchmark_metrics"]
    if value.get("outcome") is not None:
        result["outcome"] = value["outcome"]
        result["verification"] = value["verification"]
    return result
