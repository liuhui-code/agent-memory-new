# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from examples.ollama_benchmark_tools import SourceToolExecutor
from tools.agent_memory_runtime.source_exploration import (
    SOURCE_READ_LINE_LIMIT,
    SOURCE_READS_PER_FILE_LIMIT,
    SOURCE_SEARCH_LIMIT,
)


class OllamaBenchmarkToolTests(unittest.TestCase):
    def test_read_rejects_path_escape_and_enforces_budgets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            source = workspace / "Cause.ets"
            source.write_text("one\ntwo\nthree\n", encoding="utf-8")
            (workspace / "binary.bin").write_bytes(b"visible\x00hidden")
            executor = SourceToolExecutor(workspace)

            escaped = tool_result(executor.execute("read_source", {
                "path": "../secret.txt", "start_line": 1, "end_line": 1,
            }))
            oversized = tool_result(executor.execute("read_source", {
                "path": "Cause.ets",
                "start_line": 1,
                "end_line": SOURCE_READ_LINE_LIMIT + 1,
            }))
            self.assertIn("escapes", escaped["error"])
            self.assertIn("lines", oversized["error"])
            binary = tool_result(executor.execute("read_source", {
                "path": "binary.bin", "start_line": 1, "end_line": 1,
            }))
            self.assertIn("binary-like", binary["error"])
            self.assertNotIn("binary.bin", executor.investigated_files)

            for index in range(SOURCE_READS_PER_FILE_LIMIT):
                value = tool_result(executor.execute("read_source", {
                    "path": "Cause.ets",
                    "start_line": "1" if index == 0 else 1,
                    "end_line": "1" if index == 0 else 1,
                }))
                self.assertIn("content", value)
            limited = tool_result(executor.execute("read_source", {
                "path": "Cause.ets", "start_line": 1, "end_line": 1,
            }))
            self.assertIn("read limit", limited["error"])
            self.assertEqual(["Cause.ets"], executor.investigated_files)

    def test_search_is_literal_bounded_and_skips_external_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "Cause.ets").write_text("literal [term]\n", encoding="utf-8")
            secret = root / "secret.txt"
            secret.write_text("literal [term] outside\n", encoding="utf-8")
            try:
                (workspace / "linked.txt").symlink_to(secret)
            except OSError:
                pass
            executor = SourceToolExecutor(workspace)

            result = tool_result(executor.execute("search_source", {"query": "[term]"}))
            self.assertEqual(["Cause.ets"], [item["path"] for item in result["matches"]])

            for _ in range(SOURCE_SEARCH_LIMIT - 1):
                executor.execute("search_source", {"query": "absent"})
            limited = tool_result(executor.execute("search_source", {"query": "again"}))
            self.assertIn("search limit", limited["error"])
            telemetry = executor.telemetry()
            self.assertEqual(SOURCE_SEARCH_LIMIT + 1, telemetry["source_search_count"])
            self.assertEqual(SOURCE_SEARCH_LIMIT - 1, telemetry["source_search_miss_count"])
            self.assertEqual(1, telemetry["source_search_error_count"])


def tool_result(value: str) -> dict:
    return json.loads(value)
