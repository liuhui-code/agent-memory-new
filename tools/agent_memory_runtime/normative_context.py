# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from .models import Project
from .normative_documents import (
    approval_metadata_complete, document_git_states, observe_document_source,
)
from .normative_relationships import compact_document_links, inspect_cached_document_links
from .storage import connect
from .text import bounded_query_tokens


CANDIDATE_LIMIT = 12
FULL_REF_LIMIT = 6
HISTORICAL_STATUSES = {"superseded", "withdrawn", "rejected"}


def scope_state(scopes: list[str], anchors: list[str]) -> str:
    if not scopes:
        return "missing"
    if any(pattern in {".", "*", "**"} for pattern in scopes):
        return "project_wide"
    if not anchors:
        return "requires_agent_confirmation"
    return "matched" if any(
        fnmatchcase(path, pattern) or path == pattern.rstrip("/")
        or path.startswith(pattern.rstrip("/") + "/")
        for path in anchors for pattern in scopes
    ) else "outside_selected_anchors"


def document_excerpt(row: dict[str, Any], tokens: list[str]) -> dict[str, Any]:
    lines = row["body"].split("\n")
    start = next((i for i, line in enumerate(lines)
                  if any(token in line.casefold() for token in tokens)), 0)
    selected = "\n".join(lines[start:start + 8])
    text = selected[:500]
    start_line = row["body_start_line"] + start
    return {"text": text, "start_line": start_line,
            "end_line": start_line + text.count("\n"),
            "truncated": len(selected) > 500 or start > 0 or start + 8 < len(lines)}


def collect_normative_context(
    project: Project, query: str, anchors: list[str] | None = None,
) -> dict[str, Any] | None:
    tokens = bounded_query_tokens(query, 12)
    if not tokens or not project.db_path.is_file():
        return None
    expression = " OR ".join('"' + token.replace('"', '""') + '"' for token in tokens)
    with connect(project) as conn:
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='normative_documents'"
        ).fetchone():
            return None
        rows = [dict(row) for row in conn.execute(
            """SELECT d.* FROM normative_document_fts
               JOIN normative_documents d ON d.id = normative_document_fts.rowid
               WHERE normative_document_fts MATCH ? AND d.project_id = ?
               ORDER BY bm25(normative_document_fts), d.source_root, d.file_path LIMIT ?""",
            (expression, project.project_id, CANDIDATE_LIMIT + 1),
        ).fetchall()]
        if not rows:
            return None
        truncated = len(rows) > CANDIDATE_LIMIT
        rows = rows[:CANDIDATE_LIMIT]
        for row in rows:
            row["cached_links"] = inspect_cached_document_links(conn, project.project_id, row)
    by_root: dict[str, list[str]] = {}
    for row in rows:
        by_root.setdefault(row["source_root"], []).append(row["file_path"])
    git_states = {root: document_git_states(Path(root), paths)
                  for root, paths in by_root.items()}
    refs: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for row in rows:
        approval = json.loads(row["approval"])
        scopes = json.loads(row["scopes"])
        freshness, observed_digest = observe_document_source(row)
        git_state = git_states[row["source_root"]][row["file_path"]]
        # Anchors are relative to the query project, not to an arbitrary learned tree.
        same_source = Path(row["source_root"]).resolve() == project.root.resolve()
        scope = scope_state(scopes, (anchors or []) if same_source else [])
        warnings = []
        if freshness != "current":
            warnings.append("document_" + freshness)
        if git_state != "committed":
            warnings.append("document_git_" + git_state)
        if row["status"] == "approved" and not approval_metadata_complete(approval):
            warnings.append("approval_metadata_incomplete")
        if row["status"] == "unknown":
            warnings.append("document_status_unknown")
        if scope not in {"project_wide", "matched"}:
            warnings.append("scope_" + scope)
        if not same_source:
            warnings.append("source_root_requires_agent_confirmation")
        links = row["cached_links"]
        warnings.extend(links["warnings"])
        historical = row["status"] in HISTORICAL_STATUSES or bool(row["superseded_by"])
        allowed_use = (
            "historical_reference_only" if historical else
            "draft_hypothesis_only" if row["status"] == "draft" else
            "expected_contract_candidate" if row["status"] == "approved" and not warnings else
            "requires_source_and_approval_review"
        )
        ref = {
            "record_id": row["id"], "document_id": row["document_id"],
            "kind": row["kind"], "title": row["title"], "status": row["status"],
            "scopes": scopes, "scope_state": scope,
            "scope_basis": "document_source_root", "approval": approval,
            "approval_verification": "declared_metadata_requires_agent_review",
            "allowed_use": allowed_use,
            "authority_ceiling": (
                "confirmed_project_constraint_or_correction"
                if row["status"] == "approved" and not historical else "advisory_only"
            ),
            "supersedes": row["supersedes"], "superseded_by": row["superseded_by"],
            "replacement_refs": links["reverse_refs"], "warnings": warnings,
            "source": {
                "root": row["source_root"], "file_path": row["file_path"],
                "digest": row["source_digest"], "observed_digest": observed_digest,
                "revision": row["source_revision"],
                "index_generation": row["index_generation"],
                "revision_binding": "observed_repository_head",
                "freshness": freshness, "git_state": git_state,
                "matches_query_project": same_source,
            },
        }
        if links["forward_links"] or links["reverse_refs"]:
            ref["replacement_lookup"] = links
        if freshness == "current":
            ref["excerpt"] = document_excerpt(row, tokens)
        refs.append(ref)
        gaps.extend({"record_id": row["id"], "document_id": row["document_id"],
                     "source_root": row["source_root"], "file_path": row["file_path"],
                     "reason": reason}
                    for reason in warnings)
    refs.sort(key=lambda ref: (ref["allowed_use"] != "expected_contract_candidate",
                               ref["allowed_use"] == "historical_reference_only"))
    returned = refs[:FULL_REF_LIMIT]
    return {
        "schema_version": "normative-context/v1", "document_refs": returned,
        "evidence_gaps": gaps[:12], "examined_document_count": len(refs),
        "candidate_limit_exceeded": truncated,
        "omitted_document_count": len(refs) - len(returned),
        "omitted_evidence_gap_count": max(0, len(gaps) - 12),
        "truncated": truncated or len(refs) > len(returned) or len(gaps) > 12
        or any(ref.get("excerpt", {}).get("truncated") for ref in returned),
        "approval_review_required": True,
        "role_boundary": "Agent checks approval, scope and expected-versus-actual behavior; Runtime does not adjudicate.",
    }


def compact_normative_context(value: dict[str, Any]) -> dict[str, Any]:
    refs = []
    for original in value["document_refs"][:2]:
        ref = {key: original[key] for key in (
            "record_id", "document_id", "kind", "status", "scopes", "scope_state",
            "scope_basis", "approval",
            "approval_verification", "allowed_use", "source", "warnings",
            "supersedes", "superseded_by", "replacement_refs",
        ) if original.get(key) not in (None, "", [], {})}
        if original.get("replacement_lookup"):
            ref["replacement_lookup"] = compact_document_links(original["replacement_lookup"])
        if original.get("replacement_refs"):
            ref["replacement_refs"] = [{key: target[key] for key in (
                "record_id", "document_id", "file_path", "declared_status",
                "source_checked", "approval_verified",
            ) if key in target} for target in original["replacement_refs"]]
        if original.get("excerpt"):
            excerpt = original["excerpt"]
            text = excerpt["text"][:160]
            ref["excerpt"] = {
                **excerpt, "text": text,
                "end_line": excerpt["start_line"] + text.count("\n"),
                "truncated": bool(excerpt.get("truncated")) or len(excerpt["text"]) > 160,
            }
        refs.append(ref)
    gaps = [{key: gap[key] for key in ("record_id", "document_id", "reason") if key in gap}
            for gap in value["evidence_gaps"][:3]]
    return {"schema_version": value["schema_version"], "document_refs": refs,
            "evidence_gaps": gaps,
            "examined_document_count": value.get("examined_document_count", len(value["document_refs"])),
            "candidate_limit_exceeded": bool(value.get("candidate_limit_exceeded")),
            "omitted_document_count": value.get("omitted_document_count", 0)
            + len(value["document_refs"]) - len(refs),
            "omitted_evidence_gap_count": value.get("omitted_evidence_gap_count", 0)
            + len(value["evidence_gaps"]) - len(gaps),
            "approval_review_required": True,
            "truncated": value["truncated"] or len(value["document_refs"]) > 2
            or len(value["evidence_gaps"]) > 3
            or any(ref.get("excerpt", {}).get("truncated") for ref in refs)}


def reduce_normative_context(value: dict[str, Any] | None) -> bool:
    if not value:
        return False
    refs = value.get("document_refs", [])
    for ref in reversed(refs):
        if ref.pop("excerpt", None) is not None:
            value["truncated"] = True
            return True
    if refs:
        value["document_refs"] = refs[:-1]
        value["omitted_document_count"] = value.get("omitted_document_count", 0) + 1
        value["truncated"] = True
        return True
    if value.get("evidence_gaps"):
        value["omitted_evidence_gap_count"] = (
            value.get("omitted_evidence_gap_count", 0) + len(value["evidence_gaps"])
        )
        value["evidence_gaps"] = []
        value["truncated"] = True
        return True
    return False
