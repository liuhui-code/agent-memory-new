# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from .scope_changes import GitChangeError, git_changed_paths, git_head, git_tracked_paths


MAX_DOCUMENT_BYTES = 65536
MAX_METADATA_LINES = 48
MAX_METADATA_BYTES = 4096
DOCUMENT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
STATUSES = {
    "adr": {"proposed": "draft", "accepted": "approved", "superseded": "superseded",
            "deprecated": "withdrawn", "rejected": "rejected"},
    "feature-spec": {"draft": "draft", "approved": "approved", "superseded": "superseded",
                     "withdrawn": "withdrawn", "rejected": "rejected"},
}


def _document_lines(raw: bytes, *, errors: str = "strict") -> list[str]:
    """Use physical LF/CRLF lines, stripping a single leading UTF-8 BOM."""
    lines = raw.decode("utf-8-sig", errors=errors).split("\n")
    for index in range(len(lines) - 1):
        if lines[index].endswith("\r"):
            lines[index] = lines[index][:-1]
    if lines[-1] == "":
        lines.pop()
    return lines


def _has_normative_marker(lines: list[str]) -> bool:
    if not lines or lines[0] != "---":
        return False
    limit = min(len(lines), MAX_METADATA_LINES + 1)
    end = next((i for i in range(1, limit) if lines[i] == "---"), limit)
    return any(
        line.startswith("type:") and line.partition(":")[2].strip().strip("\"'")
        in STATUSES for line in lines[1:end]
    )


def read_document_bytes(root: Path, relative: str) -> bytes:
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    if not path.is_file():
        raise FileNotFoundError(relative)
    with path.open("rb") as handle:
        raw = handle.read(MAX_DOCUMENT_BYTES + 1)
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ValueError("document exceeds 64 KiB")
    return raw


def observe_document_source(row: dict[str, Any]) -> tuple[str, str | None]:
    """Return indexed-byte freshness and the digest observed by one bounded read."""
    try:
        raw = read_document_bytes(Path(row["source_root"]), row["file_path"])
    except FileNotFoundError:
        return "missing", None
    except (OSError, ValueError):
        return "unverified", None
    observed_digest = hashlib.sha256(raw).hexdigest()
    freshness = "current" if observed_digest == row["source_digest"] else "changed"
    return freshness, observed_digest


def read_normative_document(root: Path, relative: str) -> dict[str, Any] | None:
    """Recognize and parse a selected document through one bounded file handle."""
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    with path.open("rb") as handle:
        prefix = handle.read(MAX_METADATA_BYTES)
        header = _document_lines(prefix, errors="replace")
        if len(prefix) == MAX_METADATA_BYTES and not prefix.endswith(b"\n"):
            # A line cut at the byte boundary cannot establish an explicit marker.
            header = header[:-1]
        if not _has_normative_marker(header):
            return None
        raw = prefix + handle.read(MAX_DOCUMENT_BYTES + 1 - len(prefix))
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ValueError("document exceeds 64 KiB")
    return parse_normative_document(raw)


def parse_normative_document(raw: bytes) -> dict[str, Any] | None:
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ValueError("document exceeds 64 KiB")
    lines = _document_lines(raw)
    if not lines or lines[0] != "---":
        return None
    end = next((i for i in range(1, min(len(lines), MAX_METADATA_LINES + 1))
                if lines[i] == "---"), None)
    if end is None:
        raise ValueError("frontmatter must close within 48 lines after the opening delimiter")
    if not _has_normative_marker(lines[:end + 1]):
        return None
    # Include BOM, delimiters and actual line endings through the closing line.
    header_bytes = min(len(raw), sum(len(line) + 1 for line in raw.split(b"\n")[:end + 1]))
    if header_bytes > MAX_METADATA_BYTES:
        raise ValueError("normative frontmatter exceeds 4 KiB")
    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([a-z][a-z_]*):\s*(.*)", line)
        if not match or match[1] in metadata:
            raise ValueError("normative frontmatter requires unique flat scalar keys")
        value = match[2].strip()
        if value.startswith('"'):
            value = json.loads(value)
            if not isinstance(value, str):
                raise ValueError("quoted metadata must be a string")
        elif len(value) >= 2 and value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
        metadata[match[1]] = value
    kind = metadata["type"]
    if kind not in STATUSES:
        raise ValueError("normative type must be adr or feature-spec")
    document_id = metadata.get("id", "")
    if not DOCUMENT_ID.fullmatch(document_id):
        raise ValueError("normative document requires a stable id")
    for key in ("supersedes", "superseded_by"):
        if metadata.get(key) and not DOCUMENT_ID.fullmatch(metadata[key]):
            raise ValueError(f"{key} must name one document id")
        if metadata.get(key) == document_id:
            raise ValueError("a document cannot replace itself")
    scope = metadata.get("scope", "")
    scopes = json.loads(scope) if scope.startswith("[") else [scope] if scope else []
    if not isinstance(scopes, list) or len(scopes) > 12:
        raise ValueError("scope must be a scalar or a JSON array of at most 12 paths")
    for pattern in scopes:
        if (not isinstance(pattern, str) or not pattern or len(pattern) > 240
                or Path(pattern).is_absolute() or ".." in Path(pattern).parts):
            raise ValueError("scope must contain repository-relative paths or globs")
    body_lines = lines[end + 1:]
    if not any(line.strip() for line in body_lines):
        raise ValueError("normative document requires source content")
    title = next((line[2:].strip() for line in body_lines if line.startswith("# ")),
                 document_id)
    approval = {key: metadata.get(key, "")
                for key in ("owner", "approved_by", "approved_at", "approval_ref")}
    if any(len(value) > 512 for value in approval.values()):
        raise ValueError("approval metadata fields exceed 512 characters")
    return {
        "document_id": document_id, "kind": kind, "title": title[:240],
        "status": STATUSES[kind].get(metadata.get("status", ""), "unknown"),
        "scopes": scopes, "approval": approval,
        "supersedes": metadata.get("supersedes", ""),
        "superseded_by": metadata.get("superseded_by", ""),
        "body": "\n".join(body_lines), "body_start_line": end + 2,
        "source_digest": hashlib.sha256(raw).hexdigest(),
    }


def approval_metadata_complete(approval: dict[str, Any]) -> bool:
    if not all(str(approval.get(key) or "").strip()
               for key in ("owner", "approved_by", "approved_at", "approval_ref")):
        return False
    approved_at = str(approval["approved_at"])
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", approved_at):
        return False
    try:
        date.fromisoformat(approved_at)
    except ValueError:
        return False
    return True


def document_git_states(root: Path, paths: list[str]) -> dict[str, str]:
    """Check only selected paths, never the complete worktree."""
    revision = git_head(root)
    if not revision:
        return dict.fromkeys(paths, "git_unverified")
    pathspecs = [f":(literal){path}" for path in paths]
    try:
        tracked = git_tracked_paths(root, pathspecs)
        changed = git_changed_paths(root, revision, pathspecs)
    except GitChangeError:
        return dict.fromkeys(paths, "git_unverified")
    return {path: "untracked" if path not in tracked else "modified" if path in changed
            else "committed" for path in paths}
