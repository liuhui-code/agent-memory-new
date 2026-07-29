# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


GOVERNANCE_SCHEMA = "agent-evaluation-governance/v1"
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
    missing = [str(item.get("id") or "<unknown>") for item in cases if not case_lineage(item)]
    if missing:
        raise SystemExit(f"evaluation governance missing case lineage: {', '.join(missing)}")
    return {
        "status": "classified",
        "enforced": True,
        "schema_version": GOVERNANCE_SCHEMA,
        "split": split,
        "change_policy": policy,
        "source_isolation": isolation,
        "case_count": len(cases),
        "tuning_allowed": split == "development" and policy == "editable",
    }


def validate_suite(suite: str, split: str, policy: str, isolation: str) -> None:
    if suite == "holdout" and (split != "holdout" or policy != "sealed"):
        raise SystemExit("holdout suite requires holdout split and sealed policy")
    if split == "holdout" and isolation != "external_holdout":
        raise SystemExit("holdout split requires external_holdout isolation")
    if split == "calibration" and policy != "frozen":
        raise SystemExit("calibration split requires frozen policy")
    if split == "development" and policy != "editable":
        raise SystemExit("development split requires editable policy")


def case_lineage(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    provenance = value.get("provenance")
    if not isinstance(provenance, dict):
        return False
    return bool(str(provenance.get("source_family") or "").strip()) and bool(
        str(provenance.get("independence_basis") or "").strip()
    )


def required(value: dict[str, Any], key: str) -> str:
    text = str(value.get(key) or "").strip()
    if not text:
        raise SystemExit(f"evaluation governance requires {key}")
    return text
