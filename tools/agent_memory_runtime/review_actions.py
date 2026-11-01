# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Explicit, atomic human actions on ordinary Memory records."""

from __future__ import annotations

import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from .graph_quality_snapshot import bump_graph_revision
from .models import Project
from .review_library import EDITABLE, KINDS, ReviewError, open_archive, record_row, version
from .storage import now_iso
from .storage_project_counters import MEMORY_EDGE_COUNTER, adjust_project_counter


def backup_archive(project: Project) -> Path:
    """Caller holds BEGIN IMMEDIATE; a separate reader copies the pre-delete state."""
    directory = project.runtime_dir / "review-backups"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / f"before-delete-{uuid.uuid4().hex}.db"
    partial = target.with_suffix(".partial")
    fd = os.open(partial, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    deadline = time.monotonic() + 30

    def progress(status: int, remaining: int, total: int) -> None:
        if time.monotonic() > deadline:
            raise ReviewError("备份超过 30 秒，未删除任何记忆。请缩小数据库后重试。", 503)

    try:
        with open_archive(project) as source:
            destination = sqlite3.connect(partial)
            try:
                source.backup(destination, pages=256, progress=progress)
                # backup() copies the source's WAL header. Publish a self-contained
                # rollback-journal image, not a renamed DB with old-name sidecars.
                if destination.execute("PRAGMA journal_mode=DELETE").fetchone()[0] != "delete":
                    raise ReviewError("备份无法转换为独立数据库，未删除任何记忆。", 503)
                if destination.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ReviewError("备份完整性检查失败，未删除任何记忆。", 503)
            finally:
                destination.close()
        with partial.open("rb") as stream:
            os.fsync(stream.fileno())
        partial.replace(target)
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return target
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    finally:
        for suffix in ("-wal", "-shm", "-journal"):
            Path(str(partial) + suffix).unlink(missing_ok=True)


def apply_action(project: Project, payload: dict[str, Any]) -> dict[str, Any]:
    action, records = payload.get("action"), payload.get("records")
    if action not in {"review", "archive", "restore", "delete"}:
        raise ReviewError("不支持的审查操作。")
    if not isinstance(records, list) or not 1 <= len(records) <= 100:
        raise ReviewError("每次请选择 1–100 条记忆。")
    keys = set()
    for item in records:
        if (not isinstance(item, dict) or item.get("kind") not in EDITABLE
                or type(item.get("id")) is not int or item["id"] < 1
                or not isinstance(item.get("version"), str) or len(item["version"]) != 64):
            raise ReviewError("仅事实、经历、反思支持人工操作，并须携带当前记录版本。")
        key = (item["kind"], item["id"])
        if key in keys:
            raise ReviewError("批次包含重复记录。")
        keys.add(key)
    if action == "delete" and payload.get("confirmation") != "永久删除":
        raise ReviewError("请输入“永久删除”以确认。")
    backup = None
    removed_edges = 0
    with open_archive(project, write=True) as conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = []
        for item in records:
            row = record_row(conn, project, item["kind"], item["id"])
            if version(row) != item["version"]:
                raise ReviewError("记录已被其他操作更新。本批次未执行，请刷新后重新审查。", 409)
            status = row.get("status") or "active"
            if action in {"delete", "restore"} and status != "archived":
                raise ReviewError("仅已归档记忆可以恢复或永久删除。", 409)
            if action == "review" and status not in {"active", "stale"}:
                raise ReviewError("仅有效或过期记忆可以标记已审查。", 409)
            if action == "archive" and status == "archived":
                raise ReviewError("记录已经归档，请刷新列表。", 409)
            rows.append((item, row))
        if action == "delete":
            backup = backup_archive(project)
        for item, row in rows:
            table = KINDS[item["kind"]][0]
            if action == "delete":
                aliases = [item["kind"]]
                if item["kind"] == "semantic":
                    aliases.append("semantic_fact")
                slots = ",".join("?" for _ in aliases)
                removed_edges += conn.execute(
                    f"DELETE FROM memory_edges WHERE project_id = ? AND "
                    f"((source_type IN ({slots}) AND source_id = ?) OR "
                    f"(target_type IN ({slots}) AND target_id = ?))",
                    [project.project_id, *aliases, item["id"], *aliases, item["id"]]).rowcount
                conn.execute(f"DELETE FROM {table} WHERE project_id = ? AND id = ?",
                             (project.project_id, item["id"]))
            else:
                assignments, values = ["reviewed_at = ?"], [now_iso()]
                if action in {"archive", "restore"}:
                    assignments.append("status = ?")
                    values.append("archived" if action == "archive" else "active")
                if action == "restore" and item["kind"] != "episode":
                    assignments.extend(["is_stale = 0", "stale_reason = NULL"])
                conn.execute(f"UPDATE {table} SET {', '.join(assignments)} WHERE project_id = ? AND id = ?",
                             [*values, project.project_id, item["id"]])
        if removed_edges:
            adjust_project_counter(conn, project.project_id, MEMORY_EDGE_COUNTER, -removed_edges)
            bump_graph_revision(conn, project.project_id)
        conn.commit()
    return {"action": action, "changed": len(records), "backup_path": str(backup) if backup else None,
            "removed_edges": removed_edges, "vault_refresh_required": action != "review"}
