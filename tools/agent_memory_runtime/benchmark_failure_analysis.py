# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import Counter
from typing import Any


ANALYSIS_SCHEMA = "agent-benchmark-failure-analysis/v1"
METHOD_REFERENCES = {
    "trec": "https://trec.nist.gov/howto.html",
    "swe_bench": "https://arxiv.org/abs/2310.06770",
    "beir": "https://arxiv.org/abs/2104.08663",
    "graphrag_local": "https://microsoft.github.io/graphrag/query/overview/",
    "context_boundary": "docs/context-provider-boundary.md",
    "agent_benchmark": "docs/agent-benchmark.md",
}

FAILURE_POLICIES = {
    "candidate_generation": {
        "owning_layer": "index_adapter_or_candidate_recall",
        "method_reference_ids": ["trec", "beir"],
        "allowed_repair": "Improve extraction, lexical recall, or bounded candidate generation.",
        "prohibited_shortcut": "Do not boost an absent candidate in final ranking.",
    },
    "ranking_precision": {
        "owning_layer": "ranking_and_evidence_fusion",
        "method_reference_ids": ["trec", "beir", "graphrag_local"],
        "allowed_repair": "Improve field evidence, reranking, diversity, or bounded local expansion.",
        "prohibited_shortcut": "Do not use unbounded graph expansion or relax the Oracle.",
    },
    "passage_selection": {
        "owning_layer": "query_focused_source_window",
        "method_reference_ids": ["trec", "beir"],
        "allowed_repair": "Select evidence-backed symbol or line windows for the query.",
        "prohibited_shortcut": "Do not return a larger arbitrary file prefix.",
    },
    "graph_structure": {
        "owning_layer": "semantic_graph_adapter",
        "method_reference_ids": ["graphrag_local", "context_boundary"],
        "allowed_repair": "Add evidence-backed language-neutral relations or bounded traversal.",
        "prohibited_shortcut": "Do not turn text similarity into a call or causal edge.",
    },
    "experience_governance": {
        "owning_layer": "experience_scope_conflict_and_guard_lanes",
        "method_reference_ids": ["beir", "context_boundary"],
        "allowed_repair": "Improve scope, freshness, conflict, trust, or correction-guard handling.",
        "prohibited_shortcut": "Do not prefer the newest or most similar experience blindly.",
    },
    "abstention_calibration": {
        "owning_layer": "evidence_gap_and_calibration_contract",
        "method_reference_ids": ["beir", "context_boundary"],
        "allowed_repair": "Expose missing evidence and keep weak lanes empty.",
        "prohibited_shortcut": "Do not fill an empty lane with weakly related evidence.",
    },
    "context_compactness": {
        "owning_layer": "compact_context_projection",
        "method_reference_ids": ["agent_benchmark"],
        "allowed_repair": "Remove redundant evidence while preserving required anchors.",
        "prohibited_shortcut": "Do not drop required evidence merely to pass the budget.",
    },
    "agent_protocol": {
        "owning_layer": "agent_skill_and_runner_protocol",
        "method_reference_ids": ["swe_bench", "agent_benchmark"],
        "allowed_repair": "Improve Agent query iteration, evidence use, or stop conditions.",
        "prohibited_shortcut": "Do not modify retrieval when the required context is present.",
    },
    "agent_efficiency": {
        "owning_layer": "agent_context_consumption_and_cost",
        "method_reference_ids": ["swe_bench", "agent_benchmark"],
        "allowed_repair": "Reduce repeated searches, reads, context, or tool failures.",
        "prohibited_shortcut": "Do not relax cost limits after observing the result.",
    },
    "evaluation_integrity": {
        "owning_layer": "evaluation_protocol",
        "method_reference_ids": ["trec", "swe_bench"],
        "allowed_repair": "Repair missing pairs, runner metadata, or evaluation coverage.",
        "prohibited_shortcut": "Do not claim capability from incomplete observations.",
    },
}


def analyze_context_failures(result: dict[str, Any]) -> dict[str, Any]:
    failures = []
    for case in result.get("cases") or []:
        if not isinstance(case, dict):
            continue
        for check, passed in (case.get("checks") or {}).items():
            if passed is False:
                failures.append(failure_record(
                    str(case.get("case_id") or "unknown"),
                    str(check),
                    context_failure_class(str(check)),
                    "context",
                ))
    return analysis_result(failures)


def analyze_agent_failures(result: dict[str, Any]) -> dict[str, Any]:
    failures = []
    for check, passed in (result.get("gate_checks") or {}).items():
        if passed is False:
            failures.append(failure_record(
                "aggregate", str(check), agent_quality_class(str(check)), "quality"
            ))
    for check, passed in (result.get("efficiency_gate_checks") or {}).items():
        if passed is False:
            failures.append(failure_record(
                "aggregate", str(check), "agent_efficiency", "efficiency"
            ))
    analysis = analysis_result(failures)
    analysis.update({
        "quality_failure_count": sum(item["gate"] == "quality" for item in failures),
        "efficiency_failure_count": sum(item["gate"] == "efficiency" for item in failures),
    })
    return analysis


def analysis_result(failures: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(item["failure_class"] for item in failures)
    primary = counts.most_common(1)[0][0] if counts else None
    return {
        "schema_version": ANALYSIS_SCHEMA,
        "status": "repair_required" if failures else "clear",
        "failure_count": len(failures),
        "primary_failure_class": primary,
        "failure_class_counts": dict(sorted(counts.items())),
        "failures": failures,
        "method_references": METHOD_REFERENCES,
        "repair_policy": (
            "Reproduce the primary class in independent development cases; "
            "never tune a sealed holdout."
        ),
    }


def failure_record(case_id: str, check: str, failure_class: str, gate: str) -> dict[str, Any]:
    policy = FAILURE_POLICIES[failure_class]
    return {
        "case_id": case_id,
        "failed_check": check,
        "gate": gate,
        "failure_class": failure_class,
        **policy,
        "next_validation": (
            "Add an independent development reproduction, run focused regression, "
            "then evaluate a new sealed holdout."
        ),
    }


def context_failure_class(check: str) -> str:
    if "source_span" in check or "source_excerpt" in check:
        return "passage_selection"
    if "experience" in check:
        return "experience_governance"
    if "path" in check or "relation" in check:
        return "graph_structure"
    if "abstention" in check or "evidence_gap" in check:
        return "abstention_calibration"
    if "budget" in check or "compact" in check:
        return "context_compactness"
    if "top_k" in check or "precision" in check or "forbidden" in check:
        return "ranking_precision"
    if "anchor" in check or "log" in check:
        return "candidate_generation"
    return "evaluation_integrity"


def agent_quality_class(check: str) -> str:
    integrity_terms = ("minimum_cases", "complete_pairs", "configuration", "budget")
    return (
        "evaluation_integrity"
        if any(term in check for term in integrity_terms)
        else "agent_protocol"
    )
