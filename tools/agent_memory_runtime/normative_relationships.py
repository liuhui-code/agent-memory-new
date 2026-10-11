# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import sqlite3
from typing import Any


TARGET_PREVIEW_LIMIT = 2
REVERSE_PREVIEW_LIMIT = 3


def cached_reference(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": row["id"], "document_id": row["document_id"],
        "file_path": row["file_path"], "kind": row["kind"],
        "declared_status": row["status"], "source_digest": row["source_digest"],
        "observed_revision": row["source_revision"],
        "index_generation": row["index_generation"],
        "source_checked": False, "approval_verified": False,
    }


def inspect_cached_document_links(
    conn: sqlite3.Connection, project_id: str, row: dict[str, Any],
) -> dict[str, Any]:
    """Expose bounded cached declarations, without approving or resolving replacement."""
    identity = (project_id, row["source_root"], row["document_id"])
    duplicate = len(conn.execute(
        """SELECT id FROM normative_documents
           WHERE project_id = ? AND source_root = ? AND document_id = ? LIMIT 2""",
        identity,
    ).fetchall()) > 1
    warnings = ["duplicate_document_id"] if duplicate else []
    links: dict[str, Any] = {}
    for field, reciprocal in (("supersedes", "superseded_by"), ("superseded_by", "supersedes")):
        target_id = row.get(field)
        if not target_id:
            continue
        targets = [dict(target) for target in conn.execute(
            """SELECT id, document_id, file_path, kind, status, source_digest,
                      source_revision, index_generation, supersedes, superseded_by
               FROM normative_documents
               WHERE project_id = ? AND source_root = ? AND document_id = ?
               ORDER BY file_path LIMIT ?""",
            (project_id, row["source_root"], target_id, TARGET_PREVIEW_LIMIT + 1),
        ).fetchall()]
        state = "not_indexed" if not targets else "ambiguous" if len(targets) > 1 else "unique"
        links[field] = {
            "document_id": target_id, "lookup_state": state,
            "target_refs": [cached_reference(target) for target in targets[:TARGET_PREVIEW_LIMIT]],
            "target_refs_truncated": len(targets) > TARGET_PREVIEW_LIMIT,
        }
        if state != "unique":
            warnings.append(field + "_target_" + state)
            continue
        target = targets[0]
        if target["kind"] != row["kind"]:
            warnings.append(field + "_kind_mismatch")
        if not target[reciprocal]:
            warnings.append(field + "_reciprocal_missing")
        elif target[reciprocal] != row["document_id"]:
            warnings.append(field + "_reciprocal_disagreement")
        if target[field] == row["document_id"]:
            warnings.append("replacement_two_document_cycle")
        if field == "superseded_by" and target["status"] != "approved":
            warnings.append("superseded_by_target_not_declared_approved")
    reverse_rows = [dict(target) for target in conn.execute(
        """SELECT id, document_id, file_path, kind, status, source_digest,
                  source_revision, index_generation
           FROM normative_documents
           WHERE project_id = ? AND source_root = ? AND supersedes = ?
             AND status = 'approved' ORDER BY file_path LIMIT ?""",
        (*identity, REVERSE_PREVIEW_LIMIT + 1),
    ).fetchall()]
    if links or reverse_rows:
        warnings.append("replacement_claim_requires_agent_review")
    return {
        "lookup_basis": "cached_same_source_root_metadata",
        "source_root": row["source_root"], "duplicate_identity": duplicate,
        "forward_links": links,
        "reverse_refs": [cached_reference(target) for target in reverse_rows[:REVERSE_PREVIEW_LIMIT]],
        "reverse_refs_truncated": len(reverse_rows) > REVERSE_PREVIEW_LIMIT,
        "warnings": list(dict.fromkeys(warnings)),
        "target_sources_checked": False, "approval_verified": False,
    }


def compact_document_links(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "lookup_basis": value["lookup_basis"],
        "forward_links": {field: {key: link[key] for key in (
            "document_id", "lookup_state", "target_refs_truncated",
        )} for field, link in value["forward_links"].items()},
        "reverse_refs_truncated": value["reverse_refs_truncated"],
        "target_sources_checked": False, "approval_verified": False,
    }
