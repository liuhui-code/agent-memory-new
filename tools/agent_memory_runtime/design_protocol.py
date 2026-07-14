# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONTRACT_SCHEMA = "design-contract/v1"
CONTRACT_SCHEMA_V2 = "design-contract/v2"
DELTA_SCHEMA = "design-delta/v1"
DELTA_SCHEMA_V2 = "design-delta/v2"
EVALUATION_SCHEMA = "design-evaluation/v1"
EVALUATION_SCHEMA_V2 = "design-evaluation/v2"
INTENT_SCHEMA = "design-intent/v1"
RULES_SCHEMA = "design-rules/v1"
MAX_CANDIDATES = 8
MAX_RULES = 200
MAX_NODES = 200
MAX_EDGES = 400


def load_json_object(path: str | Path, label: str) -> dict[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"unable to read {label}: {source}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be a JSON object")
    return value


def normalize_contract(value: dict[str, Any] | None, fallback_goal: str = "") -> dict[str, Any]:
    raw = dict(value or {})
    schema = raw.get("schema_version", CONTRACT_SCHEMA)
    if schema not in {CONTRACT_SCHEMA, CONTRACT_SCHEMA_V2}:
        raise SystemExit(f"unsupported design contract schema: {schema}")
    goal = raw.get("goal") or fallback_goal
    if not isinstance(goal, str) or not goal.strip():
        raise SystemExit("design contract requires a non-empty goal")
    contract_id = raw.get("id") or "default"
    if not isinstance(contract_id, str) or not contract_id.strip():
        raise SystemExit("design contract id must be a non-empty string")
    constraints = string_list(raw.get("constraints", []), "design contract constraints")
    scenarios = raw.get("quality_scenarios", [])
    if not isinstance(scenarios, list) or len(scenarios) > 50:
        raise SystemExit("design contract quality_scenarios must be a list of at most 50 items")
    normalized_scenarios = [normalize_scenario(item, index) for index, item in enumerate(scenarios)]
    return {
        "schema_version": schema,
        "id": contract_id.strip(),
        "intent_id": string_value(raw.get("intent_id", ""), "design contract intent_id", allow_empty=True),
        "goal": goal.strip(),
        "constraints": constraints,
        "quality_scenarios": normalized_scenarios,
    }


def normalize_scenario(value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"quality_scenarios[{index}] must be an object")
    required = ("id", "attribute", "stimulus", "response", "measure")
    result: dict[str, Any] = {}
    for field in required:
        item = value.get(field)
        if not isinstance(item, str) or not item.strip():
            raise SystemExit(f"quality_scenarios[{index}].{field} must be a non-empty string")
        result[field] = item.strip()
    for field in ("environment", "artifact"):
        item = value.get(field, "")
        if not isinstance(item, str):
            raise SystemExit(f"quality_scenarios[{index}].{field} must be a string")
        result[field] = item.strip()
    priority = value.get("priority", "medium")
    if priority not in {"high", "medium", "low"}:
        raise SystemExit(f"quality_scenarios[{index}].priority must be high, medium, or low")
    result["priority"] = priority
    requirements = value.get("evidence_requirements", [])
    result["evidence_requirements"] = string_list(requirements, f"quality_scenarios[{index}].evidence_requirements")
    return result


def normalize_delta_metadata(value: dict[str, Any]) -> dict[str, Any]:
    schema = value.get("schema_version", DELTA_SCHEMA)
    if schema not in {DELTA_SCHEMA, DELTA_SCHEMA_V2}:
        raise SystemExit(f"unsupported design delta schema: {schema}")
    candidate_id = value.get("id") or "candidate"
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise SystemExit("design proposal id must be a non-empty string")
    value["schema_version"] = schema
    value["id"] = candidate_id.strip()
    value["contract_id"] = string_value(value.get("contract_id", "default"), "contract_id")
    value["quality_coverage"] = string_list(value.get("quality_coverage", []), "quality_coverage")
    value["constraint_coverage"] = string_list(value.get("constraint_coverage", []), "constraint_coverage")
    raw_evidence = value.get("coverage_evidence", [])
    if not isinstance(raw_evidence, list) or len(raw_evidence) > 100:
        raise SystemExit("coverage_evidence must be a list of at most 100 items")
    value["coverage_evidence"] = [normalize_coverage_evidence(item, index) for index, item in enumerate(raw_evidence)]
    verification = value.get("verification", {})
    if not isinstance(verification, dict):
        raise SystemExit("design proposal verification must be an object")
    value["verification"] = {
        "tests": string_list(verification.get("tests", []), "verification.tests"),
        "observability": string_list(verification.get("observability", []), "verification.observability"),
    }
    if len(value.get("add_nodes", [])) + len(value.get("modify_nodes", [])) > MAX_NODES:
        raise SystemExit(f"design proposal exceeds the {MAX_NODES} node limit")
    if len(value.get("add_edges", [])) + len(value.get("remove_edges", [])) > MAX_EDGES:
        raise SystemExit(f"design proposal exceeds the {MAX_EDGES} edge limit")
    return value


def normalize_coverage_evidence(value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"coverage_evidence[{index}] must be an object")
    target_type = value.get("target_type", "scenario")
    if target_type not in {"scenario", "constraint"}:
        raise SystemExit(f"coverage_evidence[{index}].target_type must be scenario or constraint")
    return {
        "target_type": target_type,
        "target_id": string_value(value.get("target_id"), f"coverage_evidence[{index}].target_id"),
        "delta_refs": string_list(value.get("delta_refs", []), f"coverage_evidence[{index}].delta_refs"),
        "repository_refs": string_list(value.get("repository_refs", []), f"coverage_evidence[{index}].repository_refs"),
        "verification_refs": string_list(value.get("verification_refs", []), f"coverage_evidence[{index}].verification_refs"),
    }


def normalize_intent(value: dict[str, Any] | None, fallback_goal: str) -> dict[str, Any]:
    raw = dict(value or {})
    schema = raw.get("schema_version", INTENT_SCHEMA)
    if schema != INTENT_SCHEMA:
        raise SystemExit(f"unsupported design intent schema: {schema}")
    goal = string_value(raw.get("goal", fallback_goal), "design intent goal")
    return {
        "schema_version": INTENT_SCHEMA,
        "id": string_value(raw.get("id", "default"), "design intent id"),
        "goal": goal,
        "scope": string_list(raw.get("scope", []), "design intent scope"),
        "exclusions": string_list(raw.get("exclusions", []), "design intent exclusions"),
        "acceptance_criteria": string_list(raw.get("acceptance_criteria", []), "design intent acceptance_criteria"),
        "constraints": string_list(raw.get("constraints", []), "design intent constraints"),
        "open_questions": string_list(raw.get("open_questions", []), "design intent open_questions"),
    }


def load_intent(path: str | None, fallback_goal: str) -> dict[str, Any]:
    value = load_json_object(path, "design intent") if path else None
    return normalize_intent(value, fallback_goal)


def apply_intent_to_contract(contract: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    result = dict(contract)
    result["intent_id"] = contract.get("intent_id") or intent["id"]
    result["constraints"] = list(dict.fromkeys([*contract["constraints"], *intent["constraints"]]))
    return result


def load_contract(path: str | None, fallback_goal: str) -> dict[str, Any]:
    value = load_json_object(path, "design contract") if path else None
    return normalize_contract(value, fallback_goal)


def load_rules(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    value = load_json_object(path, "design rules")
    schema = value.get("schema_version", RULES_SCHEMA)
    if schema != RULES_SCHEMA:
        raise SystemExit(f"unsupported design rules schema: {schema}")
    rules = value.get("rules", [])
    if not isinstance(rules, list) or len(rules) > MAX_RULES:
        raise SystemExit(f"design rules must be a list of at most {MAX_RULES} items")
    return [normalize_rule(item, index) for index, item in enumerate(rules)]


def normalize_rule(value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"rules[{index}] must be an object")
    result = dict(value)
    for field in ("id", "kind"):
        result[field] = string_value(value.get(field), f"rules[{index}].{field}")
    severity = value.get("severity", "error")
    if severity not in {"error", "warning"}:
        raise SystemExit(f"rules[{index}].severity must be error or warning")
    if result["kind"] not in {"forbid_edge", "require_edge", "single_owner"}:
        raise SystemExit(f"rules[{index}].kind is not supported: {result['kind']}")
    result["severity"] = severity
    result["rationale"] = string_value(value.get("rationale", ""), f"rules[{index}].rationale", allow_empty=True)
    selectors = (
        "relation", "source_layer", "source_kind", "source_path_prefix",
        "target_layer", "target_kind", "target_path_prefix",
    )
    for field in selectors:
        if field in value:
            result[field] = string_value(value[field], f"rules[{index}].{field}")
    if result["kind"] != "single_owner" and not any(result.get(field) for field in selectors):
        raise SystemExit(f"rules[{index}] requires a relation or node selector")
    return result


def string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise SystemExit(f"{label} must be a list of non-empty strings")
    return list(dict.fromkeys(item.strip() for item in value))


def string_value(value: Any, label: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise SystemExit(f"{label} must be a {'string' if allow_empty else 'non-empty string'}")
    return value.strip()
