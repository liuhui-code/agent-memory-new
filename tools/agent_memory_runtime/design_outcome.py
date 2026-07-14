# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from typing import Any

from .design_protocol import load_json_object
from .models import Project
from .records import output, row_dict
from .storage import connect, ensure_initialized, now_iso, resolve_project


METRIC_FIELDS = (
    "planned_file_recall",
    "unplanned_file_ratio",
    "planned_symbol_recall",
    "scenario_verification_rate",
)


def design_outcome_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    verification = load_json_object(args.verification, "design verification")
    payload = record_design_outcome(project, verification, args.outcome)
    output(payload, args.json)


def record_design_outcome(project: Project, verification: dict[str, Any], outcome: str) -> dict[str, Any]:
    if not str(verification.get("schema_version") or "").startswith("design-verification/v"):
        raise SystemExit("design outcome requires a design verification payload")
    if outcome not in {"success", "partial", "failure"}:
        raise SystemExit("unsupported design outcome")
    metrics = verification.get("metrics") or {}
    if not isinstance(metrics, dict):
        raise SystemExit("design verification metrics must be an object")
    values = {field: metric(metrics, field) for field in METRIC_FIELDS}
    failed_tests = int(metrics.get("failed_test_count") or 0)
    triggers = (verification.get("verification") or {}).get("replan_triggers") or []
    if not isinstance(triggers, list):
        raise SystemExit("design verification replan triggers must be a list")
    features = calibration_features(verification.get("calibration_features"))
    with connect(project) as conn:
        cursor = conn.execute(
            """
            INSERT INTO design_outcomes(
              project_id, candidate_id, contract_id, verification_status, outcome,
              baseline_revision, current_revision,
              planned_file_recall, unplanned_file_ratio, planned_symbol_recall,
              scenario_verification_rate, failed_test_count, replan_count,
              archetype, change_size_bucket, risk_count, api_change_count,
              graph_delta_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                str(verification.get("candidate_id") or "unknown"),
                str(verification.get("contract_id") or "default"),
                str(verification.get("status") or "unknown"),
                outcome,
                int(verification.get("baseline_revision") or 0),
                int(verification.get("current_revision") or 0),
                values["planned_file_recall"],
                values["unplanned_file_ratio"],
                values["planned_symbol_recall"],
                values["scenario_verification_rate"],
                max(0, failed_tests),
                len(triggers),
                features["archetype"],
                features["change_size_bucket"],
                features["risk_count"],
                features["api_change_count"],
                features["graph_delta_count"],
                now_iso(),
            ),
        )
        conn.execute(
            """
            DELETE FROM design_outcomes
            WHERE project_id = ? AND id NOT IN (
              SELECT id FROM design_outcomes
              WHERE project_id = ? ORDER BY id DESC LIMIT 1000
            )
            """,
            (project.project_id, project.project_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM design_outcomes WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return outcome_payload(row_dict(row))


def metric(metrics: dict[str, Any], field: str) -> float:
    try:
        value = float(metrics.get(field) or 0.0)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"invalid design outcome metric: {field}") from exc
    return max(0.0, min(value, 1.0))


def outcome_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "design-outcome/v1",
        "id": int(row["id"]),
        "project_id": row["project_id"],
        "candidate_id": row["candidate_id"],
        "contract_id": row["contract_id"],
        "verification_status": row["verification_status"],
        "outcome": row["outcome"],
        "baseline_revision": int(row["baseline_revision"] or 0),
        "current_revision": int(row["current_revision"] or 0),
        "metrics": {field: float(row[field] or 0.0) for field in METRIC_FIELDS},
        "failed_test_count": int(row["failed_test_count"] or 0),
        "replan_count": int(row["replan_count"] or 0),
        "calibration_features": {
            "archetype": row["archetype"],
            "change_size_bucket": row["change_size_bucket"],
            "risk_count": int(row["risk_count"] or 0),
            "api_change_count": int(row["api_change_count"] or 0),
            "graph_delta_count": int(row["graph_delta_count"] or 0),
        },
        "created_at": row["created_at"],
    }


def design_calibration_summary(project: Project) -> dict[str, Any]:
    with connect(project) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS outcome_count,
                   AVG(planned_file_recall) AS average_planned_file_recall,
                   AVG(unplanned_file_ratio) AS average_unplanned_file_ratio,
                   AVG(planned_symbol_recall) AS average_planned_symbol_recall,
                   AVG(scenario_verification_rate) AS average_scenario_verification_rate,
                   SUM(failed_test_count) AS failed_test_count,
                   SUM(replan_count) AS replan_count
            FROM design_outcomes WHERE project_id = ?
            """,
            (project.project_id,),
        ).fetchone()
        active_profiles = conn.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT archetype, change_size_bucket
              FROM design_outcomes WHERE project_id = ?
              GROUP BY archetype, change_size_bucket HAVING COUNT(*) >= 5
            )
            """,
            (project.project_id,),
        ).fetchone()[0]
    result = row_dict(row)
    return {
        "outcome_count": int(result.get("outcome_count") or 0),
        "average_planned_file_recall": rounded(result.get("average_planned_file_recall")),
        "average_unplanned_file_ratio": rounded(result.get("average_unplanned_file_ratio")),
        "average_planned_symbol_recall": rounded(result.get("average_planned_symbol_recall")),
        "average_scenario_verification_rate": rounded(result.get("average_scenario_verification_rate")),
        "failed_test_count": int(result.get("failed_test_count") or 0),
        "replan_count": int(result.get("replan_count") or 0),
        "active_profile_count": int(active_profiles or 0),
        "authority": "calibration_only",
        "can_create_hard_rules": False,
    }


def rounded(value: Any) -> float:
    return round(float(value or 0.0), 4)


def calibration_features(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    archetype = str(raw.get("archetype") or "general")[:80]
    bucket = str(raw.get("change_size_bucket") or "small")
    if bucket not in {"small", "medium", "large"}:
        bucket = "small"
    return {
        "archetype": archetype,
        "change_size_bucket": bucket,
        "risk_count": bounded_count(raw.get("risk_count")),
        "api_change_count": bounded_count(raw.get("api_change_count")),
        "graph_delta_count": bounded_count(raw.get("graph_delta_count")),
    }


def bounded_count(value: Any) -> int:
    try:
        return max(0, min(int(value or 0), 100_000))
    except (TypeError, ValueError) as exc:
        raise SystemExit("invalid design calibration count") from exc
