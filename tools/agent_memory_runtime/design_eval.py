# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .design_check import check_design_proposal, validate_proposal
from .design_compare import compare_designs
from .design_protocol import load_json_object, normalize_contract, normalize_rule
from .design_verify import verify_design
from .records import output
from .storage import ensure_initialized, resolve_project


def eval_design_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    pack = load_json_object(Path(args.cases), "design evaluation cases")
    payload = evaluate_case_pack(project, pack)
    output(payload, args.json)


def evaluate_case_pack(project: Any, pack: dict[str, Any]) -> dict[str, Any]:
    if pack.get("schema_version") != "design-eval-cases/v1":
        raise SystemExit("unsupported design evaluation case schema")
    cases = pack.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SystemExit("design evaluation cases must contain a non-empty cases list")
    results = [evaluate_case(project, item, index) for index, item in enumerate(cases)]
    passed = sum(1 for item in results if item["status"] == "pass")
    finding_expected = sum(item["finding_expectations"] for item in results)
    finding_matched = sum(item["finding_matches"] for item in results)
    preference_cases = [item for item in results if item["preference_expected"]]
    preference_matches = sum(1 for item in preference_cases if item["preference_matched"])
    verified = [item for item in results if item["planned_file_recall"] is not None]
    proposal_count = sum(item["proposal_count"] for item in results)
    assumption_count = sum(item["assumption_count"] for item in results)
    coverage_items = sum(item["coverage_item_count"] for item in results)
    supported_items = sum(item["supported_coverage_count"] for item in results)
    ready_plans = sum(item["ready_plan_count"] for item in results)
    return {
        "schema_version": "design-eval-result/v1",
        "status": "pass" if passed == len(results) else "fail",
        "metrics": {
            "case_pass_rate": round(passed / len(results), 4),
            "finding_recall": round(finding_matched / finding_expected, 4) if finding_expected else 1.0,
            "candidate_preference_accuracy": round(preference_matches / len(preference_cases), 4) if preference_cases else 1.0,
            "contract_validity_rate": 1.0,
            "planned_file_recall": round(sum(item["planned_file_recall"] for item in verified) / len(verified), 4) if verified else 1.0,
            "unsupported_assumption_rate": round(assumption_count / proposal_count, 4) if proposal_count else 0.0,
            "supported_coverage_rate": round(supported_items / coverage_items, 4) if coverage_items else 1.0,
            "change_plan_ready_rate": round(ready_plans / proposal_count, 4) if proposal_count else 1.0,
            "input_payload_bytes": len(json.dumps(pack, ensure_ascii=False).encode("utf-8")),
            "case_count": len(results),
        },
        "cases": results,
        "audit": {"persisted": False, "llm_used": False},
    }


def evaluate_case(project: Any, value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"design case {index} must be an object")
    case_id = value.get("id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise SystemExit(f"design case {index} requires an id")
    raw_proposals = value.get("proposals")
    if not isinstance(raw_proposals, list) or not raw_proposals:
        raise SystemExit(f"design case {case_id} requires proposals")
    proposals = [validate_proposal(dict(item)) for item in raw_proposals if isinstance(item, dict)]
    if len(proposals) != len(raw_proposals):
        raise SystemExit(f"design case {case_id} proposals must be objects")
    contract = normalize_contract(value.get("contract"), proposals[0]["goal"])
    raw_rules = value.get("rules", [])
    if not isinstance(raw_rules, list):
        raise SystemExit(f"design case {case_id} rules must be a list")
    rules = [normalize_rule(rule, rule_index) for rule_index, rule in enumerate(raw_rules)]
    evaluations = {item["id"]: check_design_proposal(project, item, contract, rules) for item in proposals}
    expected_findings = value.get("expected_findings", {})
    if not isinstance(expected_findings, dict):
        raise SystemExit(f"design case {case_id} expected_findings must be an object")
    finding_expectations = 0
    finding_matches = 0
    failures: list[str] = []
    for candidate_id, codes in expected_findings.items():
        if not isinstance(codes, list):
            raise SystemExit(f"design case {case_id} expected finding codes must be a list")
        actual_codes = finding_codes(evaluations.get(candidate_id))
        for code in codes:
            finding_expectations += 1
            if code in actual_codes:
                finding_matches += 1
            else:
                failures.append(f"{candidate_id} missing finding {code}")
    expected_preference = value.get("expected_recommended")
    actual_preference = None
    preference_matched = True
    if expected_preference is not None:
        if len(proposals) < 2:
            raise SystemExit(f"design case {case_id} needs two proposals for preference evaluation")
        actual_preference = compare_designs(project, proposals, contract, rules)["recommended_candidate"]
        preference_matched = actual_preference == expected_preference
        if not preference_matched:
            failures.append(f"recommended {actual_preference}, expected {expected_preference}")
    expected_verify = value.get("expected_verify_status")
    planned_file_recall = None
    if expected_verify is not None:
        actual_files = value.get("actual_files", [])
        if not isinstance(actual_files, list) or not all(isinstance(path, str) for path in actual_files):
            raise SystemExit(f"design case {case_id} actual_files must be a string list")
        executed_tests = value.get("executed_tests", [])
        if not isinstance(executed_tests, list) or not all(isinstance(item, str) for item in executed_tests):
            raise SystemExit(f"design case {case_id} executed_tests must be a string list")
        verify_payload = verify_design(project, proposals[0], contract, rules, actual_files, executed_tests)
        verify_status = verify_payload["status"]
        planned_file_recall = verify_payload["metrics"]["planned_file_recall"]
        if verify_status != expected_verify:
            failures.append(f"verification {verify_status}, expected {expected_verify}")
    return {
        "id": case_id,
        "status": "fail" if failures else "pass",
        "failures": failures,
        "finding_expectations": finding_expectations,
        "finding_matches": finding_matches,
        "preference_expected": expected_preference is not None,
        "preference_matched": preference_matched,
        "actual_recommended": actual_preference,
        "proposal_count": len(proposals),
        "assumption_count": sum(len(proposal["assumptions"]) for proposal in proposals),
        "planned_file_recall": planned_file_recall,
        "coverage_item_count": sum(
            len(item["quality_scenarios"]) + len(item["constraint_coverage"])
            for item in evaluations.values()
        ),
        "supported_coverage_count": sum(
            sum(1 for coverage in item["quality_scenarios"] + item["constraint_coverage"] if coverage["coverage_state"] in {"supported", "verified"})
            for item in evaluations.values()
        ),
        "ready_plan_count": sum(1 for item in evaluations.values() if item["change_plan"]["status"] == "ready"),
    }


def finding_codes(evaluation: dict[str, Any] | None) -> set[str]:
    if not evaluation:
        return set()
    return {item["code"] for item in evaluation["errors"] + evaluation["warnings"]}
