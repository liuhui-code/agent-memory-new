# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from .models import Project
from .normative_documents import approval_metadata_complete, read_normative_document
from .text import terms_from_text, unique_list


class NormativeSourceReadError(RuntimeError):
    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report
        self.scope_id: int | None = None
        super().__init__(
            f"Cannot commit learning: {report['read_issue_count']} selected Markdown source "
            "read issue(s). Review the sources and retry the same scope."
        )


def sync_normative_index(
    conn: sqlite3.Connection,
    project: Project,
    files: list[Path],
    retired: list[str],
    generation: int,
    revision: str | None,
    timestamp: str,
    replace: bool = False,
) -> dict[str, Any]:
    """Participate in the caller's learning transaction without committing it."""
    source_root = str(project.root.resolve())
    changes: Counter[str] = Counter()
    retirement_counts: Counter[str] = Counter()
    retirement_sample: list[dict[str, Any]] = []
    indexed_sample: list[dict[str, Any]] = []
    read_issues: list[dict[str, str]] = []
    read_issue_count = 0
    metadata_review_count = 0

    def retire(relative: str, reason: str) -> None:
        previous = conn.execute(
            """SELECT id, document_id FROM normative_documents
               WHERE project_id = ? AND source_root = ? AND file_path = ?""",
            (project.project_id, source_root, relative),
        ).fetchone()
        if previous is None:
            return
        conn.execute(
            """DELETE FROM normative_documents
               WHERE project_id = ? AND source_root = ? AND file_path = ?""",
            (project.project_id, source_root, relative),
        )
        retirement_counts[reason] += 1
        if len(retirement_sample) < 20:
            retirement_sample.append({"record_id": previous["id"],
                                      "document_id": previous["document_id"],
                                      "file_path": relative, "reason": reason})

    if replace:
        # Keep selected rows until they are read; an I/O failure must not erase them.
        conn.execute("CREATE TEMP TABLE normative_index_selection(file_path TEXT PRIMARY KEY)")
        conn.executemany(
            "INSERT OR IGNORE INTO normative_index_selection(file_path) VALUES (?)",
            ((path.relative_to(project.root).as_posix(),) for path in files
             if path.suffix.lower() == ".md"),
        )
        excluded = """project_id = ? AND source_root = ? AND NOT EXISTS (
          SELECT 1 FROM normative_index_selection s WHERE s.file_path = normative_documents.file_path
        )"""
        remaining = 20 - len(retirement_sample)
        rows = conn.execute(
            f"SELECT id, document_id, file_path FROM normative_documents WHERE {excluded} ORDER BY file_path LIMIT ?",
            (project.project_id, source_root, remaining),
        ).fetchall()
        removed = conn.execute(
            f"DELETE FROM normative_documents WHERE {excluded}",
            (project.project_id, source_root),
        )
        retirement_counts["scope_replaced"] += removed.rowcount
        retirement_sample.extend({"record_id": row["id"], "document_id": row["document_id"],
                                  "file_path": row["file_path"], "reason": "scope_replaced"}
                                 for row in rows)
        conn.execute("DROP TABLE normative_index_selection")
    for relative in retired:
        retire(relative, "file_removed")
    indexed = 0
    issue_count = 0
    issues: list[dict[str, str]] = []
    for path in files:
        if path.suffix.lower() != ".md":
            continue
        relative = path.relative_to(project.root).as_posix()
        retirement_reason = "marker_removed"
        try:
            item = read_normative_document(project.root, relative)
        except OSError as error:
            read_issue_count += 1
            missing = isinstance(error, FileNotFoundError)
            if len(read_issues) < 20:
                read_issues.append({"file_path": relative,
                                    "reason": "source_missing" if missing else "source_unreadable",
                                    "detail": str(error)[:180]})
            if missing:
                retire(relative, "source_missing")
            continue
        except (UnicodeError, ValueError) as error:
            item = None
            retirement_reason = "invalid_metadata"
            issue_count += 1
            if len(issues) < 20:
                issues.append({"file_path": relative, "reason": str(error)[:180]})
        if item is None:
            retire(relative, retirement_reason)
            continue
        previous = conn.execute(
            """SELECT source_digest FROM normative_documents
               WHERE project_id = ? AND source_root = ? AND file_path = ?""",
            (project.project_id, source_root, relative),
        ).fetchone()
        change = "added" if previous is None else (
            "unchanged" if previous["source_digest"] == item["source_digest"] else "updated"
        )
        text = " ".join([item["document_id"], relative, item["title"],
                         *item["scopes"], item["body"]])
        search_terms = " ".join(unique_list(terms_from_text(text)))
        conn.execute(
            """
            INSERT INTO normative_documents(
              project_id, source_root, file_path, document_id, kind, title, status,
              scopes, approval, supersedes, superseded_by, body, body_start_line,
              search_terms, source_digest, source_revision, index_generation, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, source_root, file_path) DO UPDATE SET
              document_id=excluded.document_id, kind=excluded.kind, title=excluded.title,
              status=excluded.status, scopes=excluded.scopes, approval=excluded.approval,
              supersedes=excluded.supersedes, superseded_by=excluded.superseded_by,
              body=excluded.body, body_start_line=excluded.body_start_line,
              search_terms=excluded.search_terms, source_digest=excluded.source_digest,
              source_revision=excluded.source_revision,
              index_generation=excluded.index_generation, updated_at=excluded.updated_at
            """,
            (project.project_id, source_root, relative, item["document_id"], item["kind"],
             item["title"], item["status"], json.dumps(item["scopes"], ensure_ascii=False),
             json.dumps(item["approval"], ensure_ascii=False), item["supersedes"],
             item["superseded_by"], item["body"], item["body_start_line"], search_terms,
             item["source_digest"], revision, generation, timestamp),
        )
        indexed += 1
        changes[change] += 1
        warnings = []
        if item["status"] == "unknown":
            warnings.append("document_status_unknown")
        if not item["scopes"]:
            warnings.append("scope_missing")
        if item["status"] == "approved" and not approval_metadata_complete(item["approval"]):
            warnings.append("approval_metadata_incomplete")
        metadata_review_count += bool(warnings)
        if len(indexed_sample) < 20:
            indexed_sample.append({"document_id": item["document_id"], "kind": item["kind"],
                                   "file_path": relative, "declared_status": item["status"],
                                   "source_digest": item["source_digest"],
                                   "observed_revision": revision, "index_generation": generation,
                                   "change": change, "warnings": warnings})
    retired_count = sum(retirement_counts.values())
    next_action = (
        "review_source_and_metadata" if read_issue_count or issue_count or metadata_review_count
        else "query_existing_context" if indexed else
        "review_retirement_summary" if retired_count else "no_normative_change"
    )
    return {"schema_version": "normative-index/v1", "source_root": source_root,
            "documents_indexed": indexed, "documents_added": changes["added"],
            "documents_updated": changes["updated"], "documents_unchanged": changes["unchanged"],
            "documents_retired": retired_count,
            "retirement_counts": {key: value for key, value in sorted(retirement_counts.items()) if value},
            "retirement_sample": retirement_sample,
            "retirement_sample_truncated": retired_count > len(retirement_sample),
            "indexed_sample": indexed_sample, "indexed_sample_truncated": indexed > len(indexed_sample),
            "documents_requiring_metadata_review": metadata_review_count,
            "metadata_issues": issues, "metadata_issue_count": issue_count,
            "metadata_issues_truncated": issue_count > len(issues),
            "read_issues": read_issues, "read_issue_count": read_issue_count,
            "read_issues_truncated": read_issue_count > len(read_issues),
            "next_action": next_action, "approval_inferred": False}
