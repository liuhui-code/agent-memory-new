# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import Counter
from typing import Any

from .semantic_models import SemanticBatch


QUALIFICATION_SCHEMA = "semantic-provider-qualification/v1"
RELATION_FAMILIES = {
    "calls": {"calls"},
    "inheritance": {"extends", "implements", "overrides"},
    "state_flow": {"reads_state", "writes_state"},
    "callbacks": {"registers_callback"},
    "async_flow": {"awaits"},
}


def qualify_exact_batch(exact: SemanticBatch, baseline: SemanticBatch) -> dict[str, Any]:
    baseline_files = {item.file_path for item in baseline.entities}
    exact_files = {item.file_path for item in exact.entities}
    missing_files = sorted(baseline_files - exact_files)
    relation_checks = _relation_family_checks(exact, baseline)
    lost_families = sorted(
        name for name, check in relation_checks.items() if check["status"] == "missing"
    )
    covered = len(baseline_files - set(missing_files))
    coverage = covered / len(baseline_files) if baseline_files else 1.0
    status = "rejected" if missing_files or lost_families else "qualified"
    return {
        "schema_version": QUALIFICATION_SCHEMA,
        "status": status,
        "policy": "definition_file_coverage_and_relation_family_presence",
        "entity_file_coverage": round(coverage, 4),
        "baseline_entity_files": len(baseline_files),
        "exact_entity_files": len(exact_files & baseline_files),
        "missing_entity_files": missing_files[:20],
        "relation_family_checks": relation_checks,
        "lost_relation_families": lost_families,
    }


def qualification_diagnostic(profile: dict[str, Any]) -> str:
    reasons: list[str] = []
    missing = profile.get("missing_entity_files") or []
    lost = profile.get("lost_relation_families") or []
    if missing:
        reasons.append("missing definition-bearing files: " + ", ".join(missing))
    if lost:
        reasons.append("missing observed relation families: " + ", ".join(lost))
    return "; ".join(reasons) or "external provider failed semantic qualification"


def _relation_family_checks(
    exact: SemanticBatch,
    baseline: SemanticBatch,
) -> dict[str, dict[str, Any]]:
    exact_relations = Counter(item.relation for item in exact.relations)
    baseline_relations = Counter(item.relation for item in baseline.relations)
    checks: dict[str, dict[str, Any]] = {}
    for family, kinds in RELATION_FAMILIES.items():
        baseline_count = sum(baseline_relations[kind] for kind in kinds)
        exact_count = sum(exact_relations[kind] for kind in kinds)
        if not baseline_count:
            continue
        checks[family] = {
            "status": "present" if exact_count else "missing",
            "baseline_count": baseline_count,
            "exact_count": exact_count,
            "declared": family in exact.capabilities,
        }
    return checks
