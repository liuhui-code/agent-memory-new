# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CASE_SCHEMA = "agent-benchmark-cases/v1"
REVIEW_STATUSES = {"draft", "validated", "holdout", "rejected"}
TASK_TYPES = {"diagnosis", "design"}


def load_case_pack(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"failed to read benchmark cases: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid benchmark case JSON: {path}") from exc
    return validate_case_pack(data)


def validate_case_pack(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != CASE_SCHEMA:
        raise SystemExit(f"unsupported benchmark case schema; expected {CASE_SCHEMA}")
    cases = value.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SystemExit("benchmark case pack requires a non-empty cases list")
    seen: set[str] = set()
    normalized = [validate_case(item, index, seen) for index, item in enumerate(cases)]
    return {**value, "cases": normalized}


def validate_case(value: Any, index: int, seen: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"benchmark case {index} must be an object")
    case_id = required_text(value, "id", index)
    if case_id in seen:
        raise SystemExit(f"duplicate benchmark case id: {case_id}")
    seen.add(case_id)
    task_type = required_text(value, "task_type", index)
    if task_type not in TASK_TYPES:
        raise SystemExit(f"benchmark case {case_id} has unsupported task_type: {task_type}")
    review_status = str(value.get("review_status") or "draft")
    if review_status not in REVIEW_STATUSES:
        raise SystemExit(f"benchmark case {case_id} has unsupported review_status: {review_status}")
    task = value.get("task")
    source = value.get("source")
    oracle = value.get("oracle")
    if not isinstance(task, dict) or not str(task.get("description") or "").strip():
        raise SystemExit(f"benchmark case {case_id} requires task.description")
    if not isinstance(source, dict):
        raise SystemExit(f"benchmark case {case_id} requires source")
    if not isinstance(oracle, dict):
        raise SystemExit(f"benchmark case {case_id} requires hidden oracle")
    expected_files = string_list(oracle.get("expected_files"), f"case {case_id} oracle.expected_files")
    if not expected_files:
        raise SystemExit(f"benchmark case {case_id} requires oracle.expected_files")
    forbidden = string_list(oracle.get("forbidden_files") or [], f"case {case_id} oracle.forbidden_files")
    return {
        **value,
        "id": case_id,
        "task_type": task_type,
        "review_status": review_status,
        "task": dict(task),
        "source": dict(source),
        "oracle": {**oracle, "expected_files": expected_files, "forbidden_files": forbidden},
    }


def public_case(case: dict[str, Any]) -> dict[str, Any]:
    provenance = dict(case.get("provenance") or {})
    for key in ("commit_message", "fix_commit", "after_revision"):
        provenance.pop(key, None)
    source = dict(case.get("source") or {})
    for key in ("after_revision", "fix_commit", "mutation"):
        source.pop(key, None)
    return {
        "id": case["id"],
        "task_type": case["task_type"],
        "task": dict(case["task"]),
        "source": source,
        "provenance": provenance,
        "capabilities": {
            "baseline": ["current_source"],
            "memory": ["current_source", "agent-memory-query"],
        },
    }


def eligible_cases(pack: dict[str, Any], allow_drafts: bool) -> list[dict[str, Any]]:
    allowed = {"validated", "holdout"}
    if allow_drafts and pack.get("suite") != "holdout":
        allowed.add("draft")
    return [case for case in pack["cases"] if case["review_status"] in allowed]


def write_case_pack(path: Path, pack: dict[str, Any], force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"benchmark case target already exists: {path}; pass --force to replace")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def new_pack(generator: str, project_path: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": CASE_SCHEMA,
        "suite": "development",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": generator,
        "project_path": project_path,
        "cases": cases,
        "governance": {
            "oracle_hidden_from_runner": True,
            "holdout_requires_review": True,
            "raw_logs_persisted": False,
        },
    }


def generation_result(pack: dict[str, Any], target: Path) -> dict[str, Any]:
    cases = pack["cases"]
    return {
        "schema_version": pack["schema_version"],
        "generator": pack.get("generator"),
        "target": str(target),
        "audit": pack.get("audit") or {},
        "case_previews": [
            {
                "id": case["id"],
                "task_type": case["task_type"],
                "review_status": case["review_status"],
                "provenance_kind": case.get("provenance", {}).get("kind"),
                "description": str(case.get("task", {}).get("description") or "")[:160],
                "expected_file_count": len(case.get("oracle", {}).get("expected_files") or []),
            }
            for case in cases[:20]
        ],
        "next_steps": [
            "Review task wording, expected files, root-cause category, forbidden directions, and verification tests.",
            "Promote only reviewed cases from draft to validated; keep holdout cases isolated from tuning.",
            "Run eval-agent-benchmark with an approved Runner after review.",
        ],
    }


def required_text(value: dict[str, Any], key: str, index: int) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise SystemExit(f"benchmark case {index} requires {key}")
    return item.strip()


def string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit(f"{label} must be a string list")
    return list(dict.fromkeys(item.strip() for item in value if item.strip()))
