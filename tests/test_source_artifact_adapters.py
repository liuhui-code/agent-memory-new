# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_collect import collect_matches
from tools.agent_memory_runtime.query_results import limited_context
from tools.agent_memory_runtime.semantic_runtime import run_semantic_adapter
from tools.agent_memory_runtime.source_adapters import source_profile_for
from tools.agent_memory_runtime.source_static_extractors import build_symbols
from tools.agent_memory_runtime.storage import resolve_project


class SourceArtifactAdapterTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "native-boundary"
        self.project.mkdir()
        self.write_fixture()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write(self, relative: str, content: str) -> None:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")

    def write_fixture(self) -> None:
        self.write(
            "entry/src/main/ets/pages/Index.ets",
            """
import bridge from 'libentry.so'
export function launch(): void { bridge.run() }
""",
        )
        self.write(
            "entry/src/main/cpp/CMakeLists.txt",
            """
project(NativeBoundary)
add_library(
  entry
  SHARED
  napi_init.cpp
  terminal.cpp
)
""",
        )
        self.write(
            "entry/src/main/cpp/napi_init.cpp",
            """
#include "terminal.h"
static int Run() {
  Start();
  return 0;
}
""",
        )
        self.write(
            "entry/src/main/cpp/terminal.cpp",
            """
#define LOG_ERROR(...) logger(__VA_ARGS__)
void terminal_context::Fork() {
  execl("/data/app/bin/bash", "/data/app/bin/bash", nullptr);
  LOG_ERROR("EXEC FAILED: errno=%d (Permission denied)", errno);
}
void Start() {
  terminal_context context;
  context.Fork();
}
""",
        )
        self.write("entry/src/main/cpp/terminal.h", "void Start();")
        self.write(
            "entry/src/main/module.json5",
            '{"module":{"hnpPackages":[{"package":"base.hnp","type":"private"}]}}',
        )
        self.write(
            "build-hnp/Makefile",
            """
all: base.hnp
base.hnp: shell.stamp
	cp shell-root base.hnp
""",
        )
        self.write("build-ohos.sh", "build_native() { echo native; }")

    def rows(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        db = self.project_memory_dir(self.project) / "memory.db"
        with sqlite3.connect(db) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(query, params).fetchall()

    def test_classifies_native_and_build_artifacts(self) -> None:
        expected = {
            "source.cc": ("C/C++", "source"),
            "source.cpp": ("C/C++", "source"),
            "Makefile": ("Build Artifact", "build"),
            "build-ohos.sh": ("Build Artifact", "build"),
        }
        for name, values in expected.items():
            with self.subTest(name=name):
                profile = source_profile_for(Path(name))
                self.assertIsNotNone(profile)
                self.assertEqual(values, (profile.language, profile.artifact_role))

    def test_static_provider_disambiguates_conditional_duplicate_definitions(self) -> None:
        self.write(
            "duplicate.cpp",
            """
#ifdef FIRST
void Launch() { Start(); }
#else
void Launch() { Start(); }
#endif
""",
        )
        runtime_project = resolve_project(
            str(self.project), str(self.memory_home(self.project)),
        )

        batch = run_semantic_adapter(
            runtime_project, "C/C++", [self.project / "duplicate.cpp"],
        ).batch

        launches = [entity for entity in batch.entities if entity.name == "Launch"]
        self.assertEqual(2, len(launches))
        self.assertEqual(2, len({entity.key for entity in launches}))

    def test_static_provider_locates_multiline_native_and_build_definitions(self) -> None:
        self.write(
            "multiline.cc",
            """
static Napi::External<SherpaOnnxOfflineTts>
CreateOfflineTtsWrapper(
    const Napi::CallbackInfo &info) {
  return SherpaOnnxCreateOfflineTtsOHOS(config, manager);
}

const SherpaOnnxOfflineTts *
SherpaOnnxCreateOfflineTtsOHOS(
    const SherpaOnnxOfflineTtsConfig *config,
    NativeResourceManager *manager) {
  return CreateOfflineTts(config);
}
""",
        )
        self.write(
            "runtime-version.sh",
            """
onnxruntime_version=1.16.3
build_runtime() {
  echo "$onnxruntime_version"
}
""",
        )
        runtime_project = resolve_project(
            str(self.project), str(self.memory_home(self.project)),
        )

        native = run_semantic_adapter(
            runtime_project, "C/C++", [self.project / "multiline.cc"],
        ).batch
        build = run_semantic_adapter(
            runtime_project, "Build Artifact", [self.project / "runtime-version.sh"],
        ).batch

        by_name = {entity.name: entity for entity in native.entities}
        self.assertEqual(
            (1, 5),
            (by_name["CreateOfflineTtsWrapper"].start_line,
             by_name["CreateOfflineTtsWrapper"].end_line),
        )
        self.assertEqual(
            (7, 12),
            (by_name["SherpaOnnxCreateOfflineTtsOHOS"].start_line,
             by_name["SherpaOnnxCreateOfflineTtsOHOS"].end_line),
        )
        self.assertIn(
            (by_name["CreateOfflineTtsWrapper"].key,
             "SherpaOnnxCreateOfflineTtsOHOS"),
            {(relation.source_key, relation.target_name)
             for relation in native.relations},
        )
        version = next(
            entity for entity in build.entities
            if entity.name == "onnxruntime_version"
        )
        self.assertEqual((1, 1), (version.start_line, version.end_line))
        self.assertEqual("build_variable", version.kind)
        self.assertEqual(
            {("onnxruntime_version", "build_variable"),
             ("build_runtime", "build_target")},
            set(build_symbols((self.project / "runtime-version.sh").read_text())),
        )

    def test_indexes_native_logs_spans_calls_and_artifact_boundaries(self) -> None:
        result = self.run_memory(
            self.project, "learn-path", "--path", ".", "--json",
        )
        stats = json.loads(result.stdout)["parse_stats"]

        self.assertGreaterEqual(stats["languages"]["C/C++"], 3)
        self.assertGreaterEqual(stats["languages"]["Build Artifact"], 3)
        symbols = self.rows(
            "SELECT symbol, symbol_type, start_line, end_line, semantic_adapter "
            "FROM code_symbols WHERE symbol IN ('Run', 'Fork', 'Start', 'entry', 'base.hnp')"
        )
        by_name = {row["symbol"]: row for row in symbols}
        self.assertEqual("cpp-static@1.0", by_name["Run"]["semantic_adapter"])
        self.assertGreater(by_name["Fork"]["end_line"], by_name["Fork"]["start_line"])
        self.assertIn(
            ("base.hnp", "build_target"),
            {(row["symbol"], row["symbol_type"]) for row in symbols},
        )

        logs = self.rows(
            "SELECT function, level, message_template FROM code_log_statements "
            "WHERE message_template LIKE 'EXEC FAILED%'"
        )
        self.assertEqual(("Fork", "error"), (logs[0]["function"], logs[0]["level"]))

        edges = self.edge_paths()
        self.assertIn(
            ("entry/src/main/ets/pages/Index.ets", "imports", "entry/src/main/cpp/napi_init.cpp"),
            edges,
        )
        self.assertIn(
            ("entry/src/main/cpp/terminal.cpp", "configured_by", "entry/src/main/cpp/CMakeLists.txt"),
            edges,
        )
        self.assertIn(
            ("entry/src/main/module.json5", "configured_by", "build-hnp/Makefile"),
            edges,
        )
        call_count = self.rows(
            "SELECT COUNT(*) AS count FROM memory_edges "
            "WHERE valid_to IS NULL AND relation = 'calls'"
        )[0]["count"]
        self.assertGreaterEqual(call_count, 2)

        query = "EXEC FAILED errno permission denied bash launch"
        runtime_project = resolve_project(
            str(self.project), str(self.memory_home(self.project)),
        )
        raw_paths = {
            item.get("file_path")
            for item in collect_matches(runtime_project, query)["wiki_matches"]
        }
        self.assertIn("entry/src/main/cpp/CMakeLists.txt", raw_paths, raw_paths)
        handoff_paths = {
            item.get("file_path")
            for item in limited_context(runtime_project, query)["query_handoff"]["code_anchors"]
        }
        self.assertIn("entry/src/main/cpp/CMakeLists.txt", handoff_paths, handoff_paths)
        context = json.loads(self.run_memory(
            self.project,
            "context",
            "--query",
            query,
            "--compact",
            "--json",
        ).stdout)["query_handoff"]
        anchor_paths = {item["file_path"] for item in context["code_anchors"]}
        self.assertIn("entry/src/main/cpp/terminal.cpp", anchor_paths)
        self.assertIn("entry/src/main/cpp/CMakeLists.txt", anchor_paths, context)

    def test_incremental_arkts_refresh_does_not_duplicate_boundary_edges(self) -> None:
        self.run_memory(self.project, "learn-path", "--path", ".")
        before = self.boundary_edge_count()

        self.run_memory(
            self.project,
            "learn-path",
            "--path",
            "entry/src/main/ets/pages/Index.ets",
        )

        self.assertEqual(before, self.boundary_edge_count())

    def edge_paths(self) -> set[tuple[str, str, str]]:
        rows = self.rows(
            "SELECT source.file_path AS source_path, edges.relation, "
            "target.file_path AS target_path FROM memory_edges edges "
            "JOIN code_files source ON source.id = edges.source_id "
            "JOIN code_files target ON target.id = edges.target_id "
            "WHERE edges.source_type = 'code_file' AND edges.target_type = 'code_file' "
            "AND edges.valid_to IS NULL"
        )
        return {
            (str(row["source_path"]), str(row["relation"]), str(row["target_path"]))
            for row in rows
        }

    def boundary_edge_count(self) -> int:
        return int(self.rows(
            "SELECT COUNT(*) AS count FROM memory_edges WHERE valid_to IS NULL "
            "AND relation IN ('imports', 'configured_by')"
        )[0]["count"])


if __name__ == "__main__":
    import unittest

    unittest.main()
