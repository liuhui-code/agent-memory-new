# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PROTOCOL_SCHEMA = "prospective-agent-cohort/v1"
TREATMENT_MODE = "selective-query-skill"
EVIDENCE_ORIGINS = {"generated_protocol_calibration", "prospective_real_tasks"}
ELIGIBILITY = {"eligible", "excluded"}
OPPORTUNITIES = {"present", "absent", "unknown"}
EVIDENCE_TYPES = {"semantic", "reflection", "episode", "code_log"}
OUTCOMES = {"pass", "fail", "partial", "unknown"}
VERIFICATIONS = {"test", "build", "source_review", "user_confirmation", "unverified"}
PRIVACY_FLAGS = {
    "persist_raw_task", "persist_raw_query", "persist_raw_logs", "persist_reasoning",
}
PAIRED_REPLAY_MODES = {"disabled", "first_eligible"}
COHORT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


def load_protocol(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"failed to read prospective cohort protocol: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid prospective cohort protocol JSON: {path}") from exc
    return validate_protocol(value)


def validate_protocol(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != PROTOCOL_SCHEMA:
        raise SystemExit(f"prospective cohort protocol requires {PROTOCOL_SCHEMA}")
    cohort_id = required_text(value, "cohort_id", 64)
    if not COHORT_ID.fullmatch(cohort_id):
        raise SystemExit("prospective cohort_id contains unsupported characters")
    title = required_text(value, "title", 160)
    evidence_origin = str(value.get("evidence_origin") or "")
    if evidence_origin not in EVIDENCE_ORIGINS:
        raise SystemExit("prospective cohort requires a classified evidence_origin")
    if value.get("task_type") != "diagnosis":
        raise SystemExit("prospective cohort v1 supports diagnosis tasks only")
    target = value.get("target_presented_tasks")
    if not isinstance(target, int) or isinstance(target, bool) or not 1 <= target <= 100:
        raise SystemExit("target_presented_tasks must be an integer between 1 and 100")
    enrollment = require_object(value, "enrollment")
    if enrollment.get("mode") != "consecutive":
        raise SystemExit("prospective cohort enrollment mode must be consecutive")
    source_scope = required_text(enrollment, "source_scope", 200)
    reasons = string_list(enrollment.get("allowed_exclusion_reasons"), "allowed exclusion reasons")
    if not reasons or len(reasons) > 20:
        raise SystemExit("prospective cohort requires 1 to 20 exclusion reasons")
    hypothesis = require_object(value, "hypothesis")
    primary = required_text(hypothesis, "primary", 500)
    if hypothesis.get("treatment_mode") != TREATMENT_MODE:
        raise SystemExit(f"prospective cohort treatment_mode must be {TREATMENT_MODE}")
    metrics = require_object(value, "metrics")
    normalized_metrics = {
        name: string_list(metrics.get(name), f"metrics.{name}")
        for name in ("overall", "diagnostic", "guardrails")
    }
    if any(not items for items in normalized_metrics.values()):
        raise SystemExit("prospective cohort requires overall, diagnostic, and guardrail metrics")
    stop = require_object(value, "stop_rule")
    if stop.get("type") != "fixed_presented_count":
        raise SystemExit("prospective cohort requires a fixed presented-count stop rule")
    if stop.get("optional_stopping") is not False:
        raise SystemExit("prospective cohort forbids optional stopping")
    policy = require_object(value, "data_policy")
    if set(policy) != PRIVACY_FLAGS or any(policy.get(key) is not False for key in PRIVACY_FLAGS):
        raise SystemExit("prospective cohort cannot persist raw cohort data")
    paired_replay = validate_paired_replay(value.get("paired_replay"))
    return {
        "schema_version": PROTOCOL_SCHEMA,
        "cohort_id": cohort_id,
        "title": title,
        "evidence_origin": evidence_origin,
        "task_type": "diagnosis",
        "target_presented_tasks": target,
        "enrollment": {
            "mode": "consecutive",
            "source_scope": source_scope,
            "allowed_exclusion_reasons": reasons,
        },
        "hypothesis": {"primary": primary, "treatment_mode": TREATMENT_MODE},
        "metrics": normalized_metrics,
        "stop_rule": {"type": "fixed_presented_count", "optional_stopping": False},
        "data_policy": {key: False for key in sorted(PRIVACY_FLAGS)},
        "paired_replay": paired_replay,
    }


def validate_paired_replay(value: Any) -> dict[str, Any]:
    if value is None:
        return {"mode": "disabled"}
    if not isinstance(value, dict) or str(value.get("mode") or "") not in PAIRED_REPLAY_MODES:
        raise SystemExit("paired_replay requires a supported mode")
    mode = str(value["mode"])
    if mode == "disabled":
        if set(value) != {"mode"}:
            raise SystemExit("disabled paired_replay cannot include replay settings")
        return {"mode": "disabled"}
    candidates = value.get("max_candidates")
    snapshot_bytes = value.get("max_snapshot_bytes")
    retention_days = value.get("retention_days")
    if not isinstance(candidates, int) or isinstance(candidates, bool) or not 1 <= candidates <= 10:
        raise SystemExit("paired_replay.max_candidates must be between 1 and 10")
    if not isinstance(snapshot_bytes, int) or isinstance(snapshot_bytes, bool) or not 1_000_000 <= snapshot_bytes <= 536_870_912:
        raise SystemExit("paired_replay.max_snapshot_bytes must be between 1 MiB and 512 MiB")
    if not isinstance(retention_days, int) or isinstance(retention_days, bool) or not 1 <= retention_days <= 365:
        raise SystemExit("paired_replay.retention_days must be between 1 and 365")
    return {
        "mode": "first_eligible", "max_candidates": candidates,
        "max_snapshot_bytes": snapshot_bytes, "retention_days": retention_days,
    }


def validate_enrollment(
    protocol: dict[str, Any],
    eligibility: str,
    opportunity: str,
    evidence_refs: list[str] | None,
    exclusion_reason: str | None,
) -> dict[str, Any]:
    if eligibility not in ELIGIBILITY:
        raise SystemExit("cohort task eligibility must be eligible or excluded")
    if opportunity not in OPPORTUNITIES:
        raise SystemExit("cohort task opportunity must be present, absent, or unknown")
    reason = str(exclusion_reason or "").strip()
    allowed = set(protocol["enrollment"]["allowed_exclusion_reasons"])
    if eligibility == "excluded":
        if reason not in allowed:
            raise SystemExit("excluded task requires a preregistered exclusion reason")
        if opportunity != "unknown":
            raise SystemExit("excluded task opportunity must remain unknown")
    elif reason:
        raise SystemExit("eligible task cannot include an exclusion reason")
    parsed = [parse_evidence_ref(item) for item in evidence_refs or []]
    if opportunity == "present" and not parsed:
        raise SystemExit("memory opportunity requires an evidence reference")
    if opportunity != "present" and parsed:
        raise SystemExit(f"{opportunity} opportunity cannot include evidence references")
    return {
        "eligibility": eligibility,
        "opportunity": opportunity,
        "evidence_refs": parsed,
        "exclusion_reason": reason or None,
    }


def validate_completion(outcome: str, verification: str) -> None:
    if outcome not in OUTCOMES:
        raise SystemExit("unsupported prospective cohort outcome")
    if verification not in VERIFICATIONS:
        raise SystemExit("unsupported prospective cohort verification")
    if outcome != "unknown" and verification == "unverified":
        raise SystemExit("a known cohort outcome requires objective verification")


def validate_task_id(value: str) -> str:
    task_id = str(value or "").strip()
    if not COHORT_ID.fullmatch(task_id):
        raise SystemExit("cohort task_id must be a bounded opaque identifier")
    return task_id


def parse_evidence_ref(value: str) -> dict[str, Any]:
    kind, separator, raw_id = str(value or "").strip().partition(":")
    if not separator or kind not in EVIDENCE_TYPES or not raw_id.isdigit() or int(raw_id) < 1:
        raise SystemExit("invalid cohort evidence reference; expected type:positive-id")
    return {"record_type": kind, "record_id": int(raw_id)}


def require_object(value: dict[str, Any], key: str) -> dict[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict):
        raise SystemExit(f"prospective cohort protocol requires {key}")
    return item


def required_text(value: dict[str, Any], key: str, limit: int) -> str:
    text = str(value.get(key) or "").strip()
    if not text or len(text) > limit:
        raise SystemExit(f"prospective cohort protocol requires bounded {key}")
    return text


def string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise SystemExit(f"prospective cohort {label} must be a list")
    result = [str(item).strip() for item in value if str(item).strip()]
    if len(result) != len(set(result)):
        raise SystemExit(f"prospective cohort {label} cannot contain duplicates")
    return result
