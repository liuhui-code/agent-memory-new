# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from agent_memory_test_base import AgentMemoryTestBase, REPO_ROOT
from tools.agent_memory_runtime.code_wiki_extractors import extract_log_statements
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import COMPACT_TOKEN_BUDGET, compact_context
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens
from tools.agent_memory_runtime.storage import ensure_initialized, resolve_project


NOW = "2026-07-15T00:00:00Z"


class LogAnchoredPathTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "project"
        self.root.mkdir()
        self.project = resolve_project(str(self.root), str(self.memory_home(self.root)))
        ensure_initialized(self.project)
        self.ids = self._seed_graph()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _seed_graph(self) -> dict[str, int]:
        ids: dict[str, int] = {}
        with sqlite3.connect(self.project.db_path) as conn:
            for path in (
                "entry/src/main/ets/pages/ProfilePage.ets",
                "entry/src/main/ets/SessionAbility.ets",
                "feature/src/main/ets/ProfileService.ets",
            ):
                cursor = conn.execute(
                    "INSERT INTO code_files(project_id, file_path, language, updated_at) VALUES (?, ?, 'ArkTS', ?)",
                    (self.project.project_id, path, NOW),
                )
                ids[path] = int(cursor.lastrowid)
            symbols = (
                ("page", "entry/src/main/ets/pages/ProfilePage.ets", "aboutToAppear", 10, 16),
                ("ability", "entry/src/main/ets/SessionAbility.ets", "onCreate", 20, 28),
                ("load", "feature/src/main/ets/ProfileService.ets", "loadProfile", 30, 48),
            )
            for key, path, name, start, end in symbols:
                cursor = conn.execute(
                    """
                    INSERT INTO code_symbols(
                      project_id, file_path, symbol, symbol_type, qualified_name,
                      start_line, end_line, evidence_class, updated_at
                    ) VALUES (?, ?, ?, 'method', ?, ?, ?, 'static', ?)
                    """,
                    (self.project.project_id, path, name, f"Demo.{name}", start, end, NOW),
                )
                ids[key] = int(cursor.lastrowid)
            cursor = conn.execute(
                """
                INSERT INTO code_log_statements(
                  project_id, file_path, line, function, level, logger,
                  message_template, business_event, likely_causes, updated_at
                ) VALUES (?, ?, 42, 'loadProfile', 'error', 'ProfileService',
                          'profile load failed', 'profile_load_failed', '["wrong historical cause"]', ?)
                """,
                (self.project.project_id, "feature/src/main/ets/ProfileService.ets", NOW),
            )
            ids["failure_log"] = int(cursor.lastrowid)
            cursor = conn.execute(
                """
                INSERT INTO code_log_statements(
                  project_id, file_path, line, function, level, logger,
                  message_template, business_event, updated_at
                ) VALUES (?, ?, 12, 'aboutToAppear', 'info', 'ProfilePage',
                          'profile page appearing', 'profile_page_open', ?)
                """,
                (self.project.project_id, "entry/src/main/ets/pages/ProfilePage.ets", NOW),
            )
            ids["entry_log"] = int(cursor.lastrowid)
            self._insert_edge(conn, ids["page"], "calls", "code_symbol", ids["load"], 0.96)
            self._insert_edge(conn, ids["ability"], "calls", "code_symbol", ids["load"], 0.91)
            self._insert_edge(conn, ids["load"], "emits_log", "code_log_statement", ids["failure_log"], 1.0)
            self._insert_edge(conn, ids["page"], "emits_log", "code_log_statement", ids["entry_log"], 1.0)
            conn.execute(
                "INSERT OR REPLACE INTO graph_runtime_state(project_id, graph_revision, updated_at) VALUES (?, 7, ?)",
                (self.project.project_id, NOW),
            )
            conn.commit()
        return ids

    def _insert_edge(
        self,
        conn: sqlite3.Connection,
        source_id: int,
        relation: str,
        target_type: str,
        target_id: int,
        confidence: float,
        valid_to: str | None = None,
    ) -> int:
        cursor = conn.execute(
            """
            INSERT INTO memory_edges(
              project_id, source_type, source_id, relation, target_type, target_id,
              confidence, source_revision, extractor_version, valid_from, valid_to,
              evidence_kind, last_verified_at, created_at
            ) VALUES (?, 'code_symbol', ?, ?, ?, ?, ?, '7', 'arkts-semantic:v1', ?, ?,
                      'static_call', ?, ?)
            """,
            (
                self.project.project_id,
                source_id,
                relation,
                target_type,
                target_id,
                confidence,
                NOW,
                valid_to,
                NOW,
                NOW,
            ),
        )
        return int(cursor.lastrowid)

    def path_context(self, query: str = "07-15 09:30:01 pid=213 profile load failed") -> dict:
        payload = build_context_facade(self.project).execute(query)
        return payload["query_handoff"]["path_context"]

    def test_exact_log_anchor_returns_diverse_candidate_paths(self) -> None:
        result = self.path_context()

        self.assertTrue(result["activated"])
        self.assertEqual(7, result["graph_revision"])
        self.assertEqual(2, len(result["path_candidates"]))
        entries = {item["entry"]["node"]["name"] for item in result["path_candidates"]}
        self.assertEqual({"aboutToAppear", "onCreate"}, entries)
        for candidate in result["path_candidates"]:
            self.assertEqual("loadProfile", candidate["emitter"]["name"])
            self.assertNotIn("root_cause", candidate)
            self.assertNotIn("experience", candidate["score_components"])

    def test_expected_logs_help_agent_align_real_runtime_order(self) -> None:
        result = self.path_context()
        page_path = next(
            item for item in result["path_candidates"] if item["entry"]["node"]["name"] == "aboutToAppear"
        )

        messages = {item["message_template"] for item in page_path["expected_log_anchors"]}
        self.assertIn("profile page appearing", messages)
        self.assertIn("profile load failed", messages)

    def test_experience_and_semantic_correction_do_not_change_structural_paths(self) -> None:
        before = self.path_context()
        with sqlite3.connect(self.project.db_path) as conn:
            conn.execute(
                """
                INSERT INTO reflections(project_id, task, summary, lesson, created_at)
                VALUES (?, 'profile load failed', 'claim a different path', 'always blame cache', ?)
                """,
                (self.project.project_id, NOW),
            )
            conn.execute(
                """
                INSERT INTO semantic_facts(project_id, fact, source, created_at, updated_at)
                VALUES (?, 'profile load failed means business correction only', 'user', ?, ?)
                """,
                (self.project.project_id, NOW, NOW),
            )
            conn.commit()

        after = self.path_context()

        self.assertEqual(before, after)

    def test_stale_edges_are_excluded(self) -> None:
        with sqlite3.connect(self.project.db_path) as conn:
            stale = conn.execute(
                """
                INSERT INTO code_symbols(project_id, file_path, symbol, symbol_type, updated_at)
                VALUES (?, 'legacy/OldPage.ets', 'onPageShow', 'method', ?)
                """,
                (self.project.project_id, NOW),
            )
            self._insert_edge(conn, int(stale.lastrowid), "calls", "code_symbol", self.ids["load"], 1.0, NOW)
            conn.commit()

        result = self.path_context()

        names = {node["name"] for path in result["path_candidates"] for node in path["nodes"]}
        self.assertNotIn("onPageShow", names)

    def test_generic_query_does_not_activate_path_reconstruction(self) -> None:
        result = self.path_context("how should profile architecture be designed")

        self.assertFalse(result["activated"])
        self.assertEqual([], result["path_candidates"])

    def test_public_context_command_exposes_path_context_without_new_command(self) -> None:
        process = self.run_memory(
            self.root,
            "context",
            "--query",
            "profile load failed",
            "--json",
        )
        payload = json.loads(process.stdout)

        self.assertIn("path_context", payload["query_handoff"])
        self.assertTrue(payload["query_handoff"]["path_context"]["activated"])

    def test_compact_context_keeps_handoff_and_omits_full_audit(self) -> None:
        full = json.loads(self.run_memory(
            self.root, "context", "--query", "profile load failed", "--json",
        ).stdout)
        compact = json.loads(self.run_memory(
            self.root, "context", "--query", "profile load failed", "--compact", "--json",
        ).stdout)

        self.assertEqual("agent-context-compact/v1", compact["schema_version"])
        self.assertTrue(compact["query_handoff"]["log_anchors"])
        self.assertTrue(compact["query_handoff"]["path_context"]["path_candidates"])
        self.assertNotIn("query_audit", compact)
        self.assertNotIn("code_log_matches", compact)
        self.assertIn("query_audit", full)
        self.assertLess(len(json.dumps(compact)), len(json.dumps(full)) * 0.45)
        self.assertLessEqual(compact["output_budget"]["estimated_tokens"], COMPACT_TOKEN_BUDGET)

    def test_compact_budget_preserves_correction_guard(self) -> None:
        full = build_context_facade(self.project).execute("profile load failed")
        full["correction_guards"] = [{
            "id": 9,
            "experience_type": "correction_experience",
            "fact": "Use the current session lifecycle meaning.",
            "scope": "ProfileService",
            "warnings": ["historical interpretation is stale"],
        }]
        full["query_handoff"]["log_keywords"] = [f"keyword-{index}-" + "x" * 120 for index in range(40)]
        full["query_handoff"]["experience_refs"] = [
            {"reflection_id": index, "task": "x" * 300, "warnings": ["y" * 300]}
            for index in range(20)
        ]
        heavy_guard = {
            "id": 10,
            "experience_type": "semantic_patch_experience",
            "fact": "f" * 500,
            "scope": "s" * 500,
            "task": "t" * 500,
            "problem": "p" * 500,
            "trigger_condition": "c" * 500,
            "lesson": "l" * 500,
            "reason": "r" * 500,
            "warnings": ["w" * 500, "z" * 500],
        }
        full["semantic_patch_notes"] = [heavy_guard, heavy_guard]
        full["blocked_memory_notes"] = [heavy_guard, heavy_guard]
        full["conflict_notes"] = [heavy_guard, heavy_guard]

        compact = compact_context(full)

        self.assertEqual(9, compact["correction_guards"][0]["id"])
        self.assertLessEqual(estimate_payload_tokens(compact), COMPACT_TOKEN_BUDGET)

    def test_query_skill_uses_selective_compact_routing(self) -> None:
        skill = (REPO_ROOT / "skills" / "agent-memory-query" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("L0 current source first", skill)
        self.assertIn("L1 compact context", skill)
        self.assertIn("L2 focused expansion", skill)
        self.assertIn("--compact --json", skill)

    def test_relation_aware_active_edge_indexes_are_installed(self) -> None:
        with sqlite3.connect(self.project.db_path) as conn:
            indexes = {row[1] for row in conn.execute("PRAGMA index_list(memory_edges)")}

        self.assertIn("idx_memory_edges_project_valid_source_relation", indexes)
        self.assertIn("idx_memory_edges_project_valid_target_relation", indexes)

    def test_arkts_logs_bind_to_async_and_static_async_methods(self) -> None:
        source = self.root / "AsyncLogs.ets"
        source.write_text(
            """
struct Demo {
  async aboutToAppear() {
    console.info('appearing')
  }
  static async queryAll() {
    console.error('query failed')
  }
}
""".strip()
            + "\n",
            encoding="utf-8",
        )

        logs = extract_log_statements(source, "ArkTS")

        self.assertEqual(["aboutToAppear", "queryAll"], [item["function"] for item in logs])


if __name__ == "__main__":
    import unittest

    unittest.main()
