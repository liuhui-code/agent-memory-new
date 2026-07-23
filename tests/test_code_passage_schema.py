# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.code_passages import create_code_passage_schema
from tools.agent_memory_runtime.storage import connect, ensure_initialized, resolve_project


class CodePassageSchemaTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name) / "passage-schema-project"
        root.mkdir()
        self.project = resolve_project(str(root), str(self.memory_home(root)))
        ensure_initialized(self.project)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_replaces_legacy_derived_schema_for_mechanism_field(self) -> None:
        with connect(self.project) as conn:
            conn.executescript(
                """
                DROP TRIGGER IF EXISTS code_passage_fts_ai;
                DROP TRIGGER IF EXISTS code_passage_fts_ad;
                DROP TRIGGER IF EXISTS code_passage_fts_au;
                DROP TABLE code_passage_fts;
                DROP TABLE code_passages;
                CREATE TABLE code_passages (
                  id INTEGER PRIMARY KEY,
                  project_id TEXT,
                  source_type TEXT,
                  source_id INTEGER,
                  passage_kind TEXT,
                  file_path TEXT,
                  identity_terms TEXT,
                  semantic_terms TEXT,
                  body_terms TEXT,
                  string_terms TEXT
                );
                CREATE VIRTUAL TABLE code_passage_fts USING fts5(
                  project_id UNINDEXED, source_type UNINDEXED,
                  passage_kind UNINDEXED, source_id UNINDEXED,
                  file_path, symbol, identity_terms, semantic_terms,
                  body_terms, string_terms
                );
                """
            )
            create_code_passage_schema(conn)
            columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(code_passages)")
            }
            fts_columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(code_passage_fts)")
            }
            create_code_passage_schema(conn)

        self.assertIn("mechanism_terms", columns)
        self.assertIn("mechanism_terms", fts_columns)


if __name__ == "__main__":
    unittest.main()
