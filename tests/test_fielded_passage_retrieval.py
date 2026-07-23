# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.code_passages import rebuild_code_passages
from tools.agent_memory_runtime.query_candidate_recall import SQLiteCandidateRecall
from tools.agent_memory_runtime.query_fielded_retrieval import (
    candidate_path_recall_at_k,
    fielded_passage_rankings,
)
from tools.agent_memory_runtime.storage import connect, ensure_initialized, resolve_project


class FieldedPassageRetrievalTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "project"
        self.root.mkdir()
        self.project = resolve_project(str(self.root), str(self.memory_home(self.root)))
        ensure_initialized(self.project)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_passages_preserve_source_identity_and_normalized_terms(self) -> None:
        with connect(self.project) as conn:
            file_id, symbol_id = insert_source_records(conn, self.project.project_id)
            stats = rebuild_code_passages(conn, self.project.project_id)
            passages = conn.execute(
                "SELECT * FROM code_passages WHERE project_id = ? ORDER BY source_type",
                (self.project.project_id,),
            ).fetchall()

        self.assertEqual(2, stats["passages_written"])
        self.assertEqual({file_id, symbol_id}, {int(row["source_id"]) for row in passages})
        symbol = next(row for row in passages if row["source_type"] == "code_symbol")
        self.assertEqual("digest-v1", symbol["source_digest"])
        self.assertEqual(7, symbol["index_generation"])
        self.assertIn("restore", symbol["identity_terms"].split())
        self.assertIn("session", symbol["identity_terms"].split())
        self.assertIn("web_state_snapshot", symbol["string_terms"].split())
        self.assertIn("snapshot", symbol["string_terms"].split())

    def test_fielded_retrievers_keep_channels_separate(self) -> None:
        with connect(self.project) as conn:
            _file_id, symbol_id = insert_source_records(conn, self.project.project_id)
            rebuild_code_passages(conn, self.project.project_id)
            batch = fielded_passage_rankings(
                conn,
                self.project,
                "restore the web state snapshot from preferences",
                20,
            )

        self.assertIn(symbol_id, batch.rankings["symbol_identity_fts"])
        self.assertIn(symbol_id, batch.rankings["method_body_fts"])
        self.assertIn(symbol_id, batch.rankings["string_key_fts"])
        self.assertEqual("code_passage_fts/v2", batch.audit["provider"])
        self.assertGreater(batch.audit["channels"]["symbol_identity_fts"]["symbol_weight"], 1)

    def test_scoped_rebuild_replaces_old_passages(self) -> None:
        with connect(self.project) as conn:
            insert_source_records(conn, self.project.project_id)
            rebuild_code_passages(conn, self.project.project_id)
            conn.execute(
                "UPDATE code_symbols SET symbol = 'loadCurrentSession', "
                "qualified_name = 'SessionRestoreGateway.loadCurrentSession', "
                "signature = 'loadCurrentSession(): Promise<void>', "
                "method_evidence = 'preferences current session load' "
                "WHERE project_id = ?",
                (self.project.project_id,),
            )
            rebuild_code_passages(
                conn,
                self.project.project_id,
                ["src/state/SessionRestoreGateway.ets"],
            )
            passages = conn.execute(
                "SELECT symbol, identity_terms FROM code_passages "
                "WHERE project_id = ? AND source_type = 'code_symbol'",
                (self.project.project_id,),
            ).fetchall()

        self.assertEqual(1, len(passages))
        self.assertEqual("loadCurrentSession", passages[0]["symbol"])
        self.assertNotIn("restoresessionstate", passages[0]["identity_terms"].split())

    def test_candidate_audit_supports_recall_at_twenty(self) -> None:
        with connect(self.project) as conn:
            insert_source_records(conn, self.project.project_id)
            rebuild_code_passages(conn, self.project.project_id)
            recalled = SQLiteCandidateRecall(enable_passage_shadow=True).recall(
                conn, self.project, "restore web state snapshot preferences"
            )

        fielded = recalled.audit["tables"]["code_symbols"]["fielded_retrieval"]
        refs = fielded["candidate_refs"]
        self.assertEqual(
            1.0,
            candidate_path_recall_at_k(
                {"src/state/SessionRestoreGateway.ets"}, refs, 20
            ),
        )
        self.assertIn("method_body_fts", refs[0]["channels"])
        self.assertEqual("shadow", fielded["mode"])
        self.assertFalse(fielded["serving_candidates_changed"])

    def test_wiki_index_builds_callable_and_string_key_passages(self) -> None:
        source = self.root / "src" / "state" / "DraftStore.ets"
        source.parent.mkdir(parents=True)
        source.write_text(
            """export class DraftStore {
  async restoreDraft(): Promise<void> {
    const payload = await this.preferences.get('draft_snapshot_key')
    this.controller.restore(payload)
  }
}
""",
            encoding="utf-8",
        )

        self.run_memory(self.root, "learn-path", "--path", ".", "--json")

        with connect(self.project) as conn:
            symbol = conn.execute(
                "SELECT string_evidence FROM code_symbols "
                "WHERE project_id = ? AND symbol = 'restoreDraft'",
                (self.project.project_id,),
            ).fetchone()
            passage = conn.execute(
                "SELECT passage_kind, string_terms FROM code_passages "
                "WHERE project_id = ? AND symbol = 'restoreDraft'",
                (self.project.project_id,),
            ).fetchone()

        self.assertIn("draft_snapshot_key", symbol["string_evidence"].split())
        self.assertEqual("callable", passage["passage_kind"])
        self.assertIn("snapshot", passage["string_terms"].split())


def insert_source_records(conn: object, project_id: str) -> tuple[int, int]:
    file_cursor = conn.execute(
        """
        INSERT INTO code_files(
          project_id, file_path, summary, language, business_summary,
          business_terms, source_digest, index_generation, updated_at
        ) VALUES (?, ?, ?, 'ArkTS', ?, ?, 'digest-v1', 7, '2026-07-20T00:00:00Z')
        """,
        (
            project_id,
            "src/state/SessionRestoreGateway.ets",
            "Gateway for bounded saved state restoration",
            "Restores a browser session from persisted state",
            '["saved state", "restore"]',
        ),
    )
    symbol_cursor = conn.execute(
        """
        INSERT INTO code_symbols(
          project_id, file_path, symbol, symbol_type, summary, calls,
          business_summary, business_terms, qualified_name, signature,
          start_line, end_line, source_digest, evidence_class,
          method_evidence, string_evidence, index_generation, updated_at
        ) VALUES (?, ?, ?, 'method', ?, '', ?, ?, ?, ?, 10, 24,
                  'digest-v1', 'ast', ?, ?, 7, '2026-07-20T00:00:00Z')
        """,
        (
            project_id,
            "src/state/SessionRestoreGateway.ets",
            "restoreSessionState",
            "ArkTS method restoreSessionState",
            "Validates saved state size before restoring the controller",
            '["saved state", "browser restore"]',
            "SessionRestoreGateway.restoreSessionState",
            "restoreSessionState(): Promise<void>",
            "preferences get state length maximum controller restore",
            "web_state_snapshot web state snapshot",
        ),
    )
    conn.commit()
    return int(file_cursor.lastrowid), int(symbol_cursor.lastrowid)
