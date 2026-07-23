# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
from typing import Any


SEAL_SCHEMA = "agent-benchmark-case-seal/v1"
REQUIRED_HIDDEN_FIELDS = {
    "oracle",
    "source.after_revision",
    "provenance.commit_message",
}


def seal_case_pack(pack: dict[str, Any], sealed_at: str) -> dict[str, Any]:
    candidate = json_clone(pack)
    validate_sealable_pack(candidate)
    governance = candidate.get("governance")
    governance = dict(governance) if isinstance(governance, dict) else {}
    governance.update({
        "require_seal": True,
        "oracle_hidden_from_runner": True,
        "holdout_requires_review": True,
        "raw_logs_persisted": False,
    })
    candidate["governance"] = governance
    candidate.pop("seal", None)
    candidate["seal"] = {
        "schema_version": SEAL_SCHEMA,
        "sealed_at": required_text(sealed_at, "sealed_at"),
        "digest_algorithm": "sha256",
        "canonicalization": "json-sort-keys-compact-excluding-seal",
        "case_count": len(candidate["cases"]),
        "digest": case_pack_digest(candidate),
    }
    return candidate


def case_pack_seal_audit(pack: dict[str, Any]) -> dict[str, Any]:
    governance = pack.get("governance")
    governance = governance if isinstance(governance, dict) else {}
    seal = pack.get("seal")
    if seal is None:
        if governance.get("require_seal"):
            raise SystemExit("benchmark case pack requires a seal")
        return {
            "status": "unsealed",
            "required": False,
            "case_count": len(pack.get("cases") or []),
        }
    if not isinstance(seal, dict) or seal.get("schema_version") != SEAL_SCHEMA:
        raise SystemExit(f"benchmark case pack seal must use {SEAL_SCHEMA}")
    if seal.get("digest_algorithm") != "sha256":
        raise SystemExit("benchmark case pack seal requires sha256")
    expected = case_pack_digest(pack)
    observed = str(seal.get("digest") or "")
    if observed != expected:
        raise SystemExit("benchmark case pack seal digest mismatch")
    cases = pack.get("cases") if isinstance(pack.get("cases"), list) else []
    if int(seal.get("case_count") or -1) != len(cases):
        raise SystemExit("benchmark case pack seal case count mismatch")
    return {
        "status": "verified",
        "required": bool(governance.get("require_seal")),
        "schema_version": SEAL_SCHEMA,
        "digest": observed,
        "sealed_at": seal.get("sealed_at"),
        "case_count": len(cases),
    }


def case_pack_digest(pack: dict[str, Any]) -> str:
    payload = json_clone(pack)
    payload.pop("seal", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_sealable_pack(pack: dict[str, Any]) -> None:
    if pack.get("schema_version") != "agent-benchmark-cases/v1":
        raise SystemExit("only agent-benchmark-cases/v1 packs can be sealed")
    if pack.get("suite") != "holdout":
        raise SystemExit("only holdout case packs can be sealed")
    cases = pack.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SystemExit("sealed holdout requires at least one case")
    for case in cases:
        validate_sealable_case(case)


def validate_sealable_case(case: Any) -> None:
    if not isinstance(case, dict):
        raise SystemExit("sealed holdout case must be an object")
    case_id = str(case.get("id") or "<unknown>")
    if case.get("review_status") != "holdout":
        raise SystemExit(f"sealed case {case_id} must have holdout review status")
    source = case.get("source") if isinstance(case.get("source"), dict) else {}
    if not source.get("before_revision") or not source.get("after_revision"):
        raise SystemExit(f"sealed case {case_id} requires pre-fix and post-fix revisions")
    review = case.get("review") if isinstance(case.get("review"), dict) else {}
    if review.get("source_diff_reviewed") is not True:
        raise SystemExit(f"sealed case {case_id} requires source diff review")
    leakage = (
        case.get("leakage_guard")
        if isinstance(case.get("leakage_guard"), dict) else {}
    )
    hidden = set(leakage.get("hidden_fields") or [])
    missing = sorted(REQUIRED_HIDDEN_FIELDS - hidden)
    if missing:
        raise SystemExit(
            f"sealed case {case_id} missing hidden field guards: {', '.join(missing)}"
        )


def json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def required_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SystemExit(f"benchmark case seal requires {label}")
    return text

