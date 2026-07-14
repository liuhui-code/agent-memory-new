# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from .design_protocol import load_json_object


DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_BOUND_FILES = 500


def load_verification_provenance(
    manifest_path: str | None,
    project_root: Path | None,
    report_paths: list[str],
) -> dict[str, Any]:
    if not manifest_path:
        return {"schema_version": "verification-run/v1", "status": "unbound", "reasons": []}
    if project_root is None:
        raise SystemExit("verification run requires a project root")
    value = load_json_object(manifest_path, "verification run")
    if value.get("schema_version") != "verification-run/v1":
        raise SystemExit("unsupported verification run schema")
    head = required_string(value, "head_revision")
    base = optional_string(value, "base_revision")
    started_at = optional_string(value, "started_at")
    completed_at = optional_string(value, "completed_at")
    source_digests = digest_map(value.get("source_digests", {}), "source_digests")
    report_digests = digest_map(value.get("report_digests", {}), "report_digests")
    if len(source_digests) + len(report_digests) > MAX_BOUND_FILES:
        raise SystemExit(f"verification run exceeds {MAX_BOUND_FILES} bound files")
    reasons = revision_reasons(project_root, head)
    reasons.extend(digest_reasons(project_root, source_digests, "source"))
    reasons.extend(report_reasons(project_root, report_paths, report_digests))
    return {
        "schema_version": "verification-run/v1",
        "status": "stale" if reasons else "bound",
        "head_revision": head,
        "base_revision": base,
        "started_at": started_at,
        "completed_at": completed_at,
        "reasons": reasons[:50],
        "source_count": len(source_digests),
        "report_count": len(report_digests),
    }


def required_string(value: dict[str, Any], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise SystemExit(f"verification run {field} must be a non-empty string")
    return item.strip()


def optional_string(value: dict[str, Any], field: str) -> str | None:
    item = value.get(field)
    if item is None:
        return None
    if not isinstance(item, str) or not item.strip():
        raise SystemExit(f"verification run {field} must be a non-empty string when present")
    return item.strip()[:100]


def digest_map(value: Any, field: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise SystemExit(f"verification run {field} must be an object")
    result: dict[str, str] = {}
    for path, digest in value.items():
        if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
            raise SystemExit(f"verification run {field} contains an invalid path")
        if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
            raise SystemExit(f"verification run {field} contains an invalid sha256 digest")
        result[Path(path).as_posix()] = digest
    return result


def revision_reasons(root: Path, expected: str) -> list[dict[str, str]]:
    process = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False,
    )
    actual = process.stdout.strip() if process.returncode == 0 else ""
    if not actual:
        return [{"code": "git_revision_unavailable", "path": ""}]
    if actual != expected:
        return [{"code": "head_revision_mismatch", "path": "", "expected": expected, "actual": actual}]
    return []


def digest_reasons(root: Path, expected: dict[str, str], kind: str) -> list[dict[str, str]]:
    reasons = []
    for path, digest in expected.items():
        actual = file_digest(root / path)
        if actual != digest:
            reasons.append({"code": f"{kind}_digest_mismatch", "path": path})
    return reasons


def report_reasons(root: Path, reports: list[str], expected: dict[str, str]) -> list[dict[str, str]]:
    reasons = digest_reasons(root, expected, "report")
    for report in reports:
        path = Path(report).resolve()
        try:
            relative = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            reasons.append({"code": "report_outside_project", "path": str(path)})
            continue
        if relative not in expected:
            reasons.append({"code": "report_not_bound", "path": relative})
    return reasons


def file_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""
