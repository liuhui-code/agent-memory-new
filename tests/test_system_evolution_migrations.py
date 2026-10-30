# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Controlled schema upgrades/downgrades; never a user's existing archive."""

import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_system_evolution import synthetic_report
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.system_evolution_migrations import migrate_governance
from tools.agent_memory_runtime import system_evolution_migrations as migrations


class SystemEvolutionMigrationTests(AgentMemoryTestBase):
    def command(self, root: Path, *args: str) -> dict:
        return json.loads(self.run_memory(root, *args, "--json").stdout)

    def fixture(self, directory: str) -> tuple[Path, dict]:
        root = Path(directory) / "project"
        root.mkdir()
        self.run_memory(root, "init")
        saved = self.command(root, "reflect-system", "--review-key", "schema-fixture", "--payload", json.dumps(synthetic_report()))
        return root, saved

    def test_upgrade_preview_backup_foreign_keys_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, saved = self.fixture(directory)
            backup = Path(directory) / "before-v2.db"
            args = ("maintain-system-migrate", "--target-version", "system-evolution-v2", "--backup-file", str(backup))
            self.assertFalse(self.command(root, *args)["migration_performed"])
            self.assertFalse(backup.exists())
            result = self.command(root, *args, "--execute")
            self.assertTrue(result["migration_performed"])
            self.assertEqual(1, result["proposal_rows_preserved"])
            with closing(sqlite3.connect(backup)) as conn:
                self.assertEqual("system-evolution-v1", conn.execute("SELECT version FROM runtime_schema_versions WHERE component='system_evolution'").fetchone()[0])
            with closing(sqlite3.connect(self.project_memory_dir(root) / "memory.db")) as conn:
                self.assertEqual([], conn.execute("PRAGMA foreign_key_check").fetchall())
                self.assertEqual(saved["proposal_id"], conn.execute("SELECT proposal_id FROM system_change_events").fetchone()[0])
            self.assertTrue(self.command(root, *args, "--execute")["reused"])

    def test_supported_downgrade_preserves_post_upgrade_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, saved = self.fixture(directory)
            self.command(root, "maintain-system-migrate", "--target-version", "system-evolution-v2",
                         "--backup-file", str(Path(directory) / "before-up.db"), "--execute")
            self.run_memory(root, "update", "--type", "semantic", "--fact", "Synthetic fact written after schema upgrade.")
            result = self.command(root, "maintain-system-migrate", "--target-version", "system-evolution-v1",
                                  "--backup-file", str(Path(directory) / "before-down.db"), "--execute")
            self.assertTrue(result["migration_performed"])
            self.assertEqual(1, len(self.list_records(root, "semantic")))
            self.assertEqual(saved["proposal_id"], self.command(root, "maintain-system", "--change-id", str(saved["proposal_id"]))["change"]["id"])

    def test_interrupted_rebuild_rolls_back_and_retains_valid_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root, saved = self.fixture(directory)
            project = resolve_project(str(root), str(self.memory_home(root)))
            backup = Path(directory) / "failure-backup.db"
            original = migrations.rebuild_proposals
            def interrupt_after_rebuild(conn, target):
                original(conn, target)
                self.assertIn("'checked'", conn.execute("SELECT sql FROM sqlite_master WHERE name='system_change_proposals'").fetchone()[0])
                raise RuntimeError("Controlled interruption after actual table rebuild")
            with patch("tools.agent_memory_runtime.system_evolution_migrations.rebuild_proposals", side_effect=interrupt_after_rebuild):
                with self.assertRaisesRegex(RuntimeError, "Controlled interruption"):
                    migrate_governance(project, "system-evolution-v2", str(backup), True)
            for database in (backup, project.db_path):
                with closing(sqlite3.connect(database)) as conn:
                    self.assertEqual("ok", conn.execute("PRAGMA integrity_check").fetchone()[0])
                    self.assertEqual("system-evolution-v1", conn.execute("SELECT version FROM runtime_schema_versions WHERE component='system_evolution'").fetchone()[0])
                    self.assertNotIn("'checked'", conn.execute("SELECT sql FROM sqlite_master WHERE name='system_change_proposals'").fetchone()[0])
            self.assertEqual(1, self.command(root, "maintain-system", "--change-id", str(saved["proposal_id"]))["change"]["state_revision"])
