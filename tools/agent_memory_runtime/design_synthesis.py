# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


def build_synthesis_brief(
    model: dict[str, Any],
    intent: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    architecture = model["architecture"]
    return {
        "schema_version": "design-synthesis-brief/v1",
        "intent_id": intent["id"],
        "goal": intent["goal"],
        "baseline_revision": model["snapshot"]["graph_revision"],
        "baseline_entry_points": model["baseline_entry_points"][:12],
        "stable_boundaries": architecture["boundaries"][:12],
        "extension_points": architecture["extension_points"][:12],
        "state_owners": architecture["state_owners"][:12],
        "constraints": contract["constraints"],
        "scope": intent["scope"],
        "exclusions": intent["exclusions"],
        "acceptance_criteria": intent["acceptance_criteria"],
        "open_questions": intent["open_questions"],
        "quality_scenarios": [
            {key: scenario[key] for key in ("id", "attribute", "priority", "measure")}
            for scenario in contract["quality_scenarios"]
        ],
        "evidence_gaps": model["evidence_gaps"][:12],
        "candidate_policy": {
            "smallest_viable_first": True,
            "alternatives_only_for_material_tradeoffs": True,
            "required_difference": "structural or behavioral",
            "max_candidates": 3,
        },
        "audit": {"llm_used": False, "persisted": False, "bounded": True},
    }


def build_decision(recommended: str, candidates: list[dict[str, Any]], reasons: list[str], tradeoffs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "design-decision/v1",
        "selected_candidate": recommended,
        "rejected_candidates": sorted(item["candidate_id"] for item in candidates if item["candidate_id"] != recommended),
        "decision_reasons": reasons,
        "tradeoffs": tradeoffs,
        "persisted": False,
    }
