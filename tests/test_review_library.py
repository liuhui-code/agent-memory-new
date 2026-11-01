# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Controlled development fixtures for the human workbench; no business Memory."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.agent_memory_runtime.models import Project
from tools.agent_memory_runtime.review_actions import apply_action
from tools.agent_memory_runtime.review_library import ReviewError, browse, detail, open_archive, overview
from tools.agent_memory_runtime.storage import connect, ensure_initialized, resolve_project


class ReviewFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="memory-review-", dir="/private/tmp")
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        (root / "project").mkdir()
        self.project = resolve_project(str(root / "project"), str(root / "home"))
        ensure_initialized(self.project)

    def seed(self, count: int = 4) -> None:
        with connect(self.project) as conn:
            for index in range(count):
                stamp = f"2026-10-{1 + index % 28:02}T10:00:00+00:00"
                common = (self.project.project_id, stamp)
                conn.execute("INSERT INTO semantic_facts(project_id,fact,source,confidence,created_at,updated_at) "
                             "VALUES(?,?,?,?,?,?)", (common[0], f"中文事实 {index} 100%_准确 <script>alert(1)</script>",
                             "manual", .4 if index == 0 else .9, stamp, stamp))
                conn.execute("INSERT INTO episodes(project_id,task,summary,created_at) VALUES(?,?,?,?)",
                             (common[0], f"任务 {index}", "隔离样本", stamp))
                conn.execute("INSERT INTO reflections(project_id,task,lesson,created_at) VALUES(?,?,?,?)",
                             (common[0], f"反思 {index}", "先核对依据再审查", stamp))
                conn.execute("INSERT INTO code_files(project_id,file_path,summary,updated_at) VALUES(?,?,?,?)",
                             (common[0], f"src/file{index}.py", "文件摘要", stamp))
                conn.execute("INSERT INTO code_symbols(project_id,file_path,symbol,updated_at) VALUES(?,?,?,?)",
                             (common[0], f"src/file{index}.py", f"run{index}", stamp))
                conn.execute("INSERT INTO code_log_statements(project_id,file_path,message_template,updated_at) "
                             "VALUES(?,?,?,?)", (common[0], f"src/file{index}.py", "sample event", stamp))
            conn.commit()

    def selected(self, kind: str = "semantic", record_id: int = 1) -> dict:
        return {key: value for key, value in detail(self.project, kind, record_id).items()
                if key in {"kind", "id", "version"}}

    def action(self, action: str, records: list[dict] | None = None, **extra) -> dict:
        return apply_action(self.project, {"action": action, "records": records or [self.selected()], **extra})


class ReviewLibraryTests(ReviewFixture):
    def test_empty_archive_and_read_only_connection(self) -> None:
        self.assertEqual(0, overview(self.project)["total"])
        self.assertEqual([], browse(self.project, {})["items"])
        with open_archive(self.project) as conn:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("DELETE FROM projects")

    def test_missing_archive_does_not_initialize(self) -> None:
        absent = resolve_project(str(Path(self.temporary.name) / "absent"), str(Path(self.temporary.name) / "absent-home"))
        with self.assertRaisesRegex(ReviewError, "尚未初始化"):
            overview(absent)
        self.assertFalse(absent.memory_home.exists())

    def test_all_type_keyset_pages_have_no_duplicates_or_gaps(self) -> None:
        self.seed(36)
        for order in ("newest", "oldest"):
            seen, cursor, keys = [], "", []
            while True:
                page = browse(self.project, {"limit": "7", "cursor": cursor, "order": order})
                self.assertEqual(216, page["total"])
                self.assertLessEqual(len(page["items"]), 7)
                seen.extend((item["kind"], item["id"]) for item in page["items"])
                keys.extend((item["timestamp"], item["kind"], item["id"]) for item in page["items"])
                cursor = page["next_cursor"]
                if not cursor:
                    break
            self.assertEqual(216, len(set(seen)))
            self.assertEqual(216, len(seen))
            self.assertEqual(sorted(keys, reverse=order == "newest"), keys)

    def test_cursor_cannot_be_reused_for_different_filter(self) -> None:
        self.seed()
        cursor = browse(self.project, {"limit": "1"})["next_cursor"]
        with self.assertRaisesRegex(ReviewError, "分页"):
            browse(self.project, {"limit": "1", "q": "中文", "cursor": cursor})

    def test_search_chinese_and_literal_sql_wildcards(self) -> None:
        self.seed()
        self.assertEqual(4, browse(self.project, {"q": "中文事实"})["total"])
        self.assertEqual(4, browse(self.project, {"q": "100%_"})["total"])
        self.assertEqual(0, browse(self.project, {"q": "' OR 1=1 --"})["total"])
        self.assertEqual(4, browse(self.project, {"q": "src/file", "kind": "code-file"})["total"])

    def test_review_filters_and_aggregate_counts(self) -> None:
        self.seed()
        self.assertEqual(12, overview(self.project)["pending"])
        self.assertEqual(1, browse(self.project, {"view": "low-confidence"})["total"])
        self.action("review")
        self.assertEqual(11, browse(self.project, {"view": "pending"})["total"])
        self.assertEqual(1, browse(self.project, {"view": "reviewed"})["total"])
        self.action("archive", [self.selected("episode")])
        self.assertEqual(23, browse(self.project, {})["total"])
        self.assertEqual(1, browse(self.project, {"view": "archived"})["total"])
        self.assertEqual({"total": 24, "pending": 10, "archived": 1},
                         {key: overview(self.project)[key] for key in ("total", "pending", "archived")})

    def test_status_filter_and_project_isolation(self) -> None:
        self.seed()
        with connect(self.project) as conn:
            conn.execute("UPDATE semantic_facts SET status='stale' WHERE id=1")
            conn.execute("INSERT INTO semantic_facts(project_id,fact,source,created_at,updated_at) "
                         "VALUES('another-project','foreign','manual','2026','2026')")
            conn.commit()
        self.assertEqual(1, browse(self.project, {"status": "stale"})["total"])
        self.assertEqual(24, overview(self.project)["total"])
        with self.assertRaises(ReviewError):
            detail(self.project, "semantic", 5)

    def test_bounds_and_invalid_inputs(self) -> None:
        for params in ({"limit": "101"}, {"limit": "-1"}, {"limit": "nan"}, {"q": "字" * 201},
                       {"kind": "projects"}, {"view": "unbounded"}, {"cursor": "!not-valid!"}, {"order": "sql"}):
            with self.subTest(params=params), self.assertRaises(ReviewError):
                browse(self.project, params)

    def test_long_detail_is_bounded_but_keeps_full_record_version(self) -> None:
        self.seed()
        with connect(self.project) as conn:
            conn.execute("UPDATE semantic_facts SET fact=? WHERE id=1", ("长" * 70000,))
            conn.commit()
        record = detail(self.project, "semantic", 1)
        self.assertEqual(["fact"], record["truncated_fields"])
        self.assertEqual(64000, len(record["fields"]["fact"]))
        self.assertEqual(record["version"], browse(self.project, {"q": "长"})["items"][0]["version"])
        self.action("archive", [self.selected()])


class ReviewActionTests(ReviewFixture):
    def setUp(self) -> None:
        super().setUp()
        self.seed()

    def test_archive_restore_preserves_body_and_marks_review(self) -> None:
        before = detail(self.project, "semantic", 1)
        self.action("archive")
        archived = detail(self.project, "semantic", 1)
        self.assertEqual("archived", archived["status"])
        self.assertTrue(archived["reviewed_at"])
        self.action("restore")
        restored = detail(self.project, "semantic", 1)
        self.assertEqual("active", restored["status"])
        self.assertEqual(before["fields"]["fact"], restored["fields"]["fact"])

    def test_batch_conflict_rolls_back_every_selected_record(self) -> None:
        selected = [self.selected(), self.selected("episode")]
        with connect(self.project) as conn:
            conn.execute("UPDATE episodes SET summary='concurrent Agent write' WHERE id=1")
            conn.commit()
        with self.assertRaisesRegex(ReviewError, "已被其他操作更新"):
            self.action("archive", selected)
        self.assertEqual("active", detail(self.project, "semantic", 1)["status"])
        self.assertIsNone(detail(self.project, "semantic", 1)["reviewed_at"])

    def test_read_only_types_and_duplicates_are_rejected(self) -> None:
        for records in ([self.selected("code-file")], [self.selected(), self.selected()]):
            with self.subTest(records=records), self.assertRaises(ReviewError):
                self.action("archive", records)
        self.assertEqual(24, overview(self.project)["total"])

    def test_delete_requires_archive_and_exact_confirmation(self) -> None:
        with self.assertRaisesRegex(ReviewError, "请输入"):
            self.action("delete")
        with self.assertRaisesRegex(ReviewError, "仅已归档"):
            self.action("delete", confirmation="永久删除")
        self.assertFalse((self.project.runtime_dir / "review-backups").exists())

    def test_delete_retains_predelete_backup_and_cleans_fts_and_edges(self) -> None:
        with connect(self.project) as conn:
            conn.execute("INSERT INTO memory_edges(project_id,source_type,source_id,relation,target_type,target_id,created_at) "
                         "VALUES(?, 'semantic_fact', 1, 'sample', 'episode', 1, '2026')", (self.project.project_id,))
            conn.execute("UPDATE project_counters SET value=1 WHERE project_id=? AND counter_name='memory_edges'",
                         (self.project.project_id,))
            conn.commit()
        self.action("archive")
        result = self.action("delete", confirmation="永久删除")
        backup = Path(result["backup_path"])
        self.assertTrue(backup.is_file())
        self.assertEqual(0o600, backup.stat().st_mode & 0o777)
        with sqlite3.connect(backup) as conn:
            self.assertEqual("archived", conn.execute("SELECT status FROM semantic_facts WHERE id=1").fetchone()[0])
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM memory_edges").fetchone()[0])
        with open_archive(self.project) as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM semantic_fact_fts WHERE rowid=1").fetchone()[0])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM memory_edges").fetchone()[0])
            self.assertEqual(0, conn.execute("SELECT value FROM project_counters WHERE counter_name='memory_edges'").fetchone()[0])
        with self.assertRaises(ReviewError):
            detail(self.project, "semantic", 1)

    def test_backup_failure_prevents_deletion(self) -> None:
        self.action("archive")
        with patch("tools.agent_memory_runtime.review_actions.backup_archive", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.action("delete", confirmation="永久删除")
        self.assertEqual("archived", detail(self.project, "semantic", 1)["status"])

    def test_delete_backup_is_standalone_readonly_without_wal_sidecars(self) -> None:
        self.action("archive")
        backup = Path(self.action("delete", confirmation="永久删除")["backup_path"])
        self.assertEqual([backup.name], sorted(path.name for path in backup.parent.iterdir()))
        self.assertEqual(b"\x01\x01", backup.read_bytes()[18:20])
        with sqlite3.connect(backup.as_uri() + "?mode=ro", uri=True) as conn:
            self.assertEqual("ok", conn.execute("PRAGMA quick_check").fetchone()[0])
            self.assertEqual("archived", conn.execute("SELECT status FROM semantic_facts WHERE id=1").fetchone()[0])

    def test_invalid_batch_is_rejected_without_partial_write(self) -> None:
        for payload in ({"action": "sql", "records": [self.selected()]},
                        {"action": "archive", "records": []},
                        {"action": "archive", "records": [self.selected()] * 101},
                        {"action": "archive", "records": [{"kind": "semantic", "id": True, "version": "a" * 64}]}):
            with self.subTest(payload=payload), self.assertRaises(ReviewError):
                apply_action(self.project, payload)
        self.assertEqual("active", detail(self.project, "semantic", 1)["status"])


if __name__ == "__main__":
    unittest.main()
