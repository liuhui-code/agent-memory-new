# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .system_evolution_check_plan import read_bounded_file
from .system_evolution_contract import (
    SystemEvolutionError, canonical_json, enum_value, identifier, object_fields, references,
    require, text_field, unique_object_keys, validate_versions,
)
from .system_evolution_rounds_contract import validate_round_record


def validate_host_review(value: Any) -> None:
    fields = {"enabled", "authorization_ref", "max_review_attempts", "automatic_retries", "max_report_chars"}
    object_fields(value, fields, fields, "host_review")
    require(type(value["enabled"]) is bool, "Host review enabled must be boolean.")
    text_field(value["authorization_ref"], "authorization_ref", 240)
    require(type(value["max_review_attempts"]) is int and value["max_review_attempts"] == 1
            and type(value["automatic_retries"]) is int and value["automatic_retries"] == 0,
            "Host handoff permits one attempt and no automatic retries.")
    require(type(value["max_report_chars"]) is int and 1 <= value["max_report_chars"] <= 4000,
            "Host report limit must be 1–4000 characters.")


def validate_handoff(value: Any) -> None:
    require(isinstance(value, dict), "Handoff request must be an object.")
    action = value.get("action")
    enum_value(action, {"inspect", "claim", "complete", "fail"}, "handoff action")
    common = {"schema_version", "action", "round_key"}
    extra = {"inspect": set(),
             "claim": {"expected_revision", "observations_file", "task_ref", "task_state", "activity",
                       "review_enabled", "user_cancelled", "budget_available", "version_refs"},
             "complete": {"claim_digest", "assessment"},
             "fail": {"claim_digest", "reason", "note", "evidence_refs", "additional_cost"}}[action]
    object_fields(value, common | extra, common | extra, "handoff request")
    require(value["schema_version"] == "system-evolution-handoff-request/v1", "Unsupported handoff request.")
    identifier(value["round_key"], "round_key")
    if action == "claim":
        require(type(value["expected_revision"]) is int and 1 <= value["expected_revision"] <= 22,
                "Invalid expected round revision.")
        text_field(value["observations_file"], "observations_file", 500)
        task = value["task_ref"]
        object_fields(task, {"origin", "key"}, {"origin", "key"}, "task_ref")
        enum_value(task["origin"], {"host", "client_local"}, "task origin")
        identifier(task["key"], "task_ref.key")
        enum_value(value["task_state"], {"in_progress", "completed", "failed", "blocked", "cancelled"}, "task state")
        enum_value(value["activity"], {"task", "round_follow_up", "system_review", "system_evolution"}, "activity")
        for name in ("review_enabled", "user_cancelled", "budget_available"):
            require(type(value[name]) is bool, "Handoff switches must be boolean.")
        validate_versions(value["version_refs"])
    elif action != "inspect":
        require(isinstance(value["claim_digest"], str) and bool(re.fullmatch(r"[0-9a-f]{64}", value["claim_digest"])),
                "Declare the immutable claim receipt digest.")
        if action == "complete":
            validate_round_record(value["assessment"])
            require(value["assessment"]["kind"] == "assessment" and value["assessment"]["round_key"] == value["round_key"],
                    "Complete must contain this round's assessment.")
        else:
            enum_value(value["reason"], {"host_interrupted", "budget_exhausted", "input_drift", "review_failed", "user_stopped", "unknown"}, "failure reason")
            text_field(value["note"], "failure note", 600)
            references(value["evidence_refs"], "evidence_refs", set())
            cost = value["additional_cost"]
            object_fields(cost, {"tokens", "elapsed_ms"}, {"tokens", "elapsed_ms"}, "additional_cost")
            require(all(amount is None or (type(amount) is int and 0 <= amount <= 2**53 - 1) for amount in cost.values()),
                    "Invalid declared review cost.")
    require(len(canonical_json(value).encode("utf-8")) <= 32768, "Handoff request exceeds 32 KiB.")


def load_handoff(path: str) -> dict[str, Any]:
    try:
        value = json.loads(read_bounded_file(Path(path).expanduser(), 32768).decode("utf-8"), object_pairs_hook=unique_object_keys)
        validate_handoff(value)
        return value
    except (OSError, ValueError, RecursionError) as error:
        if isinstance(error, SystemEvolutionError):
            raise
        raise SystemEvolutionError("invalid_handoff_request", "Cannot read a bounded host handoff request.") from error
