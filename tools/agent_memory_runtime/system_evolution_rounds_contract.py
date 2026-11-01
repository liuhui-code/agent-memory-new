# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .system_evolution_check_plan import read_bounded_file
from .system_evolution_contract import (
    SystemEvolutionError, canonical_json, enum_value, identifier, object_fields, references, require,
    text_field, unique_object_keys,
)


def load_round_record(path: str) -> dict[str, Any]:
    try:
        raw = read_bounded_file(Path(path).expanduser(), 32768)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object_keys)
        validate_round_record(value)
        require(len(canonical_json(value).encode("utf-8")) <= 32768, "Round record exceeds its byte limit.")
        return value
    except (OSError, ValueError, RecursionError) as error:
        if isinstance(error, SystemEvolutionError):
            raise
        raise SystemEvolutionError("invalid_round_record", "Cannot read a bounded round record.") from error


def validate_round_record(value: Any) -> None:
    require(isinstance(value, dict), "Round record must be an object.")
    enum_value(value.get("kind"), {"open", "assessment", "decision"}, "record kind")
    common = {"schema_version", "kind", "record_key", "study_key", "round_key", "expected_revision"}
    extra = {"open": {"parent_round_key", "proposal_id", "application_key", "plan_file", "budget"},
             "assessment": {"observations_file", "observations_digest", "finding", "summary", "evidence_refs", "additional_cost"},
             "decision": {"assessment_revision", "decision", "note", "evidence_refs"}}[value["kind"]]
    object_fields(value, common | extra, common | extra, "round record")
    require(value["schema_version"] == "system-evolution-round-record/v1", "Unsupported round record.")
    for name in ("record_key", "study_key", "round_key"):
        identifier(value[name], name)
    require(type(value["expected_revision"]) is int and 0 <= value["expected_revision"] <= 22,
            "Invalid expected round revision.")
    if value["kind"] == "open":
        require(value["expected_revision"] == 0 and type(value["proposal_id"]) is int and 0 < value["proposal_id"] <= 2**63 - 1,
                "Opening requires revision zero and a positive proposal ID.")
        if value["parent_round_key"] is not None:
            identifier(value["parent_round_key"], "parent_round_key")
            require(value["parent_round_key"] != value["round_key"], "A round cannot parent itself.")
        identifier(value["application_key"], "application_key")
        text_field(value["plan_file"], "plan_file", 500)
        budget = value["budget"]
        object_fields(budget, {"max_rounds", "max_assessments"}, {"max_rounds", "max_assessments"}, "round budget")
        for name, maximum in (("max_rounds", 10), ("max_assessments", 20)):
            require(type(budget[name]) is int and 1 <= budget[name] <= maximum, "Invalid count budget.")
    else:
        require(value["expected_revision"] > 0, "An existing round revision is required.")
        refs: set[str] = set()
        references(value["evidence_refs"], "evidence_refs", refs)
        if value["kind"] == "assessment":
            text_field(value["observations_file"], "observations_file", 500)
            require(isinstance(value["observations_digest"], str) and bool(re.fullmatch(r"[0-9a-f]{64}", value["observations_digest"])),
                    "Declare the observation file SHA-256.")
            enum_value(value["finding"], {"supported", "contradicted", "inconclusive"}, "Agent finding")
            text_field(value["summary"], "assessment summary", 600)
            require(value["finding"] == "inconclusive" or bool(refs), "A supported/contradicted opinion requires evidence references.")
            cost = value["additional_cost"]
            object_fields(cost, {"tokens", "elapsed_ms"}, {"tokens", "elapsed_ms"}, "additional_cost")
            require(all(amount is None or (type(amount) is int and 0 <= amount <= 2**53 - 1) for amount in cost.values()),
                    "Invalid declared review cost.")
        else:
            enum_value(value["decision"], {"keep_baseline", "adopt_candidate", "rollback", "inconclusive", "stop"}, "Agent decision")
            require(value["assessment_revision"] is None or (type(value["assessment_revision"]) is int and value["assessment_revision"] > 0),
                    "Invalid assessment revision.")
            text_field(value["note"], "decision note", 600)
