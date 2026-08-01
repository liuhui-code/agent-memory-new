# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.evidence_context import build_evidence_context
from tools.agent_memory_runtime.semantic_adapters import ArkTSSemanticAdapter, registered_adapter_manifest
from tools.agent_memory_runtime.semantic_dispatch_candidates import (
    MAX_DISPATCH_CANDIDATES,
    expand_dispatch_candidates_across_batches,
)
from tools.agent_memory_runtime.semantic_models import SemanticBatch, SemanticEntity
from tools.agent_memory_runtime.semantic_index import supersede_weaker_edge
from tools.agent_memory_runtime.storage import connect, now_iso, resolve_project


class SemanticIndexTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "semantic-demo"
        self.project.mkdir()
        self.write_arkts_project()
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_file(self, relative: str, content: str) -> None:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")

    def write_arkts_project(self) -> None:
        self.write_file(
            "service/ProfileService.ets",
            """
export class ProfileService {
  load(): string {
    console.error('profile load failed')
    return ''
  }
}
""",
        )
        self.write_file(
            "pages/ProfilePage.ets",
            """
import { ProfileService } from '../service/ProfileService'
@Component
struct ProfilePage {
  @State profileName: string = ''
  private service: ProfileService = new ProfileService()
  handleSave(): void {
    this.profileName = this.profileName + '!'
  }
  refresh(): void {
    this.handleSave()
    this.service.load()
  }
  build() {
    Button('Refresh').onClick(this.handleSave)
  }
}
""",
        )

    def db_rows(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        db_path = self.project_memory_dir(self.project) / "memory.db"
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(query, params).fetchall()

    def learn_all(self) -> dict:
        result = self.run_memory(self.project, "learn-path", "--path", ".", "--json")
        return json.loads(result.stdout)

    def test_semantic_ir_round_trip_and_validation(self) -> None:
        entity = SemanticEntity(
            key="symbol:local", file_path="src/a.ts", name="run", kind="function",
            qualified_name="run", signature="run():void", start_line=1, end_line=2,
        )
        batch = SemanticBatch(
            adapter_id="test", adapter_version="1", language="TypeScript",
            capabilities=["definitions"], source_digests={"src/a.ts": "digest"},
            entities=[entity],
        )

        restored = SemanticBatch.from_dict(batch.to_dict())

        self.assertEqual("semantic-index/v1", restored.schema_version)
        self.assertEqual(entity, restored.entities[0])
        with self.assertRaises(ValueError):
            SemanticBatch.from_dict({"schema_version": "semantic-index/v2"})

    def test_adapter_registry_keeps_language_specific_logic_out_of_core(self) -> None:
        manifest = registered_adapter_manifest()

        self.assertEqual({"ArkTS", "TypeScript"}, {item["language"] for item in manifest})
        self.assertTrue(all("calls" in item["capabilities"] for item in manifest))

    def test_dispatch_catalog_crosses_batches_with_explicit_candidate_budget(self) -> None:
        self.write_file("dispatch/Contract.ets", "export interface Contract {\n}")
        self.write_file(
            "dispatch/Caller.ets",
            """
export class Caller {
  private target: Contract
  run(): void { this.target.execute('work') }
}
""",
        )
        implementations: list[Path] = []
        for index in range(MAX_DISPATCH_CANDIDATES + 2):
            relative = f"dispatch/Worker{index}.ets"
            self.write_file(
                relative,
                f"""
export class Worker{index} implements Contract {{
  execute(message: string): void {{ console.error(message) }}
}}
""",
            )
            implementations.append(self.project / relative)
        runtime_project = resolve_project(
            str(self.project), str(self.memory_home(self.project)),
        )
        adapter = ArkTSSemanticAdapter()
        caller_batch = adapter.index(runtime_project, [
            (self.project / "dispatch/Caller.ets").resolve(),
            (self.project / "dispatch/Contract.ets").resolve(),
        ])
        implementation_batch = adapter.index(
            runtime_project, [path.resolve() for path in implementations],
        )
        bounded_caller = SemanticBatch.from_dict(caller_batch.to_dict())
        bounded_implementations = SemanticBatch.from_dict(implementation_batch.to_dict())
        base_count = sum(
            item.relation != "dispatches_via" and item.evidence_class != "inferred"
            for item in bounded_caller.relations
        )
        relation_budget = base_count + 3
        with patch(
            "tools.agent_memory_runtime.semantic_dispatch_candidates.MAX_RELATIONS",
            relation_budget,
        ):
            expand_dispatch_candidates_across_batches([
                bounded_caller, bounded_implementations,
            ])
        bounded_inferred = [
            item for item in bounded_caller.relations if item.evidence_class == "inferred"
        ]

        self.assertLessEqual(len(bounded_caller.relations), relation_budget)
        self.assertEqual(2, len(bounded_inferred))

        expand_dispatch_candidates_across_batches([caller_batch, implementation_batch])

        inferred = [
            item for item in caller_batch.relations
            if item.relation == "calls" and item.evidence_class == "inferred"
        ]
        self.assertEqual(MAX_DISPATCH_CANDIDATES, len(inferred))
        self.assertIn(
            "dispatch_candidates_truncated",
            {item["kind"] for item in caller_batch.gaps},
        )

    def test_semantic_columns_belong_to_symbols_not_files(self) -> None:
        symbol_columns = {row[1] for row in self.db_rows("PRAGMA table_info(code_symbols)")}
        file_columns = {row[1] for row in self.db_rows("PRAGMA table_info(code_files)")}

        self.assertIn("symbol_key", symbol_columns)
        self.assertIn("semantic_adapter", symbol_columns)
        self.assertIn("mechanism_evidence", symbol_columns)
        self.assertNotIn("symbol_key", file_columns)

    def test_exact_edge_blocks_weaker_semantic_duplicate(self) -> None:
        runtime_project = resolve_project(str(self.project), str(self.memory_home(self.project)))
        timestamp = now_iso()
        with connect(runtime_project) as conn:
            conn.execute(
                """
                INSERT INTO memory_edges(
                  project_id, source_type, source_id, relation, target_type, target_id,
                  evidence_kind, extractor_version, created_at
                ) VALUES (?, 'code_symbol', 1, 'calls', 'code_symbol', 2,
                          'exact_semantic_calls', 'compiler@test', ?)
                """,
                (runtime_project.project_id, timestamp),
            )
            allowed = supersede_weaker_edge(
                conn, runtime_project.project_id,
                ("code_symbol", 1, "calls", "code_symbol", 2), "static", timestamp,
            )

        self.assertFalse(allowed)

    def test_learning_enriches_symbols_and_emits_semantic_edges(self) -> None:
        payload = self.learn_all()
        stats = payload["parse_stats"]["semantic_index"]
        symbols = self.db_rows(
            "SELECT * FROM code_symbols WHERE project_id = ? AND semantic_adapter IS NOT NULL",
            (self.project_id(self.project),),
        )
        edges = self.db_rows(
            """
            SELECT * FROM memory_edges
            WHERE project_id = ? AND valid_to IS NULL
              AND extractor_version LIKE 'semantic-index:%'
            """,
            (self.project_id(self.project),),
        )

        self.assertEqual("semantic-index/v1", stats["schema_version"])
        self.assertEqual("ArkTS", stats["adapters"][0]["language"])
        self.assertTrue(symbols)
        self.assertTrue(all(row["symbol_key"] and row["start_line"] for row in symbols))
        self.assertIn("calls", {row["relation"] for row in edges})
        self.assertIn("writes_state", {row["relation"] for row in edges})
        self.assertIn("registers_callback", {row["relation"] for row in edges})
        self.assertGreater(stats["mechanisms_extracted"], 0)
        self.assertTrue(all(row["evidence_kind"].startswith("static_semantic") for row in edges))

    def test_learning_persists_callable_owner_and_roles(self) -> None:
        self.learn_all()
        rows = self.db_rows(
            """
            SELECT owner_name, owner_kind, callable_roles
            FROM code_symbols
            WHERE project_id = ? AND qualified_name = 'ProfilePage.handleSave'
            """,
            (self.project_id(self.project),),
        )

        self.assertEqual("ProfilePage", rows[0]["owner_name"])
        self.assertEqual("component", rows[0]["owner_kind"])
        self.assertIn("state_write", json.loads(rows[0]["callable_roles"]))

    def test_static_async_arkts_methods_receive_semantic_identity(self) -> None:
        self.write_file(
            "service/StaticService.ets",
            """
export default class StaticService {
  static async queryAll(): Promise<void> {
    console.error('query failed')
  }
}
""",
        )
        self.write_file(
            "pages/StaticPage.ets",
            """
import StaticService from '../service/StaticService'
struct StaticPage {
  async aboutToAppear(): Promise<void> {
    await StaticService.queryAll()
  }
}
""",
        )

        self.learn_all()
        rows = self.db_rows(
            """
            SELECT qualified_name, start_line, semantic_adapter
            FROM code_symbols
            WHERE project_id = ? AND file_path = 'service/StaticService.ets'
              AND symbol = 'queryAll'
            """,
            (self.project_id(self.project),),
        )

        self.assertEqual("StaticService.queryAll", rows[0]["qualified_name"])
        self.assertTrue(rows[0]["start_line"])
        self.assertTrue(rows[0]["semantic_adapter"])
        edges = self.db_rows(
            """
            SELECT e.relation, source.qualified_name AS source_name,
                   target.qualified_name AS target_name
            FROM memory_edges e
            JOIN code_symbols source ON source.id = e.source_id
            JOIN code_symbols target ON target.id = e.target_id
            WHERE e.project_id = ? AND e.valid_to IS NULL
              AND e.relation = 'awaits'
              AND target.qualified_name = 'StaticService.queryAll'
            """,
            (self.project_id(self.project),),
        )
        self.assertEqual("StaticPage.aboutToAppear", edges[0]["source_name"])

    def test_symbol_edges_expand_change_impact_to_cross_file_caller(self) -> None:
        self.learn_all()

        result = self.run_memory(
            self.project, "impact-scope", "--files", "service/ProfileService.ets",
            "--query", "change profile loading", "--json",
        )
        summary = json.loads(result.stdout)["impact_summary"]

        self.assertTrue(any(
            link["source"] == "pages/ProfilePage.ets" and link["relation"] == "calls"
            for link in summary["reverse_dependents"]
        ))

    def test_architecture_slice_exposes_semantic_symbol_identity(self) -> None:
        self.learn_all()

        project = resolve_project(self.project, self.memory_home(self.project))
        payload = build_evidence_context(
            project, "Profile page service state", explicit_goal="design",
        )
        nodes = payload["architecture_slice"]["nodes"]
        semantic_symbols = [node for node in nodes if node.get("semantic_adapter")]

        self.assertTrue(semantic_symbols)
        self.assertTrue(all(node.get("qualified_name") for node in semantic_symbols))
        self.assertTrue(all((node.get("span") or {}).get("start_line") for node in semantic_symbols))

    def test_partial_relearn_restores_incoming_semantic_edge(self) -> None:
        self.learn_all()
        self.write_file(
            "service/ProfileService.ets",
            """
export class ProfileService {
  load(): string {
    console.error('profile load retry failed')
    return ''
  }
}
""",
        )

        result = self.run_memory(
            self.project, "learn-path", "--path", "service/ProfileService.ets", "--json",
        )
        stats = json.loads(result.stdout)["parse_stats"]
        edges = self.db_rows(
            """
            SELECT e.* FROM memory_edges e
            JOIN code_symbols source ON source.id = e.source_id
            JOIN code_symbols target ON target.id = e.target_id
            WHERE e.project_id = ? AND e.valid_to IS NULL AND e.relation = 'calls'
              AND source.file_path = 'pages/ProfilePage.ets'
              AND target.file_path = 'service/ProfileService.ets'
            """,
            (self.project_id(self.project),),
        )

        self.assertIn("pages/ProfilePage.ets", stats["reverse_dependents_reindexed"])
        self.assertTrue(edges)

    def test_typescript_adapter_uses_the_same_ir_contract(self) -> None:
        self.write_file(
            "typescript/task.ts",
            """
export class TaskRunner {
  helper(): void {}
  run(): void {
    this.helper()
  }
}
""",
        )

        payload = self.learn_all()
        adapters = payload["parse_stats"]["semantic_index"]["adapters"]
        edges = self.db_rows(
            """
            SELECT e.* FROM memory_edges e
            JOIN code_symbols source ON source.id = e.source_id
            WHERE e.project_id = ? AND e.valid_to IS NULL AND e.relation = 'calls'
              AND source.file_path = 'typescript/task.ts'
            """,
            (self.project_id(self.project),),
        )

        self.assertIn("TypeScript", {item["language"] for item in adapters})
        self.assertTrue(edges)


if __name__ == "__main__":
    import unittest

    unittest.main()
