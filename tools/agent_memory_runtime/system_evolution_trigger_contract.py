# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .system_evolution_contract import (
    SystemEvolutionError, canonical_json, enum_value, identifier, items, object_fields,
    references, require, unique_object_keys, validate_versions,
)


SIGNALS = ("memory_error", "user_correction", "evidence_conflict", "repeated_gap")
FIELDS = {"schema_version", "task_ref", "task_state", "task_outcome", "memory_use", "memory_requested",
          "manual_request", "review_enabled", "user_cancelled", "budget_available", "activity",
          "signals", "version_refs", "query_refs"}


def validate_trigger(value: Any) -> str:
    object_fields(value, FIELDS, FIELDS, "trigger request")
    require(value["schema_version"] == "system-meta-trigger/v1", "Unsupported trigger request format.")
    for key in ("memory_requested", "manual_request", "review_enabled", "user_cancelled", "budget_available"):
        require(type(value[key]) is bool, "Trigger switches must be booleans.")
    enum_value(value["task_state"], {"in_progress", "completed", "failed", "blocked", "cancelled"}, "task state")
    enum_value(value["task_outcome"], {"success", "failure", "partial", "unknown"}, "task outcome")
    enum_value(value["memory_use"], {"used", "not_used", "unknown"}, "Memory use")
    enum_value(value["activity"], {"task", "system_review", "system_evolution"}, "activity")
    if value["task_ref"] is not None:
        task = value["task_ref"]
        object_fields(task, {"key", "origin"}, {"key", "origin"}, "task_ref")
        identifier(task["key"], "task_ref.key")
        enum_value(task["origin"], {"host", "client_local"}, "task origin")
    validate_versions(value["version_refs"])
    refs: set[str] = set()
    references(value["query_refs"], "query_refs", refs)
    kinds: set[str] = set()
    for signal in items(value["signals"], "signals", 4):
        require(isinstance(signal, dict), "Signal must be an object.")
        enum_value(signal.get("kind"), set(SIGNALS), "signal kind")
        fields = {"kind", "refs"} | ({"gap_key", "round_refs"} if signal["kind"] == "repeated_gap" else set())
        object_fields(signal, fields, fields, "signal")
        require(signal["kind"] not in kinds, "Duplicate signal kind.")
        kinds.add(signal["kind"])
        references(signal["refs"], "signal refs", refs)
        require(bool(signal["refs"]), "A concrete signal needs an observation reference.")
        if signal["kind"] == "repeated_gap":
            identifier(signal["gap_key"], "gap_key")
            references(signal["round_refs"], "round_refs", refs)
            require(len(set(signal["round_refs"])) == len(signal["round_refs"]) >= 2,
                    "Repeated-gap signals need at least two distinct observed round references.")
    require(len(refs) <= 8, "Trigger request exceeds eight distinct references.")
    encoded = canonical_json(value)
    require(len(encoded) <= 4000, "Trigger request exceeds 4,000 canonical characters.")
    return encoded


def load_trigger(payload: str | None, payload_file: str | None) -> dict[str, Any]:
    try:
        require(bool(payload) != bool(payload_file), "Supply exactly one trigger payload source.")
        supplied = payload or ""
        if payload_file:
            with Path(payload_file).expanduser().open("rb") as handle:
                raw = handle.read(32769)
            require(len(raw) <= 32768, "Trigger file exceeds the bounded read.")
            supplied = raw.decode("utf-8")
        require(len(supplied) <= 4000, "Trigger input exceeds 4,000 characters.")
        value = json.loads(supplied, object_pairs_hook=unique_object_keys)
        validate_trigger(value)
        return value
    except (OSError, ValueError, RuntimeError, RecursionError) as error:
        raise SystemEvolutionError("invalid_trigger", "Invalid bounded system-trigger request; inspect the trigger contract.") from error


def trigger_choice(value: dict[str, Any]) -> tuple[str | None, str]:
    if value["user_cancelled"]:
        return None, "user_stopped"
    if not value["review_enabled"]:
        return None, "review_disabled"
    if not value["budget_available"]:
        return None, "review_budget_unavailable"
    if value["manual_request"]:
        return "manual", "manual_request"
    if value["activity"] != "task":
        return None, "recursive_review_suppressed"
    if value["task_state"] not in {"completed", "failed", "blocked"}:
        return None, "task_not_closed"
    if value["memory_use"] != "used" and not value["memory_requested"]:
        return None, "memory_not_observed_or_requested"
    if value["task_ref"] is None:
        return None, "task_identity_unavailable"
    kinds = {signal["kind"] for signal in value["signals"]}
    for kind in SIGNALS:
        if kind in kinds:
            return kind, "concrete_task_end_signal"
    return None, "no_concrete_signal"
