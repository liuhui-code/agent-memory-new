# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_candidate_recall import (
    merge_lane_ids,
    method_evidence_focus_terms,
    method_evidence_term_coverage,
)


class MethodSymbolEvidenceTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "method-evidence"
        source = self.project / "src" / "Coordinator.ets"
        source.parent.mkdir(parents=True)
        source.write_text(
            """export class Coordinator {
  async execute(): Promise<boolean> {
    const response = await this.accessManager.requestPermissionsFromUser(['camera'])
    return response.authResults.every((value: number) => value === 0)
  }

  render(): string {
    return this.themeManager.resolveColor('accent')
  }
}
""",
            encoding="utf-8",
        )
        self.run_memory(self.project, "learn-path", "--path", ".", "--json")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def symbol_rows(self) -> list[sqlite3.Row]:
        db_path = self.project_memory_dir(self.project) / "memory.db"
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT symbol, summary, method_evidence, start_line, end_line FROM code_symbols "
                "WHERE project_id = ? AND file_path = 'src/Coordinator.ets' "
                "ORDER BY start_line, id",
                (self.project_id(self.project),),
            ).fetchall()

    def test_learning_indexes_bounded_method_body_evidence_per_symbol(self) -> None:
        rows = {str(row["symbol"]): row for row in self.symbol_rows()}
        execute_evidence = str(rows["execute"]["method_evidence"])
        render_evidence = str(rows["render"]["method_evidence"])

        self.assertIn("permissions", execute_evidence)
        self.assertIn("auth", execute_evidence)
        self.assertNotIn("resolvecolor", execute_evidence)
        self.assertIn("resolvecolor", render_evidence)
        self.assertNotIn("permissions", render_evidence)
        self.assertLessEqual(len(execute_evidence.split()), 36)

    def test_method_index_is_sparse_and_rejects_single_term_noise(self) -> None:
        db_path = self.project_memory_dir(self.project) / "memory.db"
        with sqlite3.connect(db_path) as conn:
            indexed_count = conn.execute(
                "SELECT COUNT(*) FROM code_method_fts WHERE project_id = ?",
                (self.project_id(self.project),),
            ).fetchone()[0]
            evidence_count = conn.execute(
                "SELECT COUNT(*) FROM code_symbols WHERE project_id = ? "
                "AND COALESCE(method_evidence, '') != ''",
                (self.project_id(self.project),),
            ).fetchone()[0]

        self.assertEqual(evidence_count, indexed_count)
        self.assertEqual(
            1,
            method_evidence_term_coverage(
                "request permissions response auth results",
                ["unrelated", "permission"],
            ),
        )
        self.assertGreaterEqual(
            method_evidence_term_coverage(
                "request permissions response auth results",
                ["results", "permission", "request"],
            ),
            2,
        )

    def test_method_terms_preserve_embedded_identifiers_in_long_chinese_query(self) -> None:
        terms = method_evidence_focus_terms(
            "清空 lease; locate the method that destroys it before opening"
        )

        self.assertTrue({"lease", "destroy", "open"} <= set(terms))

    def test_method_body_lane_remains_lower_priority_than_identity_terms(self) -> None:
        lanes = {
            "method_body_fts": [99],
            "term_fts:1": [1, 2],
            "term_fts:2": [3, 4],
            "broad_fts": [5, 6],
        }

        selected = merge_lane_ids(lanes, 3)

        self.assertEqual([1, 3, 2], selected)
        self.assertNotIn(99, selected)

    def test_context_recalls_method_owner_and_its_source_range(self) -> None:
        result = self.run_memory(
            self.project,
            "context",
            "--query",
            "authorization results from the permission request",
            "--compact",
            "--json",
        )
        payload = json.loads(result.stdout)
        anchors = payload["query_handoff"]["code_anchors"]
        owner = next(
            item for item in anchors
            if item.get("file_path") == "src/Coordinator.ets" and item.get("symbol") == "execute"
        )

        self.assertEqual("primary", owner["role"])
        source_range = owner["source_ranges"][0]
        self.assertLessEqual(int(source_range["start_line"]), 3)
        self.assertGreaterEqual(int(source_range["end_line"]), 4)
        self.assertTrue(owner.get("source_excerpts"))

    def test_graph_rebuild_keeps_method_evidence_idempotent(self) -> None:
        self.run_memory(
            self.project,
            "maintain-rebuild-derived",
            "--target",
            "graph",
            "--json",
        )
        before = {
            str(row["symbol"]): str(row["method_evidence"] or "")
            for row in self.symbol_rows()
        }
        self.run_memory(
            self.project,
            "maintain-rebuild-derived",
            "--target",
            "graph",
            "--json",
        )
        after = {
            str(row["symbol"]): str(row["method_evidence"] or "")
            for row in self.symbol_rows()
        }

        self.assertEqual(before, after)


if __name__ == "__main__":
    import unittest

    unittest.main()
