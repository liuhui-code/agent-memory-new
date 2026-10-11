# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from typing import Any

from .models import Project
from .normative_documents import approval_metadata_complete, observe_document_source
from .normative_relationships import inspect_cached_document_links


SOURCE_SAMPLE_LIMIT = 20
REVIEW_SAMPLE_LIMIT = 5


def normative_index_health(conn: sqlite3.Connection, project: Project) -> dict[str, Any]:
    """Describe cached declarations and a bounded source sample, never certify them."""
    status_counts = {
        row["status"]: row["count"] for row in conn.execute(
            """SELECT status, COUNT(*) AS count FROM normative_documents
               WHERE project_id = ? GROUP BY status ORDER BY status""",
            (project.project_id,),
        ).fetchall()
    }
    document_count = sum(status_counts.values())
    duplicate_count = conn.execute(
        """SELECT COUNT(*) AS count FROM (
             SELECT 1 FROM normative_documents WHERE project_id = ?
             GROUP BY source_root, document_id HAVING COUNT(*) > 1
           )""",
        (project.project_id,),
    ).fetchone()["count"]
    rows = conn.execute(
        """SELECT id, document_id, kind, status, source_root, file_path,
                  scopes, approval, supersedes, superseded_by, source_digest,
                  source_revision, index_generation
           FROM normative_documents WHERE project_id = ?
           ORDER BY updated_at DESC, id DESC LIMIT ?""",
        (project.project_id, SOURCE_SAMPLE_LIMIT),
    ).fetchall()
    freshness_counts: Counter[str] = Counter()
    review_rows: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        freshness, observed_digest = observe_document_source(item)
        freshness_counts[freshness] += 1
        warnings = []
        if freshness != "current":
            warnings.append("document_" + freshness)
        try:
            approval = json.loads(item["approval"])
            scopes = json.loads(item["scopes"])
            if not isinstance(approval, dict) or not isinstance(scopes, list):
                raise ValueError("invalid cached metadata")
        except (TypeError, ValueError):
            approval, scopes = {}, []
            warnings.append("invalid_cached_metadata")
        if item["status"] == "approved" and not approval_metadata_complete(approval):
            warnings.append("approval_metadata_incomplete")
        if not scopes:
            warnings.append("scope_missing")
        if item["status"] == "unknown":
            warnings.append("document_status_unknown")
        links = inspect_cached_document_links(conn, project.project_id, item)
        warnings.extend(links["warnings"])
        if warnings:
            review_rows.append({
                "record_id": item["id"], "document_id": item["document_id"], "kind": item["kind"],
                "declared_status": item["status"], "source_root": item["source_root"],
                "file_path": item["file_path"], "source_freshness": freshness,
                "source_digest": item["source_digest"], "observed_digest": observed_digest,
                "observed_revision": item["source_revision"],
                "index_generation": item["index_generation"], "warnings": warnings,
            })
            if links["forward_links"] or links["reverse_refs"]:
                review_rows[-1]["replacement_lookup"] = links
    return {
        "schema_version": "normative-index-health/v1",
        "document_count": document_count,
        "declared_status_counts": status_counts,
        "duplicate_identity_count": duplicate_count,
        "source_sample": {
            "selection": "most_recently_indexed_documents", "limit": SOURCE_SAMPLE_LIMIT,
            "sampled_document_count": len(rows),
            "unexamined_document_count": document_count - len(rows),
            "freshness_counts": dict(sorted(freshness_counts.items())),
            "truncated": document_count > len(rows),
            "git_state_checked": False,
        },
        "sample_review_document_count": len(review_rows),
        "review_sample": review_rows[:REVIEW_SAMPLE_LIMIT],
        "review_sample_truncated": len(review_rows) > REVIEW_SAMPLE_LIMIT,
        "approval_review_required": bool(document_count),
        "advisory_notice": (
            "Index counts and bounded source samples do not verify approval, applicability, "
            "acceptance or overall freshness. Review original Git documents and refresh "
            "their existing learned scopes when needed."
        ),
    }
