# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any

from .system_evolution_contract import enum_value, identifier, items, object_fields, references, require, text_field
from .system_evolution_handoff_contract import validate_host_review


def validate_outcome_plan(value: dict[str, Any], proposal_id: int, revision: int) -> None:
    require(isinstance(value, dict), "Outcome plan must be an object.")
    fields = {"schema_version", "proposal_id", "prepared_state_revision", "round_key", "hypothesis",
              "expected_result", "guardrails", "window"}
    if value.get("schema_version") == "system-change-outcome-plan/v2":
        fields = fields | {"host_review"}
    object_fields(value, fields, fields, "outcome plan")
    require(value["schema_version"] in {"system-change-outcome-plan/v1", "system-change-outcome-plan/v2"}, "Unsupported outcome plan.")
    if "host_review" in value:
        validate_host_review(value["host_review"])
    require(type(value["proposal_id"]) is int and value["proposal_id"] == proposal_id
            and type(value["prepared_state_revision"]) is int and value["prepared_state_revision"] == revision,
            "Outcome plan binds a different prepared proposal.", "outcome_binding_mismatch")
    identifier(value["round_key"], "round_key")
    text_field(value["hypothesis"], "hypothesis", 600)
    text_field(value["expected_result"], "expected_result", 600)
    for guardrail in items(value["guardrails"], "guardrails", 5):
        text_field(guardrail, "guardrail", 300)
    window = value["window"]
    fields = {"key", "source_ref", "target_presented", "allowed_exclusion_reasons"}
    object_fields(window, fields, fields, "outcome window")
    identifier(window["key"], "window.key")
    text_field(window["source_ref"], "source_ref", 240)
    require(type(window["target_presented"]) is int and 1 <= window["target_presented"] <= 20,
            "Outcome windows permit one to twenty presented tasks.")
    reasons = items(window["allowed_exclusion_reasons"], "allowed_exclusion_reasons", 5)
    for reason in reasons:
        identifier(reason, "exclusion reason")
    require(len(set(reasons)) == len(reasons), "Duplicate exclusion reasons.")


def validate_observations(value: dict[str, Any], plan: dict[str, Any], project_id: str,
                          plan_digest: str, application_key: str) -> dict[str, Any]:
    fields = {"schema_version", "project_id", "proposal_id", "round_key", "plan_digest", "application_key", "tasks"}
    object_fields(value, fields, fields, "outcome observations")
    require(value["schema_version"] == "system-change-outcome-observations/v1", "Unsupported observations.")
    require(value["project_id"] == project_id and type(value["proposal_id"]) is int
            and value["proposal_id"] == plan["proposal_id"] and value["round_key"] == plan["round_key"]
            and value["plan_digest"] == plan_digest and value["application_key"] == application_key,
            "Observations bind a different project, proposal, round, plan or application.", "outcome_binding_mismatch")
    tasks = items(value["tasks"], "tasks", plan["window"]["target_presented"])
    identities: set[tuple[str, str]] = set()
    refs: set[str] = set()
    counts = {name: 0 for name in ("presented", "included", "excluded", "pass", "fail", "partial", "unknown")}
    costs = {name: {"observed_total": 0, "missing_tasks": 0} for name in ("tokens", "elapsed_ms")}
    for sequence, task in enumerate(tasks, 1):
        fields = {"sequence", "task_ref", "state", "exclusion_reason", "outcome", "verification", "evidence_refs", "cost"}
        object_fields(task, fields, fields, "observed task")
        require(type(task["sequence"]) is int and task["sequence"] == sequence,
                "Presented task sequence must be contiguous from one.")
        identity = task["task_ref"]
        object_fields(identity, {"key", "origin"}, {"key", "origin"}, "task_ref")
        identifier(identity["key"], "task_ref.key")
        enum_value(identity["origin"], {"host", "client_local"}, "task_ref.origin")
        pair = (identity["origin"], identity["key"])
        require(pair not in identities, "Repeated task identity cannot form another observation.")
        identities.add(pair)
        enum_value(task["state"], {"included", "excluded"}, "observation state")
        enum_value(task["outcome"], {"pass", "fail", "partial", "unknown"}, "task outcome")
        enum_value(task["verification"], {"test", "build", "source_review", "user_confirmation", "unavailable"},
                   "verification source")
        references(task["evidence_refs"], "task evidence_refs", refs)
        object_fields(task["cost"], {"tokens", "elapsed_ms"}, {"tokens", "elapsed_ms"}, "task cost")
        for name, amount in task["cost"].items():
            require(amount is None or (type(amount) is int and 0 <= amount <= 2**53 - 1), "Invalid declared cost.")
        if task["state"] == "excluded":
            require(task["exclusion_reason"] in plan["window"]["allowed_exclusion_reasons"]
                    and task["outcome"] == "unknown" and task["verification"] == "unavailable"
                    and not task["evidence_refs"] and all(amount is None for amount in task["cost"].values()),
                    "Excluded tasks require a declared reason and no invented outcome/cost.")
        else:
            require(task["exclusion_reason"] is None, "Included tasks cannot have an exclusion reason.")
            require(task["outcome"] == "unknown" or
                    (task["verification"] != "unavailable" and bool(task["evidence_refs"])),
                    "Known task outcomes require a verification source and evidence references.")
            counts[task["outcome"]] += 1
            for name, amount in task["cost"].items():
                costs[name]["missing_tasks"] += amount is None
                if amount is not None:
                    costs[name]["observed_total"] += amount
        counts[task["state"]] += 1
        counts["presented"] += 1
    require(len(refs) <= 40, "Observations permit at most forty distinct evidence references.")
    return {"tasks": tasks, "counts": counts, "declared_task_costs": costs,
            "window_state": "declared_complete" if len(tasks) == plan["window"]["target_presented"] else "partial",
            "provenance": "caller_declared_unverified", "external_continuity_authenticated": False,
            "incremental_meta_cost_measured": False}
