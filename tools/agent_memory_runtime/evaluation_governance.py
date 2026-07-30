# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


GOVERNANCE_SCHEMA = "agent-evaluation-governance/v1"
PROMOTION_SCHEMA = "agent-context-promotion-policy/v1"
SPLITS = {"development", "calibration", "holdout"}
POLICIES = {"editable", "frozen", "sealed"}
ISOLATION_KINDS = {"project_neutral", "independent_source", "external_holdout"}


def validate_evaluation_governance(pack: dict[str, Any]) -> dict[str, Any]:
    """Validate optional split metadata without invalidating legacy case packs."""
    governance = pack.get("governance")
    governance = governance if isinstance(governance, dict) else {}
    value = governance.get("evaluation")
    if value is None:
        return {"status": "legacy_unclassified", "enforced": False}
    if not isinstance(value, dict) or value.get("schema_version") != GOVERNANCE_SCHEMA:
        raise SystemExit(f"evaluation governance must use {GOVERNANCE_SCHEMA}")
    split = required(value, "split")
    policy = required(value, "change_policy")
    isolation = required(value, "source_isolation")
    if split not in SPLITS or policy not in POLICIES or isolation not in ISOLATION_KINDS:
        raise SystemExit("evaluation governance has unsupported split, policy, or isolation")
    validate_suite(str(pack.get("suite") or ""), split, policy, isolation)
    cases = pack.get("cases") if isinstance(pack.get("cases"), list) else []
    defaults = lineage_defaults(value)
    effective_defaults = {} if split == "holdout" else defaults
    missing = [
        str(item.get("id") or "<unknown>")
        for item in cases
        if not case_lineage(item, effective_defaults)
    ]
    if missing:
        if split == "holdout" and defaults:
            raise SystemExit(f"holdout requires explicit case lineage: {', '.join(missing)}")
        raise SystemExit(f"evaluation governance missing case lineage: {', '.join(missing)}")
    inherited = bool(defaults) and any(not case_lineage(item) for item in cases)
    return {
        "status": "classified",
        "enforced": True,
        "schema_version": GOVERNANCE_SCHEMA,
        "split": split,
        "change_policy": policy,
        "source_isolation": isolation,
        "case_count": len(cases),
        "lineage_mode": "pack_defaults" if inherited else "case_explicit",
        "tuning_allowed": split == "development" and policy == "editable",
    }


def assess_promotion_policy(
    system_context_gate: str,
    calibration_gate: str,
    governance: dict[str, Any],
    case_seal: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    if system_context_gate != "pass":
        reasons.append("system_context_gate_failed")
    if calibration_gate not in {"pass", "not_required"}:
        reasons.append("calibration_gate_failed")
    if not governance.get("enforced"):
        reasons.append("evaluation_governance_not_enforced")
    elif governance.get("split") != "holdout":
        reasons.append("evaluation_split_not_holdout")
    elif case_seal.get("status") != "verified" or not case_seal.get("required"):
        reasons.append("holdout_seal_not_verified")
    return {
        "schema_version": PROMOTION_SCHEMA,
        "eligible": not reasons,
        "reasons": reasons,
        "next_gate": promotion_next_gate(reasons),
    }


def promotion_next_gate(reasons: list[str]) -> str:
    priorities = (
        ("system_context_gate_failed", "repair_context_supply"),
        ("calibration_gate_failed", "repair_calibration_coverage"),
        ("evaluation_governance_not_enforced", "classify_evaluation_pack"),
        ("evaluation_split_not_holdout", "prepare_external_holdout"),
        ("holdout_seal_not_verified", "seal_reviewed_holdout"),
    )
    return next((gate for reason, gate in priorities if reason in reasons), "paired_external_agent_ab")


def validate_suite(suite: str, split: str, policy: str, isolation: str) -> None:
    if suite == "holdout" and (split != "holdout" or policy != "sealed"):
        raise SystemExit("holdout suite requires holdout split and sealed policy")
    if split == "holdout" and isolation != "external_holdout":
        raise SystemExit("holdout split requires external_holdout isolation")
    if split == "calibration" and policy != "frozen":
        raise SystemExit("calibration split requires frozen policy")
    if split == "development" and policy != "editable":
        raise SystemExit("development split requires editable policy")


def case_lineage(value: Any, defaults: dict[str, str] | None = None) -> bool:
    if not isinstance(value, dict):
        return False
    provenance = value.get("provenance")
    if provenance is not None and not isinstance(provenance, dict):
        return False
    provenance = provenance or {}
    defaults = defaults or {}
    return bool(str(provenance.get("source_family") or defaults.get("source_family") or "").strip()) and bool(
        str(provenance.get("independence_basis") or defaults.get("independence_basis") or "").strip()
    )


def lineage_defaults(value: dict[str, Any]) -> dict[str, str]:
    raw = value.get("lineage_defaults")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise SystemExit("evaluation governance lineage_defaults must be an object")
    defaults = {
        "source_family": str(raw.get("source_family") or "").strip(),
        "independence_basis": str(raw.get("independence_basis") or "").strip(),
    }
    if not all(defaults.values()):
        raise SystemExit("evaluation governance lineage_defaults requires source_family and independence_basis")
    return defaults


def required(value: dict[str, Any], key: str) -> str:
    text = str(value.get(key) or "").strip()
    if not text:
        raise SystemExit(f"evaluation governance requires {key}")
    return text
