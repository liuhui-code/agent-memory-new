# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.storage import ensure_initialized, resolve_project
from tools.agent_memory_runtime.semantic_index import semantic_file_batches
from tools.agent_memory_runtime.semantic_models import MAX_GAPS, SemanticBatch
from tools.agent_memory_runtime.semantic_ecma import bounded_gaps, parse_file
from tools.agent_memory_runtime.retrieval_feedback import collect_feedback_adjustments
from tools.agent_memory_runtime.experience_usage import collect_usage_adjustments_by_type
from tools.agent_memory_runtime.query_edges import collect_related_edges
from tools.agent_memory_runtime.governance_corrections import build_experience_conflict_candidates
from tools.agent_memory_runtime.governance_review import reflection_experience_type
from tools.agent_memory_runtime.governance_utils import duplicate_candidates, overlap_candidates_for
from tools.agent_memory_runtime.storage_migrations import migrate_memory_edge_metadata


class GraphQueryPerformanceTests(AgentMemoryTestBase):
    def test_duplicate_detection_does_not_compare_disjoint_rows(self) -> None:
        rows = [
            {"id": index, "fact": f"unique_token_{index}"}
            for index in range(500)
        ]
        prepared_tokens = [
            {f"unique_token_{index}"} for index in range(500)
        ]
        postings = {
            f"unique_token_{index}": [index] for index in range(500)
        }

        self.assertEqual({}, overlap_candidates_for(0, prepared_tokens[0], postings))
        self.assertEqual([], duplicate_candidates(rows, "semantic"))

    def test_experience_conflict_classifies_each_row_once(self) -> None:
        rows = [
            {
                "id": index,
                "experience_type": "procedure_experience",
                "trigger_condition": "same trigger",
                "scope": "same scope",
                "future_rule": "same rule",
                "repair_action": "same action",
            }
            for index in range(200)
        ]

        with patch(
            "tools.agent_memory_runtime.governance_corrections.reflection_experience_type",
            wraps=reflection_experience_type,
        ) as classify:
            candidates = build_experience_conflict_candidates(rows)

        self.assertEqual([], candidates)
        self.assertEqual(len(rows), classify.call_count)

    def test_experience_conflict_skips_disjoint_context_pairs(self) -> None:
        rows = [
            {
                "id": index,
                "experience_type": "procedure_experience",
                "trigger_condition": f"trigger_{index}",
                "scope": f"scope_{index}",
                "future_rule": "rule",
                "repair_action": "action",
            }
            for index in range(200)
        ]

        with patch(
            "tools.agent_memory_runtime.governance_corrections.prepared_shared_context",
            wraps=__import__(
                "tools.agent_memory_runtime.governance_corrections",
                fromlist=["prepared_shared_context"],
            ).prepared_shared_context,
        ) as compare:
            candidates = build_experience_conflict_candidates(rows)

        self.assertEqual([], candidates)
        self.assertEqual(0, compare.call_count)

    def test_related_edges_read_both_directions_with_one_query_per_batch(self) -> None:
        project = MagicMock(project_id="project")
        conn = MagicMock()
        conn.__enter__.return_value = conn
        conn.execute.return_value.fetchall.return_value = []

        with patch("tools.agent_memory_runtime.query_edges.connect", return_value=conn):
            edges = collect_related_edges(project, {"code_symbol": {1, 2, 3}})

        self.assertEqual([], edges)
        self.assertEqual(1, conn.execute.call_count)

    def test_feedback_adjustments_for_both_types_use_one_query(self) -> None:
        project = MagicMock(project_id="project")
        conn = MagicMock()
        conn.__enter__.return_value = conn
        conn.execute.return_value.fetchall.return_value = []

        with patch("tools.agent_memory_runtime.retrieval_feedback.connect", return_value=conn):
            penalties, calibration = collect_feedback_adjustments(
                project, "profile failed", ("semantic", "reflection")
            )

        self.assertEqual({"semantic": {}, "reflection": {}}, penalties)
        self.assertEqual({"semantic": {}, "reflection": {}}, calibration)
        self.assertEqual(1, conn.execute.call_count)

    def test_usage_adjustments_for_both_types_use_one_query(self) -> None:
        project = MagicMock(project_id="project")
        conn = MagicMock()
        conn.__enter__.return_value = conn
        conn.execute.return_value.fetchall.return_value = []

        with patch("tools.agent_memory_runtime.experience_usage.connect", return_value=conn):
            adjustments = collect_usage_adjustments_by_type(
                project, "profile failed", ("semantic", "reflection")
            )

        self.assertEqual({"semantic": {}, "reflection": {}}, adjustments)
        self.assertEqual(1, conn.execute.call_count)

    def test_static_semantic_fields_are_scanned_once_per_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "src" / "ManyMethods.ets"
            source.parent.mkdir()
            methods = "\n".join(
                f"  method{index}(): void {{ this.service.run() }}" for index in range(40)
            )
            source.write_text(
                "export class ManyMethods {\n"
                "  service: WorkerService\n"
                f"{methods}\n"
                "}\n",
                encoding="utf-8",
            )
            project = resolve_project(str(root), str(self.memory_home(root)))

            with patch(
                "tools.agent_memory_runtime.semantic_ecma.container_fields",
                wraps=__import__(
                    "tools.agent_memory_runtime.semantic_ecma",
                    fromlist=["container_fields"],
                ).container_fields,
            ) as field_scan:
                parsed = parse_file(project, source.resolve(), "ArkTS", True)

        self.assertEqual(1, field_scan.call_count)
        self.assertEqual(40, len([edge for edge in parsed.relations if edge.relation == "calls"]))

    def test_semantic_files_are_split_into_bounded_batches(self) -> None:
        batches = semantic_file_batches([Path(f"src/File{index}.ets") for index in range(5001)])

        self.assertEqual([1000, 1000, 1000, 1000, 1000, 1], [len(batch) for batch in batches])

    def test_static_gap_diagnostics_are_bounded_without_relaxing_provider_contract(self) -> None:
        gaps = [{"kind": "unresolved", "symbol": str(index)} for index in range(MAX_GAPS + 1)]
        batch = SemanticBatch(
            adapter_id="static",
            adapter_version="1",
            language="ArkTS",
            capabilities=[],
            source_digests={},
            gaps=gaps,
        )

        self.assertEqual(MAX_GAPS, len(bounded_gaps(gaps)))
        with self.assertRaisesRegex(ValueError, "exceeds 1000 gaps"):
            batch.validate()

    def test_repeated_initialization_does_not_rebuild_fts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = resolve_project(str(root), str(self.memory_home(root)))
            ensure_initialized(project)

            with patch("tools.agent_memory_runtime.storage_search_schema.rebuild_search_indexes") as rebuild:
                ensure_initialized(project)

        rebuild.assert_not_called()

    def test_query_feedback_batch_indexes_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = resolve_project(str(root), str(self.memory_home(root)))
            ensure_initialized(project)
            with sqlite3.connect(project.db_path) as conn:
                feedback_indexes = {
                    row[1] for row in conn.execute("PRAGMA index_list(retrieval_feedback)")
                }
                usage_indexes = {
                    row[1] for row in conn.execute("PRAGMA index_list(experience_usage_events)")
                }

        self.assertIn("idx_retrieval_feedback_project_type_recent", feedback_indexes)
        self.assertIn("idx_experience_usage_project_type_recent", usage_indexes)

    def test_repeated_edge_metadata_migration_does_not_rewrite_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = resolve_project(str(root), str(self.memory_home(root)))
            ensure_initialized(project)
            with sqlite3.connect(project.db_path) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute(
                    """
                    INSERT INTO memory_edges(
                      project_id, source_type, source_id, relation, target_type, target_id,
                      extractor_version, evidence_kind, valid_from, last_verified_at, created_at
                    ) VALUES (?, 'code_file', 1, 'contains', 'code_symbol', 2,
                              'code-wiki:v4', 'static_containment', 'now', 'now', 'now')
                    """,
                    (project.project_id,),
                )
                conn.commit()
                before = conn.total_changes

                migrate_memory_edge_metadata(conn)

                self.assertEqual(0, conn.total_changes - before)

    def test_test_edges_stay_inside_module_and_exclude_config_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            files = {
                "feature-a/oh-package.json5": "{}",
                "feature-a/src/main/ets/ProfileService.ets": "export class ProfileService {}",
                "feature-a/src/test/ProfileServiceTest.ets": "export class ProfileServiceTest {}",
                "feature-a/TestRely/oh-package.json5": "{}",
                "feature-b/oh-package.json5": "{}",
                "feature-b/src/main/ets/ProfileService.ets": "export class ProfileService {}",
                "feature-b/src/test/ProfileServiceTest.ets": "export class ProfileServiceTest {}",
            }
            for relative, content in files.items():
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content + "\n", encoding="utf-8")

            self.run_memory(project, "learn-path", "--path", ".", "--json")
            rows = self.list_records(project, "memory-edge")
            code_files = {
                int(row["id"]): str(row["file_path"])
                for row in self.list_records(project, "code-file")
            }

        tested = [row for row in rows if row["relation"] == "tested_by"]
        pairs = {
            (code_files[int(row["source_id"])], code_files[int(row["target_id"])])
            for row in tested
        }
        self.assertEqual(
            {
                (
                    "feature-a/src/main/ets/ProfileService.ets",
                    "feature-a/src/test/ProfileServiceTest.ets",
                ),
                (
                    "feature-b/src/main/ets/ProfileService.ets",
                    "feature-b/src/test/ProfileServiceTest.ets",
                ),
            },
            pairs,
        )

    def test_safe_graph_rebuild_preserves_business_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            source = project / "src" / "Profile.ets"
            source.parent.mkdir()
            source.write_text("@Component\nstruct Profile { build() {} }\n", encoding="utf-8")
            self.run_memory(project, "learn-path", "--path", "src", "--json")
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps(
                    {
                        "files": [
                            {
                                "file_path": "src/Profile.ets",
                                "business_summary": "用户资料页",
                                "business_terms": ["用户资料"],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "Profile 页面展示用户资料",
            )

            result = self.run_memory(
                project,
                "maintain-rebuild-derived",
                "--target",
                "graph",
                "--json",
            )
            payload = json.loads(result.stdout)
            code_file = self.list_records(project, "code-file")[0]
            semantic = self.list_records(project, "semantic")

        self.assertEqual("用户资料页", code_file["business_summary"])
        self.assertEqual(["用户资料"], json.loads(str(code_file["business_terms"])))
        self.assertEqual(1, len(semantic))
        self.assertGreater(payload["graph"]["after"]["edge_count"], 0)
        self.assertEqual(0, payload["preserved"]["code_business_rows_changed"])

    def test_explicit_search_rebuild_repairs_missing_fts_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            source = project / "src" / "Profile.ets"
            source.parent.mkdir()
            source.write_text("@Component\nstruct Profile { build() {} }\n", encoding="utf-8")
            self.run_memory(project, "learn-path", "--path", "src", "--json")
            memory_home = self.memory_home(project)
            resolved = resolve_project(str(project), str(memory_home))
            with sqlite3.connect(resolved.db_path) as conn:
                conn.execute("DELETE FROM code_file_fts")

            self.run_memory(
                project,
                "maintain-rebuild-derived",
                "--target",
                "search",
                "--json",
            )
            result = self.run_memory(
                project,
                "wiki-search",
                "--query",
                "Profile",
                "--json",
            )

        self.assertTrue(json.loads(result.stdout))


if __name__ == "__main__":
    import unittest

    unittest.main()
