# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .models import Project
from .query import limited_context
from .records import output
from .storage import ensure_initialized, resolve_project
from .text import tokenize, unique_list


GROUND_THRESHOLD = 0.45
WEAK_THRESHOLD = 0.25


def eval_evidence_attribution_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    cases = load_cases(Path(args.cases))
    data = evaluate_evidence_attribution(project, cases)
    output(data, args.json)


def load_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"eval cases file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid eval cases JSON: {exc}") from exc
    if not isinstance(data, list):
        raise SystemExit("eval cases JSON must be a list")
    return [item for item in data if isinstance(item, dict)]


def evaluate_evidence_attribution(project: Project, cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_results = [evaluate_case(project, case) for case in cases]
    total_claims = sum(result["claim_count"] for result in case_results)
    grounded_claims = sum(result["grounded_claims"] for result in case_results)
    unsupported_claims = sum(result["unsupported_claims"] for result in case_results)
    failed_cases = [result for result in case_results if result["quality_gate"] == "fail"]
    return {
        "project_id": project.project_id,
        "quality_gate": "pass" if not failed_cases else "fail",
        "summary": {
            "case_count": len(case_results),
            "claim_count": total_claims,
            "grounded_claims": grounded_claims,
            "grounded_claim_rate": ratio(grounded_claims, total_claims),
            "unsupported_claims": unsupported_claims,
            "unsupported_claim_rate": ratio(unsupported_claims, total_claims),
        },
        "cases": case_results,
        "thresholds": {
            "grounded": GROUND_THRESHOLD,
            "weak": WEAK_THRESHOLD,
        },
    }


def evaluate_case(project: Project, case: dict[str, Any]) -> dict[str, Any]:
    query = str(case.get("query") or "").strip()
    claims = [str(claim) for claim in case.get("claims") or [] if str(claim).strip()]
    if not query:
        raise SystemExit("eval case query is required")
    context = limited_context(project, query)
    claim_results = [claim_support_score(claim, context) for claim in claims]
    grounded = sum(1 for item in claim_results if item["support_band"] == "grounded")
    unsupported = sum(1 for item in claim_results if item["support_band"] == "unsupported")
    min_grounded_rate = float(case.get("min_grounded_rate") if case.get("min_grounded_rate") is not None else 0.8)
    max_unsupported = int(case.get("max_unsupported_claims") if case.get("max_unsupported_claims") is not None else 0)
    quality_gate = "pass" if ratio(grounded, len(claims)) >= min_grounded_rate and unsupported <= max_unsupported else "fail"
    return {
        "name": case.get("name") or query,
        "query": query,
        "quality_gate": quality_gate,
        "claim_count": len(claims),
        "grounded_claims": grounded,
        "unsupported_claims": unsupported,
        "grounded_claim_rate": ratio(grounded, len(claims)),
        "claims": claim_results,
    }


def claim_support_score(claim: str, context: dict[str, Any]) -> dict[str, Any]:
    claim_terms = {token for token in tokenize(claim) if len(token) > 1}
    evidence_items = flatten_context_evidence(context)
    best_score = 0.0
    best_evidence: list[dict[str, Any]] = []
    for evidence in evidence_items:
        evidence_terms = {token for token in tokenize(evidence["text"]) if len(token) > 1}
        if not claim_terms or not evidence_terms:
            continue
        overlap = len(claim_terms & evidence_terms) / max(1, len(claim_terms))
        bonus = exact_anchor_bonus(claim, evidence["text"])
        score = min(1.0, overlap + bonus)
        if score > best_score:
            best_score = score
            best_evidence = [
                {
                    "type": evidence["type"],
                    "id": evidence.get("id"),
                    "score": round(score, 3),
                    "matched_terms": sorted(claim_terms & evidence_terms)[:10],
                    "snippet": evidence["text"][:240],
                }
            ]
    return {
        "claim": claim,
        "support_score": round(best_score, 3),
        "support_band": support_band(best_score),
        "supporting_evidence": best_evidence,
    }


def flatten_context_evidence(context: dict[str, Any]) -> list[dict[str, Any]]:
    fields = {
        "semantic_facts": ("fact", "source", "scope", "evidence"),
        "reflections": ("task", "summary", "lesson", "future_rule", "evidence", "verification_method", "source_cases"),
        "episodes": ("task", "summary", "outcome", "files_touched"),
        "wiki_matches": ("file_path", "summary", "business_summary", "business_terms"),
        "code_log_matches": ("file_path", "function", "logger", "message_template", "business_event", "likely_causes"),
        "edge_matches": ("source_label", "target_label", "relation", "evidence"),
        "incident_trace_matches": ("symptom", "summary", "candidate_chain", "resolution"),
    }
    evidence: list[dict[str, Any]] = []
    for key, names in fields.items():
        values = context.get(key)
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            text = " ".join(str(item.get(name) or "") for name in names)
            if text.strip():
                evidence.append({"type": key, "id": item.get("id"), "text": text})
    return evidence


def exact_anchor_bonus(claim: str, evidence: str) -> float:
    lowered_claim = claim.lower()
    lowered_evidence = evidence.lower()
    bonus = 0.0
    for anchor in unique_list(re.findall(r"[A-Za-z0-9_./:-]{4,}", claim)):
        if anchor.lower() in lowered_evidence:
            bonus += 0.08
    if "error" in lowered_claim and "error" in lowered_evidence:
        bonus += 0.05
    return min(0.25, bonus)


def support_band(score: float) -> str:
    if score >= GROUND_THRESHOLD:
        return "grounded"
    if score >= WEAK_THRESHOLD:
        return "weak"
    return "unsupported"


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 3)
