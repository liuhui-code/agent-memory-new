# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from typing import Any


POLICY_NAME = "anchor_first_deterministic_expansion_v8"
RUNNER_TELEMETRY_POLICIES = {
    "anchor_first_gap_driven_v4",
    "anchor_first_sufficient_evidence_v5",
    "anchor_first_ledgered_stop_v6",
    "anchor_first_search_ledger_v7",
    POLICY_NAME,
}
READ_LEDGER_POLICIES = {"anchor_first_ledgered_stop_v6"}
DETERMINISTIC_EXPANSION_POLICIES = {POLICY_NAME}
PRIMARY_ANCHOR_LIMIT = 3
EXPANSION_ANCHOR_LIMIT = 2
SOURCE_SEARCH_LIMIT = 3
SOURCE_READS_PER_FILE_LIMIT = 2
SOURCE_READ_LINE_LIMIT = 180
EXPANSION_ROUND_LIMIT = 2
FILES_PER_EXPANSION_LIMIT = 2
SOURCE_FILE_LIMIT = PRIMARY_ANCHOR_LIMIT + (
    EXPANSION_ROUND_LIMIT * FILES_PER_EXPANSION_LIMIT
)
ALLOWED_EXPANSION_REASONS = (
    "missing_emitter",
    "missing_caller",
    "missing_state_owner",
    "missing_async_boundary",
    "missing_route_target",
    "missing_resource_owner",
    "contradicting_evidence",
)
STOP_REASONS = (
    "supported_cause_found",
    "direct_verification_settled",
    "budget_exhausted_report_uncertainty",
    "no_new_evidence",
)
EVIDENCE_BASES = (
    "direct_source_mechanism",
    "runtime_verified_mechanism",
    "inference_only",
)
EXPLORATION_RESPONSE_FIELDS = (
    "source_search_count",
    "expansion_rounds",
    "expansion_reason_codes",
    "stop_reason",
    "primary_anchor_hit_count",
    "non_anchor_file_count",
    "evidence_basis",
    "mechanism_evidence_files",
)


def exploration_contract() -> dict[str, Any]:
    return {
        "policy": POLICY_NAME,
        "limits": {
            "primary": PRIMARY_ANCHOR_LIMIT,
            "rounds": EXPANSION_ROUND_LIMIT,
            "round_files": FILES_PER_EXPANSION_LIMIT,
            "searches": SOURCE_SEARCH_LIMIT,
            "files": SOURCE_FILE_LIMIT,
            "reads_per_file": SOURCE_READS_PER_FILE_LIMIT,
            "read_lines": SOURCE_READ_LINE_LIMIT,
        },
    }


def assign_anchor_roles(anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = anchors[: PRIMARY_ANCHOR_LIMIT + EXPANSION_ANCHOR_LIMIT]
    return [
        {
            **item,
            "role": "primary" if index < PRIMARY_ANCHOR_LIMIT else "expansion",
        }
        for index, item in enumerate(selected)
    ]


def exploration_metrics_reported(observation: dict[str, Any]) -> bool:
    return all(field in observation for field in EXPLORATION_RESPONSE_FIELDS)


def source_exploration_within_budget(observations: list[dict[str, Any]]) -> bool:
    memory = [item for item in observations if item.get("variant") == "memory"]
    reported = [item for item in memory if item.get("exploration_metrics_reported")]
    if not reported:
        return True
    return len(reported) == len(memory) and all(
        observation_within_budget(item) for item in reported
    )


def observation_within_budget(observation: dict[str, Any]) -> bool:
    rounds = int(observation.get("expansion_rounds") or 0)
    source_files = int(observation.get("source_file_count") or 0)
    primary_hits = int(observation.get("primary_anchor_hit_count") or 0)
    expanded_files = max(0, source_files - primary_hits)
    reasons = observation.get("expansion_reason_codes") or []
    stop_reason = str(observation.get("stop_reason") or "")
    evidence_basis = str(observation.get("evidence_basis") or "")
    mechanism_files = set(observation.get("mechanism_evidence_files") or [])
    predicted_files = set(observation.get("predicted_files") or [])
    investigated_files = set(observation.get("investigated_files") or [])
    trace = observation.get("expansion_trace") or []
    trace_reported = bool(observation.get("expansion_trace_reported"))
    valid_reasons = (
        deterministic_expansion_audit(
            observation,
            rounds,
            reasons,
            trace,
            investigated_files,
            expanded_files,
        )
        if uses_deterministic_expansion(observation)
        else valid_expansion_audit(
            rounds,
            reasons,
            trace,
            trace_reported,
            investigated_files,
            expanded_files,
        )
    )
    return (
        source_files <= SOURCE_FILE_LIMIT
        and int(observation.get("source_search_count") or 0) <= SOURCE_SEARCH_LIMIT
        and source_search_audit_valid(observation)
        and source_read_audit_valid(observation)
        and int(observation.get("non_anchor_file_count") or 0)
        <= rounds * FILES_PER_EXPANSION_LIMIT
        and rounds <= EXPANSION_ROUND_LIMIT
        and expanded_files <= rounds * FILES_PER_EXPANSION_LIMIT
        and valid_reasons
        and stop_reason in STOP_REASONS
        and evidence_basis in EVIDENCE_BASES
        and supported_stop_has_direct_evidence(
            stop_reason,
            evidence_basis,
            mechanism_files,
            predicted_files,
            investigated_files,
        )
    )


def source_search_audit_valid(observation: dict[str, Any]) -> bool:
    metadata = observation.get("runner_metadata")
    if not isinstance(metadata, dict):
        return True
    is_audited_codex = (
        metadata.get("runner") == "codex_cli"
        and metadata.get("retrieval_policy") in RUNNER_TELEMETRY_POLICIES
    )
    return not is_audited_codex or (
        observation.get("source_search_count_source") == "runner_telemetry"
    )


def source_read_audit_valid(observation: dict[str, Any]) -> bool:
    metadata = observation.get("runner_metadata")
    if not isinstance(metadata, dict):
        return True
    is_ledgered_codex = (
        metadata.get("runner") == "codex_cli"
        and metadata.get("retrieval_policy") in READ_LEDGER_POLICIES
    )
    return not is_ledgered_codex or (
        bool(observation.get("cost_metrics_reported"))
        and int(observation.get("source_read_count") or 0)
        <= int(observation.get("source_file_count") or 0)
    )


def uses_deterministic_expansion(observation: dict[str, Any]) -> bool:
    metadata = observation.get("runner_metadata")
    return (
        isinstance(metadata, dict)
        and metadata.get("runner") == "codex_cli"
        and metadata.get("retrieval_policy") in DETERMINISTIC_EXPANSION_POLICIES
    )


def deterministic_expansion_audit(
    observation: dict[str, Any],
    rounds: int,
    reasons: Any,
    trace: Any,
    investigated_files: set[str],
    expanded_files: int,
) -> bool:
    reported_count = int(observation.get("expansion_file_count") or 0)
    expected_rounds = (
        expanded_files + FILES_PER_EXPANSION_LIMIT - 1
    ) // FILES_PER_EXPANSION_LIMIT
    if (
        observation.get("expansion_accounting_source")
        != "runner_investigated_files"
        or reported_count != expanded_files
        or rounds != expected_rounds
        or rounds > EXPANSION_ROUND_LIMIT
        or not isinstance(reasons, list)
        or not isinstance(trace, list)
    ):
        return False
    if expanded_files == 0:
        return not reasons and not trace
    if not 1 <= len(reasons) <= rounds or len(trace) != len(reasons):
        return False
    traced_files: set[str] = set()
    for index, step in enumerate(trace):
        if not isinstance(step, dict) or step.get("reason") != reasons[index]:
            return False
        if reasons[index] not in ALLOWED_EXPANSION_REASONS:
            return False
        files = step.get("files")
        if not isinstance(files, list) or not 1 <= len(files) <= FILES_PER_EXPANSION_LIMIT:
            return False
        if len(set(files)) != len(files) or traced_files & set(files):
            return False
        traced_files.update(files)
    return traced_files <= investigated_files


def valid_expansion_audit(
    rounds: int,
    reasons: Any,
    trace: Any,
    trace_reported: bool,
    investigated_files: set[str],
    expanded_files: int,
) -> bool:
    if not isinstance(reasons, list) or len(reasons) != rounds:
        return False
    if any(reason not in ALLOWED_EXPANSION_REASONS for reason in reasons):
        return False
    if not trace_reported:
        return True
    if not isinstance(trace, list) or len(trace) != rounds:
        return False
    traced_files: set[str] = set()
    for index, step in enumerate(trace):
        if not isinstance(step, dict) or step.get("reason") != reasons[index]:
            return False
        files = step.get("files")
        if not isinstance(files, list) or not 1 <= len(files) <= FILES_PER_EXPANSION_LIMIT:
            return False
        if len(set(files)) != len(files) or traced_files & set(files):
            return False
        traced_files.update(files)
    return traced_files <= investigated_files and len(traced_files) == expanded_files


def supported_stop_has_direct_evidence(
    stop_reason: str,
    evidence_basis: str,
    mechanism_files: set[str],
    predicted_files: set[str],
    investigated_files: set[str],
) -> bool:
    if stop_reason != "supported_cause_found":
        return not mechanism_files or mechanism_files <= investigated_files
    return (
        evidence_basis in {"direct_source_mechanism", "runtime_verified_mechanism"}
        and bool(mechanism_files)
        and mechanism_files <= investigated_files
        and bool(mechanism_files & predicted_files)
    )
