# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Bounded human browsing, separate from Agent retrieval and ranking."""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from .models import Project

# kind: (table, title, searchable fields, timestamp)
KINDS = {
    "semantic": ("semantic_facts", "fact", ("fact", "source", "category", "scope", "evidence"), "created_at"),
    "reflection": ("reflections", "task", ("task", "summary", "lesson", "future_rule", "evidence"), "created_at"),
    "episode": ("episodes", "task", ("task", "summary", "outcome", "files_touched"), "created_at"),
    "code-file": ("code_files", "file_path", ("file_path", "summary", "business_summary", "business_terms"), "updated_at"),
    "code-symbol": ("code_symbols", "symbol", ("file_path", "symbol", "summary", "business_summary"), "updated_at"),
    "code-log": ("code_log_statements", "message_template", ("file_path", "message_template", "raw_statement", "function"), "updated_at"),
}
EDITABLE = {"semantic", "reflection", "episode"}
STATUSES = {"active", "stale", "merged", "rejected", "archived"}
MAX_PAGE = 100
MAX_FIELD = 64000


class ReviewError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


@contextmanager
def open_archive(project: Project, *, write: bool = False) -> Iterator[sqlite3.Connection]:
    if not project.db_path.is_file():
        raise ReviewError("该项目尚未初始化记忆库，请先运行 init。", 404)
    conn = sqlite3.connect(project.db_path.as_uri() + ("?mode=rw" if write else "?mode=ro"),
                           uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def version(row: dict[str, Any]) -> str:
    raw = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record_row(conn: sqlite3.Connection, project: Project, kind: str, record_id: int) -> dict[str, Any]:
    if kind not in KINDS or type(record_id) is not int or record_id < 1:
        raise ReviewError("无效的记忆类型或编号。")
    row = conn.execute(f"SELECT * FROM {KINDS[kind][0]} WHERE project_id = ? AND id = ?",
                       (project.project_id, record_id)).fetchone()
    if row is None:
        raise ReviewError("记录已不存在，请刷新列表。", 404)
    return dict(row)


def summary(kind: str, row: dict[str, Any]) -> dict[str, Any]:
    _, title, _, stamp = KINDS[kind]
    body = row.get("lesson") or row.get("summary") or row.get("business_summary") or row.get("raw_statement") or row.get(title) or ""
    return {
        "kind": kind, "id": row["id"], "title": str(row.get(title) or "未命名记忆")[:180],
        "preview": str(body)[:260], "timestamp": row.get(stamp) or "", "version": version(row),
        "status": row.get("status") or ("active" if kind in EDITABLE else "indexed"),
        "confidence": row.get("confidence"), "reviewed_at": row.get("reviewed_at"),
        "source": str(row.get("source") or row.get("file_path") or row.get("scope") or "")[:240],
        "editable": kind in EDITABLE, "is_stale": bool(row.get("is_stale")),
    }


def detail(project: Project, kind: str, record_id: int) -> dict[str, Any]:
    with open_archive(project) as conn:
        row = record_row(conn, project, kind, record_id)
    truncated = [key for key, value in row.items() if isinstance(value, str) and len(value) > MAX_FIELD]
    fields = {key: (value[:MAX_FIELD] if key in truncated else value)
              for key, value in row.items() if key != "project_id"}
    return {**summary(kind, row), "fields": fields, "truncated_fields": truncated}


def overview(project: Project) -> dict[str, Any]:
    counts, pending, archived = {}, 0, 0
    with open_archive(project) as conn:
        conn.execute("BEGIN")
        for kind, (table, _, _, _) in KINDS.items():
            counts[kind] = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE project_id = ?",
                                        (project.project_id,)).fetchone()[0]
            if kind in EDITABLE:
                row = conn.execute(
                    f"SELECT SUM(CASE WHEN COALESCE(status,'active') IN ('active','stale') "
                    "AND COALESCE(reviewed_at,'') = '' THEN 1 ELSE 0 END), "
                    "SUM(CASE WHEN status = 'archived' THEN 1 ELSE 0 END) "
                    f"FROM {table} WHERE project_id = ?", (project.project_id,)).fetchone()
                pending += row[0] or 0
                archived += row[1] or 0
    return {"project_name": project.project_name, "project_path": str(project.root),
            "project_id": project.project_id, "db_path": str(project.db_path),
            "counts": counts, "total": sum(counts.values()), "pending": pending, "archived": archived}


def _cursor(raw: str, binding: str) -> list[Any] | None:
    if not raw:
        return None
    try:
        if len(raw) > 1000:
            raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(raw.encode("ascii")))
        anchor = payload["anchor"]
        if (payload["binding"] != binding or not isinstance(anchor, list) or len(anchor) != 3
                or not isinstance(anchor[0], str) or anchor[1] not in KINDS
                or type(anchor[2]) is not int or anchor[2] < 1):
            raise ValueError()
        return anchor
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise ReviewError("分页位置已失效，请回到第一页。") from None


def browse(project: Project, params: dict[str, str]) -> dict[str, Any]:
    kind, query, view = params.get("kind", "all"), params.get("q", "").strip(), params.get("view", "library")
    status, order = params.get("status", "all"), params.get("order", "newest")
    try:
        size = int(params.get("limit", "30"))
    except (ValueError, TypeError):
        raise ReviewError("每页数量必须为整数。") from None
    if (kind not in {"all", *KINDS} or view not in {"library", "pending", "archived", "low-confidence", "reviewed"}
            or status not in {"all", *STATUSES} or order not in {"newest", "oldest"}
            or not 1 <= size <= MAX_PAGE or len(query) > 200):
        raise ReviewError("无效的筛选条件（搜索限 200 字，每页 1–100 条）。")
    binding = version({"kind": kind, "q": query, "view": view, "status": status, "order": order, "limit": size})
    anchor = _cursor(params.get("cursor", ""), binding)
    direction, compare = ("DESC", "<") if order == "newest" else ("ASC", ">")
    result, total = [], 0
    with open_archive(project) as conn:
        conn.execute("BEGIN")
        for item_kind in (KINDS if kind == "all" else [kind]):
            table, _, fields, stamp = KINDS[item_kind]
            editable = item_kind in EDITABLE
            if not editable and (view != "library" or status != "all"):
                continue
            where, values = ["project_id = ?"], [project.project_id]
            if editable:
                where.append("COALESCE(status,'active') = 'archived'" if view == "archived"
                             else "COALESCE(status,'active') != 'archived'")
                if status != "all":
                    where.append("COALESCE(status,'active') = ?")
                    values.append(status)
                if view in {"pending", "reviewed", "low-confidence"}:
                    where.append("COALESCE(status,'active') IN ('active','stale')")
                if view in {"pending", "reviewed"}:
                    where.append("COALESCE(reviewed_at,'') " + ("= ''" if view == "pending" else "!= ''"))
                if view == "low-confidence":
                    if item_kind == "episode":
                        continue
                    where.append("confidence < 0.6")
            if query:
                escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                where.append("(" + " OR ".join(f"COALESCE({field},'') LIKE ? ESCAPE '\\'" for field in fields) + ")")
                values.extend([f"%{escaped}%"] * len(fields))
            predicate = " AND ".join(where)
            total += conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {predicate}", values).fetchone()[0]
            if anchor:
                where.append(f"(COALESCE({stamp},''), ?, id) {compare} (?, ?, ?)")
                values.extend([item_kind, *anchor])
            rows = conn.execute(f"SELECT * FROM {table} WHERE {' AND '.join(where)} "
                                f"ORDER BY {stamp} {direction}, id {direction} LIMIT ?", [*values, size + 1]).fetchall()
            result.extend(summary(item_kind, dict(row)) for row in rows)
    result.sort(key=lambda row: (row["timestamp"], row["kind"], row["id"]), reverse=order == "newest")
    has_more = len(result) > size
    result = result[:size]
    cursor = None
    if has_more:
        last = result[-1]
        cursor = base64.urlsafe_b64encode(json.dumps({"binding": binding,
            "anchor": [last["timestamp"], last["kind"], last["id"]]}).encode()).decode("ascii")
    return {"items": result, "total": total, "next_cursor": cursor, "limit": size}
