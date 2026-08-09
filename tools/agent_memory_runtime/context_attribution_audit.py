# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .records import output


AUDIT_SCHEMA = "agent-context-attribution-audit/v1"
CONTEXT_RESULT_SCHEMA = "agent-context-capability-result/v1"
AGENT_RESULT_SCHEMA = "agent-benchmark-result/v1"
OBSERVED_LAYERS = (
    "oracle_evidence_insufficient",
    "candidate_recall",
    "localizer_projection",
    "compact_projection",
    "source_excerpt_projection",
    "non_gating_evidence_observation",
    "unresolved",
)


def eval_context_attribution_audit_command(args: argparse.Namespace) -> None:
    context_paths = [Path(value).expanduser() for value in args.context_result]
    case_paths = [Path(value).expanduser() for value in args.case_pack]
    agent_path = Path(args.agent_result).expanduser() if args.agent_result else None
    target = Path(args.target).expanduser()
    if target.exists():
        raise SystemExit("context attribution audit target already exists")
    if len(context_paths) != len(case_paths):
        raise SystemExit("context attribution audit requires one case pack per context result")
    result = build_context_attribution_audit(context_paths, case_paths, agent_path)
    if not target.parent.is_dir():
        raise SystemExit("context attribution audit target parent does not exist")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output(result, args.json)


def build_context_attribution_audit(
    context_paths: list[Path], case_paths: list[Path], agent_path: Path | None = None,
) -> dict[str, Any]:
    case_provenance = load_case_provenance(case_paths)
    inputs = [artifact("context_result", path) for path in context_paths]
    inputs.extend(artifact("case_pack", path) for path in case_paths)
    agent_cases: dict[str, dict[str, Any]] = {}
    if agent_path is not None:
        agent = load_json(agent_path, "agent result")
        if agent.get("schema_version") != AGENT_RESULT_SCHEMA:
            raise SystemExit("context attribution audit requires an agent benchmark result")
        agent_cases = indexed_records(agent.get("cases"), "case_id", "agent result")
        inputs.append(artifact("agent_result", agent_path))
    cases: list[dict[str, Any]] = []
    for path in context_paths:
        result = load_json(path, "context result")
        if result.get("schema_version") != CONTEXT_RESULT_SCHEMA:
            raise SystemExit("context attribution audit requires context capability results")
        for observation in records(result.get("cases")):
            scenario_id = str(observation.get("scenario_id") or observation.get("case_id") or "")
            provenance = case_provenance.get(scenario_id)
            if provenance is None:
                raise SystemExit(f"context result case has no supplied case-pack provenance: {scenario_id}")
            cases.append(case_attribution(observation, provenance, agent_cases.get(scenario_id)))
    if not cases:
        raise SystemExit("context attribution audit contains no cases")
    return {
        "schema_version": AUDIT_SCHEMA,
        "mode": "read_only_saved_development_observation",
        "input_artifacts": inputs,
        "case_count": len(cases),
        "cases": sorted(cases, key=lambda item: item["case_id"]),
        "cross_case": cross_case_summary(cases),
        "policy": {
            "serving_change_authorized": False,
            "architecture_change_authorized": False,
            "rerun_required": False,
            "reason": (
                "Saved Development observations classify visible loss layers only. "
                "They do not establish a root cause, change a consumed result, or authorize serving changes."
            ),
        },
    }


def load_case_provenance(paths: list[Path]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for path in paths:
        pack = load_json(path, "case pack")
        for case in records(pack.get("cases")):
            case_id = str(case.get("id") or "")
            provenance = case.get("provenance") if isinstance(case.get("provenance"), dict) else {}
            source = case.get("source") if isinstance(case.get("source"), dict) else {}
            repository = str(pack.get("source_repository") or "").strip()
            family = str(provenance.get("source_family") or repository or "").strip()
            review = case.get("review") if isinstance(case.get("review"), dict) else {}
            if not case_id or not family or not source.get("before_revision"):
                raise SystemExit("case pack must provide id, source revision, and source family")
            if case_id in result:
                raise SystemExit(f"duplicate context attribution case id: {case_id}")
            result[case_id] = {
                "source_family": family,
                "source_repository": repository or family,
                "before_revision": str(source["before_revision"]),
                "reviewed": str(bool(review.get("source_diff_reviewed") and review.get("symptom_source_reviewed"))).lower(),
            }
    return result


def case_attribution(
    observation: dict[str, Any], provenance: dict[str, str], agent_case: dict[str, Any] | None,
) -> dict[str, Any]:
    funnel = observation.get("evidence_funnel") if isinstance(observation.get("evidence_funnel"), dict) else {}
    stages = funnel.get("stages") if isinstance(funnel.get("stages"), dict) else {}
    checks = observation.get("checks") if isinstance(observation.get("checks"), dict) else {}
    status = str(observation.get("status") or "unknown")
    oracle_status = "reviewed" if provenance["reviewed"] == "true" else "incomplete"
    layer, reason_codes = observed_layer(status, stages, checks, oracle_status)
    return {
        "case_id": str(observation.get("case_id") or ""),
        "scenario_id": str(observation.get("scenario_id") or observation.get("case_id") or ""),
        "source_family": provenance["source_family"],
        "source_repository": provenance["source_repository"],
        "source_revision": provenance["before_revision"],
        "oracle_review_status": oracle_status,
        "context_status": status,
        "observed_layer": layer,
        "reason_codes": reason_codes,
        "first_loss_signal": funnel.get("first_loss"),
        "stage_observations": {key: stages.get(key) for key in (
            "candidate_file", "localizer_file", "callable", "source_range",
            "evidence_primary", "compact_primary", "compact_anchor",
        )},
        "failed_context_checks": sorted(key for key, value in checks.items() if value is False),
        "missing_expected_anchor_count": len(strings(observation.get("missing_expected_anchors"))),
        "agent_utilization": agent_utilization(agent_case),
        "evidence_level": "development_observation",
    }


def observed_layer(
    status: str, stages: dict[str, Any], checks: dict[str, Any], oracle_status: str,
) -> tuple[str, list[str]]:
    if oracle_status != "reviewed":
        return "oracle_evidence_insufficient", ["oracle_source_or_symptom_review_missing"]
    if status == "pass":
        if stages.get("evidence_primary") is False:
            return "non_gating_evidence_observation", ["funnel_primary_is_not_a_context_gate"]
        return "unresolved", ["no_failed_context_gate"]
    if stages.get("candidate_file") is False:
        return "candidate_recall", ["candidate_file_missing_expected_anchor"]
    if stages.get("localizer_file") is False:
        return "localizer_projection", ["localizer_file_dropped_candidate"]
    if stages.get("compact_primary") is False or stages.get("compact_anchor") is False:
        return "compact_projection", ["compact_projection_dropped_localized_anchor"]
    if checks.get("expected_source_excerpt_returned") is False:
        return "source_excerpt_projection", ["source_excerpt_missing_after_anchor_selection"]
    return "unresolved", ["saved_observation_does_not_identify_a_single_loss_layer"]


def agent_utilization(agent_case: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(agent_case, dict):
        return {"status": "not_supplied", "reason": "no_per_case_agent_result"}
    variants = agent_case.get("variants") if isinstance(agent_case.get("variants"), dict) else {}
    memory = variants.get("memory") if isinstance(variants.get("memory"), dict) else {}
    if not memory:
        return {"status": "unresolved", "reason": "agent_memory_variant_missing"}
    return {
        "status": "unresolved_unbound",
        "reason": "saved_agent_result_has_no_verified_context_result_digest_binding",
        "memory_context_present": float(memory.get("memory_context_bytes") or 0) > 0,
        "memory_anchor_hit_count": memory.get("memory_anchor_hit_count"),
        "trial_non_regression_rate": agent_case.get("trial_non_regression_rate"),
    }


def cross_case_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[case["observed_layer"]].append(case)
    candidates = []
    for layer in OBSERVED_LAYERS:
        members = grouped.get(layer, [])
        repositories = sorted({item["source_repository"] for item in members})
        if layer in {
            "oracle_evidence_insufficient", "unresolved", "non_gating_evidence_observation",
        } or not members:
            continue
        candidates.append({
            "existing_boundary": layer,
            "case_ids": sorted(item["case_id"] for item in members),
            "distinct_source_repository_count": len(repositories),
            "distinct_source_repositories": repositories,
            "independent_reproduction_candidate": len(repositories) >= 2,
            "repair_contract_authorized": False,
        })
    counts = Counter(case["observed_layer"] for case in cases)
    return {
        "observed_layer_counts": dict(sorted(counts.items())),
        "boundary_hypotheses": candidates,
        "agent_utilization_status": "unresolved_unbound" if any(
            case["agent_utilization"]["status"] == "unresolved_unbound" for case in cases
        ) else "not_supplied",
        "next_action": (
            "Create one project-neutral Development reproduction for each boundary hypothesis "
            "before considering a serving repair; do not combine different observed layers into one contract."
        ),
    }


def artifact(kind: str, path: Path) -> dict[str, str]:
    if not path.is_file():
        raise SystemExit(f"context attribution audit {kind} file not found: {path}")
    return {"kind": kind, "file_name": path.name, "sha256": digest(path)}


def load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"{label} file not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{label} JSON must be an object")
    return value


def indexed_records(value: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records(value):
        identifier = str(record.get(key) or "")
        if not identifier or identifier in result:
            raise SystemExit(f"{label} has missing or duplicate {key}")
        result[identifier] = record
    return result


def records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def strings(value: Any) -> list[str]:
    return [str(item) for item in value if str(item)] if isinstance(value, list) else []


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
