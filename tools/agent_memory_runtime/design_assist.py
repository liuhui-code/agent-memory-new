# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import hashlib
from typing import Any

from .design_prepare import build_design_workbench
from .design_protocol import normalize_contract, normalize_intent
from .evidence_context import build_evidence_context
from .models import Project
from .records import output
from .repository_model import build_repository_model
from .storage import ensure_initialized, resolve_project


DEFAULT_ACCEPTANCE = [
    "preserve current behavior outside the stated design goal",
    "give each changed behavior a test or inspectable verification path",
]


def design_assist_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    intent = assist_intent(args)
    evidence = build_evidence_context(
        project,
        intent["goal"],
        explicit_goal="design",
        max_items=args.max_items,
        explicit_scope="auto",
    )
    model = assist_repository_model(project, intent, evidence)
    contract = normalize_contract({
        "schema_version": "design-contract/v2",
        "id": f"{intent['id']}-contract",
        "intent_id": intent["id"],
        "goal": intent["goal"],
        "constraints": intent["constraints"],
        "quality_scenarios": [],
    })
    workbench = build_design_workbench(project.project_id, intent, contract, [], model)
    output(build_assist_payload(args, evidence, workbench), args.json)


def assist_repository_model(
    project: Project,
    intent: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    if intent["scope"]:
        return build_repository_model(project, intent["goal"], intent["scope"])
    return {
        **evidence["repository_model"],
        "architecture": evidence["architecture_slice"],
    }


def assist_intent(args: argparse.Namespace) -> dict[str, Any]:
    digest = hashlib.sha256(args.query.encode("utf-8")).hexdigest()[:12]
    supplied_acceptance = clean_list(args.acceptance)
    return normalize_intent({
        "schema_version": "design-intent/v1",
        "id": f"assist-{digest}",
        "goal": args.query,
        "scope": clean_list(args.scope),
        "exclusions": clean_list(args.exclude),
        "acceptance_criteria": supplied_acceptance or DEFAULT_ACCEPTANCE,
        "constraints": clean_list(args.constraint),
        "open_questions": [],
    }, args.query)


def build_assist_payload(
    args: argparse.Namespace,
    evidence: dict[str, Any],
    workbench: dict[str, Any],
) -> dict[str, Any]:
    brief = workbench["synthesis_brief"]
    guidance = workbench["design_guidance"]
    readiness = workbench["authoring_readiness"]
    return {
        "schema_version": "design-assist/v1",
        "project_id": workbench["project_id"],
        "mode": args.mode,
        "query": args.query,
        "intent": workbench["intent"],
        "current_design": {
            "snapshot": workbench["repository_model"]["snapshot"],
            "baseline_entry_points": brief["baseline_entry_points"],
            "stable_boundaries": brief["stable_boundaries"],
            "extension_points": brief["extension_points"],
            "state_owners": brief["state_owners"],
            "evidence_gaps": brief["evidence_gaps"],
        },
        "design_guidance": guidance,
        "candidate_template": workbench["candidate_template"],
        "authoring_readiness": readiness,
        "evidence_summary": {
            "counts_by_source": evidence["audit"]["counts_by_source"],
            "counts_by_authority": evidence["audit"]["counts_by_authority"],
            "gaps": evidence["evidence_gaps"][:12],
            "recommended_actions": evidence["recommended_actions"],
        },
        "interaction": interaction(args.mode, guidance, readiness),
        "audit": {
            "persisted": False,
            "llm_used": False,
            "bounded": True,
            "natural_language_entry": True,
            "inferred_acceptance_criteria": not bool(clean_list(args.acceptance)),
            "full_workbench_command": "design-prepare",
        },
    }


def interaction(
    mode: str,
    guidance: dict[str, Any],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    decisions = guidance["required_decisions"]
    next_steps = [
        "inspect current source at the baseline entry points",
        "author the smallest viable candidate using the candidate template",
        "explain applicable principles and pattern tradeoffs without forcing a pattern",
    ]
    if mode == "compare":
        next_steps.append("author and compare only materially different candidates")
    elif mode == "design-and-implement":
        next_steps.append("run design-check before implementation and design-verify after tests")
    else:
        next_steps.append("return the recommended design without modifying source")
    return {
        "needs_user_input": readiness["status"] == "needs_input",
        "decision_questions": decisions[:6],
        "next_steps": next_steps,
        "user_visible_output": [
            "recommended design",
            "main reasons and applicable principles",
            "material alternative when one exists",
            "structural changes, risks, and verification plan",
        ],
    }


def clean_list(values: list[str] | None) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in (values or []) if value.strip()))
