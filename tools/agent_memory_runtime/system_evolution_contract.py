# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


REPORT_FORMAT = "system-meta-review/v1"
MAX_REPORT_CHARS = 4000
MAX_INPUT_BYTES = 32768
COMPONENTS = {"memory", "rules", "query", "learn", "reflect", "data_model", "evaluator", "delivery"}
EDITABLE_STATES = {"proposed", "needs_evidence", "prepared", "rejected", "superseded"}
PROTECTED_STATES = {"checked", "applied", "monitoring", "closed", "rolled_back"}
VERSION_FIELDS = {
    "runtime_revision", "runtime_digest", "skill_revision", "skill_digest", "protocol_version",
    "source_revision", "source_digest", "archive_project_id", "index_generation",
}
REPORT_FIELDS = {
    "report_format", "task_ref", "review_revision", "trigger", "task_state", "task_outcome",
    "memory_use", "version_refs", "query_refs", "observations", "checks", "model_opinions",
    "target_components", "change_proposals", "missing_evidence", "omitted_counts",
    "additional_cost", "review_status", "advisory_only",
}


class SystemEvolutionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def require(condition: bool, message: str, code: str = "invalid_report") -> None:
    if not condition:
        raise SystemEvolutionError(code, message)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def identifier(value: Any, name: str) -> str:
    require(isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", value)),
            f"{name} must be an opaque ASCII identifier of 1-160 characters.")
    return value


def text_field(value: Any, name: str, limit: int = 500, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= limit,
            f"{name} must be a nonempty string of at most {limit} characters.")
    require(not any(ord(char) < 32 and char not in "\n\t" for char in value),
            f"{name} contains unsupported control characters.")
    require(not any(0xD800 <= ord(char) <= 0xDFFF for char in value), f"{name} contains invalid Unicode.")


def enum_value(value: Any, allowed: set[str], name: str) -> None:
    require(isinstance(value, str) and value in allowed, f"Invalid {name}.")


def object_fields(value: Any, allowed: set[str], required: set[str], name: str) -> None:
    require(isinstance(value, dict), f"{name} must be an object.")
    require(required <= value.keys() and value.keys() <= allowed, f"{name} has missing or unsupported fields.")


def items(value: Any, name: str, limit: int) -> list[Any]:
    require(isinstance(value, list) and len(value) <= limit, f"{name} must be a list of at most {limit} items.")
    return value


def references(value: Any, name: str, collected: set[str]) -> None:
    for ref in items(value, name, 8):
        text_field(ref, name, 240)
        require("\n" not in ref and "\t" not in ref, f"{name} must contain references, not multiline text.")
        collected.add(ref)


def strings(value: Any, name: str, limit: int = 5, length: int = 300) -> None:
    for entry in items(value, name, limit):
        text_field(entry, name, length)


def validate_versions(value: Any) -> None:
    object_fields(value, VERSION_FIELDS, set(), "version_refs")
    for key, entry in value.items():
        if key == "index_generation":
            require(entry is None or (type(entry) is int and 0 <= entry <= 2**63 - 1), "Invalid index_generation.")
        else:
            text_field(entry, key, 240, nullable=True)


def validate_proposal(value: Any, collected: set[str], targets: list[str]) -> None:
    required = {"target_component", "change_kind", "problem", "proposed_change", "evidence_refs",
                "acceptance_criteria", "compatibility", "rollback", "proposal_state"}
    allowed = required | {"proven_layer", "alternatives", "migration", "artifact_refs"}
    object_fields(value, allowed, required, "change_proposal")
    require(value["target_component"] in targets, "Proposal component must appear in target_components.")
    enum_value(value["change_kind"], {"defect", "requirement", "structural"}, "proposal change_kind")
    enum_value(value["proposal_state"], {"proposed", "needs_evidence"}, "initial proposal state")
    for name in ("problem", "proposed_change", "compatibility", "rollback"):
        text_field(value[name], name, 600)
    for name in ("proven_layer", "migration"):
        if name in value:
            text_field(value[name], name, 400, nullable=True)
    if "alternatives" in value:
        strings(value["alternatives"], "alternatives", 3)
    references(value["evidence_refs"], "proposal.evidence_refs", collected)
    if "artifact_refs" in value:
        references(value["artifact_refs"], "artifact_refs", collected)
    strings(value["acceptance_criteria"], "acceptance_criteria")
    require(bool(value["acceptance_criteria"]), "A proposal needs at least one acceptance assertion.")


def validate_report(value: Any) -> str:
    object_fields(value, REPORT_FIELDS, REPORT_FIELDS, "report")
    require(value["report_format"] == REPORT_FORMAT, "Unsupported report_format.")
    require(value["advisory_only"] is True, "A system review must remain advisory_only=true.")
    require(type(value["review_revision"]) is int and 1 <= value["review_revision"] <= 2**31 - 1, "Invalid review_revision.")
    enum_value(value["trigger"], {"manual", "memory_error", "user_correction", "evidence_conflict", "repeated_gap"}, "trigger")
    enum_value(value["task_state"], {"in_progress", "completed", "failed", "blocked", "cancelled"}, "task_state")
    enum_value(value["task_outcome"], {"success", "failure", "partial", "unknown"}, "task_outcome")
    enum_value(value["memory_use"], {"used", "not_used", "unknown"}, "memory_use")
    enum_value(value["review_status"], {"completed", "partial", "skipped", "failed"}, "executed review_status")
    task = value["task_ref"]
    if task is not None:
        object_fields(task, {"key", "origin"}, {"key", "origin"}, "task_ref")
        identifier(task["key"], "task_ref.key")
        enum_value(task["origin"], {"host", "client_local"}, "task_ref.origin")
    if value["trigger"] != "manual":
        require(task is not None and value["task_state"] in {"completed", "failed", "blocked"},
                "Automatic review needs an associated closed task; cancellation does not trigger review.")
    validate_versions(value["version_refs"])
    targets = items(value["target_components"], "target_components", len(COMPONENTS))
    require(all(isinstance(entry, str) and entry in COMPONENTS for entry in targets) and len(set(targets)) == len(targets),
            "Invalid or duplicate target_components.")
    refs: set[str] = set()
    references(value["query_refs"], "query_refs", refs)
    for observation in items(value["observations"], "observations", 8):
        object_fields(observation, {"summary", "refs"}, {"summary", "refs"}, "observation")
        text_field(observation["summary"], "observation.summary")
        references(observation["refs"], "observation.refs", refs)
    for check in items(value["checks"], "checks", 5):
        object_fields(check, {"assertion", "expected_ref", "observed_refs", "result", "scope"},
                      {"assertion", "expected_ref", "observed_refs", "result", "scope"}, "check")
        text_field(check["assertion"], "assertion", 300)
        text_field(check["scope"], "scope", 300)
        text_field(check["expected_ref"], "expected_ref", 240, nullable=True)
        references(check["observed_refs"], "observed_refs", refs)
        enum_value(check["result"], {"pass", "fail", "unknown", "not_run"}, "check result")
        if check["expected_ref"] is not None:
            references([check["expected_ref"]], "expected_ref", refs)
        if check["result"] in {"pass", "fail"}:
            require(bool(check["expected_ref"]) and bool(check["observed_refs"]),
                    "A reported pass/fail needs expected and observed references; these remain caller assertions.")
    for opinion in items(value["model_opinions"], "model_opinions", 5):
        fields = {"dimension", "assessment", "evidence_refs", "counter_evidence_refs"}
        object_fields(opinion, fields, fields, "model_opinion")
        text_field(opinion["dimension"], "dimension", 80)
        text_field(opinion["assessment"], "assessment", 400)
        references(opinion["evidence_refs"], "opinion.evidence_refs", refs)
        references(opinion["counter_evidence_refs"], "counter_evidence_refs", refs)
    proposals = items(value["change_proposals"], "change_proposals", 1)
    for proposal in proposals:
        validate_proposal(proposal, refs, targets)
    require(not proposals or value["review_status"] in {"completed", "partial"}, "Skipped/failed reviews cannot create proposals.")
    require(len(refs) <= 8, "The complete report permits at most eight distinct evidence references.")
    strings(value["missing_evidence"], "missing_evidence", 8)
    omissions = value["omitted_counts"]
    object_fields(omissions, {"observations", "checks", "model_opinions", "change_proposals", "evidence_refs"}, set(), "omitted_counts")
    require(all(type(count) is int and 0 <= count <= 2**31 - 1 for count in omissions.values()), "Invalid omission count.")
    costs = value["additional_cost"]
    object_fields(costs, {"tokens", "elapsed_ms"}, {"tokens", "elapsed_ms"}, "additional_cost")
    require(costs["tokens"] is None or (type(costs["tokens"]) is int and 0 <= costs["tokens"] <= 2**63 - 1), "Invalid measured Token cost.")
    elapsed = costs["elapsed_ms"]
    require(elapsed is None or (type(elapsed) in {int, float} and 0 <= elapsed <= 10**15 and math.isfinite(elapsed)), "Invalid elapsed cost.")
    try:
        encoded = canonical_json(value)
        encoded.encode("utf-8")
    except (ValueError, TypeError, RecursionError, UnicodeError) as error:
        raise SystemEvolutionError("invalid_report", "Report cannot be serialized as bounded JSON.") from error
    require(len(encoded) <= MAX_REPORT_CHARS, "Report exceeds the 4,000-character canonical JSON limit.")
    return encoded


def unique_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON object keys are not accepted.")
        result[key] = value
    return result


def load_report(payload: str | None, payload_file: str | None) -> dict[str, Any]:
    require(bool(payload) != bool(payload_file), "Supply exactly one of --payload or --payload-file.")
    if payload_file:
        try:
            with Path(payload_file).expanduser().open("rb") as handle:
                raw = handle.read(MAX_INPUT_BYTES + 1)
            require(len(raw) <= MAX_INPUT_BYTES, "Report input exceeds the bounded file read.")
            supplied = raw.decode("utf-8")
        except (OSError, ValueError, RuntimeError) as error:
            if isinstance(error, SystemEvolutionError):
                raise
            raise SystemEvolutionError("invalid_report", "Cannot read report as UTF-8.") from error
    else:
        supplied = payload or ""
    require(len(supplied) <= MAX_REPORT_CHARS, "Report input exceeds 4,000 Unicode characters.")
    try:
        value = json.loads(supplied, object_pairs_hook=unique_object_keys)
    except (ValueError, RecursionError) as error:
        if isinstance(error, SystemEvolutionError):
            raise
        raise SystemEvolutionError("invalid_report", "Report is not valid bounded JSON.") from error
    validate_report(value)
    return value
