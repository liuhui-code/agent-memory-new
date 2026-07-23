# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
from typing import Any

from .design_knowledge import routing_hints, select_design_knowledge, unique
from .evidence_context import build_evidence_context
from .performance_scoring import estimate_payload_tokens
from .records import output
from .repository_model import build_repository_model, public_repository_model
from .storage import ensure_initialized, resolve_project


QUALITY_PROMPTS = {
    "performance": [
        "What workload, latency, throughput, or resource response is observable?",
        "Which path repeats expensive work, and at what measured frequency?",
    ],
    "compatibility": [
        "Which callers, persisted formats, or public contracts must remain compatible?",
        "What migration and rollback behavior is required?",
    ],
    "reliability": [
        "What stimulus causes failure, and what recovery response is observable?",
        "Which timeout, retry, fallback, and partial-success semantics are required?",
    ],
    "security": [
        "Which assets, actors, trust boundaries, and abuse cases are in scope?",
        "Where are authorization and audit decisions enforced?",
    ],
    "maintainability": [
        "Which responsibility changes, and which modules should remain unaffected?",
        "What coupling or ownership currently makes the change expensive?",
    ],
    "modifiability": [
        "What future change scenario is credible and how quickly must it be implemented?",
        "Which decisions are stable and which are expected to vary?",
    ],
    "testability": [
        "Which behavior needs an isolated or end-to-end verification path?",
        "What observation distinguishes success from a plausible failure?",
    ],
    "flexibility": [
        "Which behaviors vary independently and who selects them?",
        "What is the lifetime and fallback of the selected behavior?",
    ],
}


def design_context_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    concerns = unique(args.concern)
    anchors = clean_values(args.anchor)
    constraints = clean_values(args.constraint)
    knowledge_query = " ".join([args.query, *constraints])
    evidence = build_evidence_context(
        project,
        args.query,
        explicit_goal="design",
        max_items=max(4, min(args.max_items, 24)),
        explicit_scope="auto",
    )
    model = build_repository_model(project, args.query, anchors)
    hints = routing_hints(knowledge_query, concerns)
    routed_concerns = [item["concern"] for item in hints]
    knowledge, knowledge_audit = select_design_knowledge(
        knowledge_query,
        routed_concerns,
        2 if args.compact else 8,
    )
    if args.compact:
        knowledge = [compact_knowledge_entry(item) for item in knowledge]
        knowledge_audit = {
            key: value for key, value in knowledge_audit.items()
            if key != "catalog_sources"
        }
    payload = build_design_context_payload(
        args.query,
        concerns,
        anchors,
        constraints,
        hints,
        evidence,
        model,
        knowledge,
        knowledge_audit,
        args.compact,
    )
    if args.compact:
        enforce_compact_budget(payload)
    output(payload, args.json)


def enforce_compact_budget(payload: dict[str, Any], token_budget: int = 1500) -> None:
    reductions = (
        lambda: payload["quality_context"].pop("vocabulary_source", None),
        lambda: payload.__setitem__("expansion_hints", payload["expansion_hints"][:1]),
        lambda: payload.__setitem__("design_knowledge", payload["design_knowledge"][:1]),
        lambda: payload["current_repository"].__setitem__(
            "relations", payload["current_repository"]["relations"][:2]
        ),
    )
    for reduce_payload in reductions:
        if estimate_payload_tokens(payload) <= token_budget:
            break
        reduce_payload()


def build_design_context_payload(
    query: str,
    concerns: list[str],
    anchors: list[str],
    constraints: list[str],
    hints: list[dict[str, Any]],
    evidence: dict[str, Any],
    model: dict[str, Any],
    knowledge: list[dict[str, Any]],
    knowledge_audit: dict[str, Any],
    compact: bool,
) -> dict[str, Any]:
    architecture = model["architecture"]
    limits = {"nodes": 3 if compact else 24, "edges": 3 if compact else 36, "memory": 3 if compact else 8}
    corrections = correction_context(evidence, limits["memory"])
    project_memory = project_memory_context(evidence, limits["memory"])
    return {
        "schema_version": "design-context/v1",
        "request": {
            "query": query,
            "explicit_concerns": concerns,
            "explicit_anchors": anchors,
            "explicit_constraints": constraints,
            "query_stage": "agent_directed_expansion" if concerns or anchors else "orientation",
        },
        "authority_order": [
            "current_task_constraint",
            "current_source_or_test",
            "confirmed_project_constraint_or_correction",
            "current_derived_graph",
            "project_semantic_correction",
            "verified_project_experience",
            "general_advisory_knowledge",
            "unverified_historical_observation",
        ],
        "current_repository": repository_context(model, limits, compact),
        "project_context": {
            "task_constraints": [task_constraint(value) for value in constraints],
            "semantic_corrections": corrections,
            "memory_evidence": project_memory,
        },
        "quality_context": {
            "routing_hints": hints,
            "notice": (
                "Routing hints are not design conclusions."
                if compact
                else "Lexical hints only route retrieval; the Agent decides which quality attributes matter."
            ),
            "scenario_questions": quality_questions(hints, compact),
            "vocabulary_source": "https://www.iso.org/standard/78176.html",
        },
        "design_knowledge": knowledge,
        "evidence_gaps": unique_dicts([*evidence["evidence_gaps"], *model["evidence_gaps"]])[:12],
        "expansion_hints": expansion_hints(hints, architecture, evidence, compact),
        "agent_ownership": agent_ownership(compact),
        "audit": audit_payload(compact, knowledge_audit, model, evidence),
    }


def task_constraint(value: str) -> dict[str, Any]:
    return {
        "statement": value,
        "authority": "current_task_constraint",
        "applicability": "hard constraint for this design request",
        "provenance": {"kind": "agent_explicit_input", "ref": "--constraint"},
    }


def repository_context(
    model: dict[str, Any],
    limits: dict[str, int],
    compact: bool,
) -> dict[str, Any]:
    architecture = model["architecture"]
    if not compact:
        return {
            **public_repository_model(model),
            "entry_points": architecture["entry_points"],
            "boundaries": architecture["boundaries"],
            "state_owners": architecture["state_owners"],
            "extension_points": architecture["extension_points"],
            "affected_consumers": architecture["public_consumers"],
            "source_anchors": architecture["nodes"][:limits["nodes"]],
            "relations": architecture["edges"][:limits["edges"]],
            "test_anchors": architecture["test_anchors"],
            "observability_anchors": architecture["observability_anchors"],
            "authority": "current_derived_graph",
            "applicability": "Agent must inspect current source before relying on derived structure.",
        }
    return {
        "schema_version": model["schema_version"],
        "snapshot": compact_snapshot(model["snapshot"]),
        "entry_points": architecture["entry_points"],
        "boundaries": architecture["boundaries"][:4],
        "state_owners": architecture["state_owners"][:4],
        "extension_points": [item.get("id") for item in architecture["extension_points"][:3] if item.get("id")],
        "affected_consumers": [compact_edge(item) for item in architecture["public_consumers"][:1]],
        "source_anchors": [compact_node(item) for item in architecture["nodes"][:limits["nodes"]]],
        "relations": [compact_edge(item) for item in architecture["edges"][:limits["edges"]]],
        "test_anchors": [item.get("id") for item in architecture["test_anchors"][:3] if item.get("id")],
        "observability_anchors": [item.get("id") for item in architecture["observability_anchors"][:3] if item.get("id")],
        "authority": "current_derived_graph",
        "applicability": "Inspect current source before relying on derived structure.",
    }


def compact_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        key: snapshot.get(key)
        for key in ("graph_revision", "freshness", "stale_paths", "truncated", "gap_count")
        if snapshot.get(key) not in (None, "", [])
    }


def compact_node(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item.get(key)
        for key in ("id", "kind", "file_path", "layer", "summary", "span", "evidence_class")
        if item.get(key) not in (None, "", [])
    }


def compact_edge(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item.get(key)
        for key in ("id", "source", "relation", "target", "confidence", "evidence_class")
        if item.get(key) not in (None, "", [])
    }


def compact_knowledge_entry(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "kind": item["kind"],
        "summary": item["summary"],
        "applicability": item["applicability"][0],
        "preconditions": item["preconditions"][0],
        "contraindications": item["contraindications"][0],
        "tradeoffs": item["tradeoffs"][0],
        "question": item["questions"][0],
        "authority": item["authority"],
        "match_reasons": item["match_reasons"][:2],
        "source_ref": item["provenance"][0]["ref"],
    }


def correction_context(evidence: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    metadata = evidence["retrieval_metadata"]
    rows = metadata.get("design_correction_guards") or metadata.get("correction_guards") or []
    result: list[dict[str, Any]] = []
    for row in rows[:limit]:
        verified = row.get("trust_level") in {"verified", "high"}
        result.append({
            "id": row.get("id"),
            "statement": (
                row.get("lesson") or row.get("future_rule") or row.get("summary")
                or row.get("proposed_value") or row.get("patch_reason")
            ),
            "scope": row.get("correction_scope") or row.get("scope") or row.get("anchor_key"),
            "authority": (
                "confirmed_project_constraint_or_correction"
                if verified else "project_semantic_correction"
            ),
            "verification_state": "verified" if verified else "requires_current_source_confirmation",
            "applicability": "guardrail only; confirm against current source and stated scope",
            "provenance": {"kind": "reflection", "ref": row.get("id")},
        })
    return result


def project_memory_context(evidence: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    rows = [
        row
        for tier in ("supporting", "advisory")
        for row in evidence["evidence"].get(tier, [])
        if row.get("source") in {"semantic", "reflection", "episode"}
    ]
    return [
        {
            "evidence_id": row["evidence_id"],
            "kind": row["kind"],
            "title": row["title"],
            "summary": row["summary"],
            "location": row["location"],
            "anchors": row["anchors"],
            "authority": (
                "verified_project_experience"
                if row["authority"] == "verified_experience"
                else "unverified_historical_observation"
            ),
            "applicability": "warning or context only; cannot establish current architecture",
            "provenance": {"kind": row["kind"], "ref": row["record_id"]},
        }
        for row in rows[:limit]
    ]


def quality_questions(hints: list[dict[str, Any]], compact: bool) -> list[dict[str, Any]]:
    return [
        {
            "concern": item["concern"],
            "questions": QUALITY_PROMPTS[item["concern"]][:1] if compact else QUALITY_PROMPTS[item["concern"]],
        }
        for item in hints
        if item["concern"] in QUALITY_PROMPTS
    ]


def expansion_hints(
    hints: list[dict[str, Any]],
    architecture: dict[str, Any],
    evidence: dict[str, Any],
    compact: bool,
) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    inferred = [item["concern"] for item in hints if item["origin"] == "lexical_routing_hint"]
    if inferred:
        values.append({"action": "confirm_or_refine_concerns", "values": inferred})
    if architecture["entry_points"] and not compact:
        values.append({"action": "inspect_source_anchors", "values": architecture["entry_points"][:6]})
    if evidence["evidence_gaps"] and not compact:
        values.append({"action": "close_evidence_gaps", "values": evidence["evidence_gaps"][:4]})
    values.append({"action": "query_again", "usage": "supply Agent-confirmed --concern and --anchor values"})
    return values


def agent_ownership(compact: bool) -> dict[str, Any]:
    if compact:
        return {
            "agent_responsibilities": ["inspect source; reason about alternatives, tradeoffs, selection, plan, and verification"],
            "runtime_limitations": ["context only; no pattern recommendation, candidate ranking, design selection, or plan"],
        }
    return {
        "agent_responsibilities": [
            "inspect current source",
            "decide applicable quality attributes and principles",
            "author and compare materially different candidates",
            "analyze tradeoffs and select the design",
            "create the implementation and verification plan",
        ],
        "runtime_limitations": [
            "does not recommend or select a design pattern",
            "does not generate or rank design candidates",
            "does not create an implementation plan",
            "does not treat graph or memory evidence as current-source proof",
        ],
    }


def audit_payload(
    compact: bool,
    knowledge: dict[str, Any],
    model: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    base = {
        "compact": compact,
        "persisted": False,
        "llm_used": False,
        "decision_free": True,
        "bounded": True,
    }
    if compact:
        return {
            **base,
            "knowledge": {
                key: knowledge[key]
                for key in ("catalog_schema", "returned_count", "truncated")
            },
        }
    return {
        **base,
        "knowledge": knowledge,
        "repository_graph_revision": model["snapshot"]["graph_revision"],
        "retrieval_counts": evidence["audit"]["candidate_counts"],
    }


def clean_values(values: list[str] | None) -> list[str]:
    return list(dict.fromkeys(str(value).strip() for value in (values or []) if str(value).strip()))[:12]


def unique_dicts(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        key = repr(sorted(value.items()))
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result
