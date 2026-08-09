# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


MANIFEST_SCHEMA = "campaign-source-manifest/v1"
BINDING_SCHEMA = "campaign-input-binding/v1"
REAL_TASKS = "prospective_real_tasks"
CALIBRATION = "generated_protocol_calibration"
CAMPAIGN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
VERIFICATION_METHODS = {"test", "build", "source_review", "user_confirmation"}


def bind_campaign_input(
    protocol: dict[str, Any], manifest_path: Path | None, project_root: Path, memory_home: Path,
) -> dict[str, Any]:
    origin = str(protocol.get("evidence_origin") or "")
    if origin == CALIBRATION:
        if manifest_path is not None:
            raise SystemExit("generated calibration cohorts cannot use a campaign manifest")
        return protocol
    if origin != REAL_TASKS:
        raise SystemExit("prospective cohort requires a classified evidence_origin")
    if manifest_path is None:
        raise SystemExit("prospective real cohort requires verified campaign input")
    manifest = load_manifest(manifest_path)
    validate_manifest(manifest, protocol, project_root, memory_home)
    return {
        **protocol,
        "campaign_input": {
            "schema_version": BINDING_SCHEMA,
            "status": "verified",
            "manifest_digest": canonical_digest(manifest),
            "campaign_id_digest": digest_text(str(manifest["campaign_id"])),
        },
    }


def require_campaign_input(protocol: dict[str, Any]) -> None:
    if campaign_input_status(protocol) == "unverified_campaign_input":
        raise SystemExit("prospective real cohort requires verified campaign input")


def campaign_input_status(protocol: dict[str, Any]) -> str:
    if str(protocol.get("evidence_origin") or "") != REAL_TASKS:
        return "not_required"
    binding = protocol.get("campaign_input")
    if not isinstance(binding, dict):
        return "unverified_campaign_input"
    if binding.get("schema_version") != BINDING_SCHEMA or binding.get("status") != "verified":
        return "unverified_campaign_input"
    if not all(valid_digest(binding.get(key)) for key in ("manifest_digest", "campaign_id_digest")):
        return "unverified_campaign_input"
    return "verified"


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit("failed to read campaign source manifest") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit("invalid campaign source manifest JSON") from exc
    if not isinstance(value, dict):
        raise SystemExit("campaign source manifest must be an object")
    return value


def validate_manifest(
    manifest: dict[str, Any], protocol: dict[str, Any], project_root: Path, memory_home: Path,
) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA or manifest.get("status") != "confirmed":
        raise SystemExit("campaign source manifest must be confirmed v1")
    campaign_id = required_text(manifest, "campaign_id", 64)
    if not CAMPAIGN_ID.fullmatch(campaign_id):
        raise SystemExit("campaign source manifest requires a bounded campaign_id")
    project = required_object(manifest, "project")
    ensure_path(project, "local_path", project_root, "project")
    required_text(project, "project_owner_role", 160)
    if project.get("source_revision_policy") != "clean_revision_required":
        raise SystemExit("campaign source manifest requires clean source revision policy")
    task_stream = required_object(manifest, "task_stream")
    required_text(task_stream, "source_description", 500)
    required_text(task_stream, "continuity_owner_role", 160)
    required_text(task_stream, "starts_at", 64)
    memory = required_object(manifest, "memory")
    ensure_path(memory, "task_start_memory_home", memory_home, "memory home")
    verification = required_object(manifest, "verification")
    methods = string_list(verification.get("allowed_methods"), "verification.allowed_methods")
    if not methods or not set(methods) <= VERIFICATION_METHODS:
        raise SystemExit("campaign source manifest requires supported verification methods")
    custody = required_object(manifest, "raw_task_custody")
    required_text(custody, "outside_sqlite_location", 500)
    days = custody.get("retention_days")
    if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 3650:
        raise SystemExit("campaign source manifest requires bounded custody retention")
    validate_cohort(manifest, protocol)
    paired = required_object(manifest, "paired_replay")
    if paired.get("candidate_policy") != "first_eligible_clean_revision_only":
        raise SystemExit("campaign source manifest requires bounded paired replay policy")
    runner = required_object(manifest, "runner")
    if runner.get("frozen_source_context_sharing_authorized") is not True:
        raise SystemExit("campaign source manifest requires frozen source context authorization")
    claims = required_object(manifest, "claims")
    if claims.get("feasibility_only") is not True or claims.get("no_generalization_or_promotion_claim") is not True:
        raise SystemExit("campaign source manifest requires feasibility-only claims")


def validate_cohort(manifest: dict[str, Any], protocol: dict[str, Any]) -> None:
    cohort = required_object(manifest, "cohort")
    if cohort.get("fixed_presented_count") != protocol.get("target_presented_tasks"):
        raise SystemExit("campaign source manifest fixed task count does not match protocol")
    actual = string_list(cohort.get("allowed_exclusion_reasons"), "cohort exclusions")
    expected = protocol.get("enrollment", {}).get("allowed_exclusion_reasons")
    if actual != expected:
        raise SystemExit("campaign source manifest exclusions do not match protocol")
    if cohort.get("optional_stopping") is not False:
        raise SystemExit("campaign source manifest forbids optional stopping")
    if cohort.get("dirty_task_policy") != "natural_observation_only":
        raise SystemExit("campaign source manifest requires natural observation dirty-task policy")


def ensure_path(value: dict[str, Any], key: str, expected: Path, label: str) -> None:
    raw = required_text(value, key, 1000)
    if Path(raw).expanduser().resolve() != expected.expanduser().resolve():
        raise SystemExit(f"campaign source manifest {label} does not match active context")


def required_object(value: dict[str, Any], key: str) -> dict[str, Any]:
    result = value.get(key)
    if not isinstance(result, dict):
        raise SystemExit(f"campaign source manifest requires {key}")
    return result


def required_text(value: dict[str, Any], key: str, limit: int) -> str:
    result = str(value.get(key) or "").strip()
    if not result or len(result) > limit:
        raise SystemExit(f"campaign source manifest requires bounded {key}")
    return result


def string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise SystemExit(f"campaign source manifest {label} must be a list")
    result = [str(item).strip() for item in value if str(item).strip()]
    if len(result) != len(set(result)):
        raise SystemExit(f"campaign source manifest {label} cannot contain duplicates")
    return result


def canonical_digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return digest_text(payload)


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def valid_digest(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))
