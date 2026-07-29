# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .context_capability_quality import span_is_observed


FUNNEL_SCHEMA = "agent-context-evidence-funnel/v1"


def assess_evidence_funnel(
    expected_files: set[str], requirements: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any]:
    """Locate the first retrieval stage that loses an Oracle target for evaluation."""
    callable_targets = records(requirements.get("hierarchical_callable_spans"))
    if not callable_targets:
        callable_targets = records(requirements.get("required_source_spans"))
    range_targets = records(requirements.get("hierarchical_range_spans"))
    if not range_targets:
        range_targets = records(requirements.get("required_source_spans"))
    candidate_files = string_set(observation.get("candidate_anchor_paths"))
    localizer_files = string_set(observation.get("hierarchical_file_paths"))
    callables = records(observation.get("hierarchical_callable_refs"))
    ranges = records(observation.get("hierarchical_source_ranges"))
    primary = primary_file(observation.get("callable_evidence"))
    compact_primary = string_set(observation.get("primary_anchor_paths"))
    compact_anchors = string_set(observation.get("anchor_paths"))
    stages = {
        "candidate_file": contains_all(expected_files, candidate_files),
        "localizer_file": contains_all(expected_files, localizer_files),
        "callable": spans_present(callable_targets, callables),
        "source_range": spans_present(range_targets, ranges),
        "evidence_primary": primary in expected_files if expected_files else None,
        "compact_primary": contains_all(expected_files, compact_primary),
        "compact_anchor": contains_all(expected_files, compact_anchors),
    }
    return {
        "schema_version": FUNNEL_SCHEMA,
        "stages": stages,
        "first_loss": first_loss(stages),
        "candidate_file_count": len(candidate_files),
        "localizer_file_count": len(localizer_files),
        "callable_count": len(callables),
        "range_count": len(ranges),
        "evidence_certainty": evidence_certainty(observation.get("callable_evidence")),
        "primary_file_path": primary,
    }


def evidence_funnel_profile(scored: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate loss attribution only; it never changes a context gate."""
    values = [item.get("evidence_funnel", {}) for item in scored]
    stages = (
        "candidate_file", "localizer_file", "callable", "source_range",
        "evidence_primary", "compact_primary", "compact_anchor",
    )
    first_losses = [str(item.get("first_loss")) for item in values if item.get("first_loss")]
    return {
        "status": "informational",
        "evaluated_cases": len(values),
        "first_loss_counts": {name: first_losses.count(name) for name in sorted(set(first_losses))},
        "stage_pass_rates": {
            name: stage_pass_rate(values, name) for name in stages
        },
    }


def contains_all(expected: set[str], observed: set[str]) -> bool | None:
    return expected <= observed if expected else None


def spans_present(expected: list[dict[str, Any]], observed: list[dict[str, Any]]) -> bool | None:
    if not expected:
        return None
    return all(span_is_observed(item, observed) for item in expected)


def first_loss(stages: dict[str, bool | None]) -> str | None:
    return next((name for name, value in stages.items() if value is False), None)


def primary_file(value: Any) -> str | None:
    if not isinstance(value, dict) or not isinstance(value.get("primary"), dict):
        return None
    return str(value["primary"].get("file_path") or "").strip() or None


def evidence_certainty(value: Any) -> str:
    return str(value.get("certainty") or "unavailable") if isinstance(value, dict) else "unavailable"


def stage_pass_rate(values: list[dict[str, Any]], stage: str) -> float | None:
    measured = [item["stages"].get(stage) for item in values if isinstance(item.get("stages"), dict)]
    booleans = [value for value in measured if isinstance(value, bool)]
    return round(sum(booleans) / len(booleans), 4) if booleans else None


def records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def string_set(value: Any) -> set[str]:
    return {str(item) for item in value if str(item)} if isinstance(value, list) else set()
