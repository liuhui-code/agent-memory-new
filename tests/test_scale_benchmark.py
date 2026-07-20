# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.cli import build_parser
from tools.agent_memory_runtime.runtime_entry import command_handlers
from tools.agent_memory_runtime.scale_benchmark import (
    ScaleProfile,
    profile_counts,
    run_scale_benchmark,
)
from tools.agent_memory_runtime.storage import connect, ensure_initialized, resolve_project


class ScaleBenchmarkTests(unittest.TestCase):
    def test_profile_counts_keep_entities_separate_from_edges(self) -> None:
        profile = ScaleProfile("tiny", 1_000, 3_000, 2)

        self.assertEqual(
            {
                "searchable_entities": 1_000,
                "code_files": 50,
                "code_symbols": 800,
                "code_log_statements": 150,
                "memory_edges": 3_000,
            },
            profile_counts(profile),
        )

    def test_tiny_profile_passes_latency_and_query_plan_gates(self) -> None:
        report = run_scale_benchmark(ScaleProfile("tiny", 1_000, 3_000, 2))

        self.assertEqual("scale-benchmark/v1", report["schema_version"])
        self.assertEqual(report["configured_counts"], report["observed_counts"])
        self.assertEqual("pass", report["status"])
        self.assertTrue(report["gates"]["latency"])
        self.assertTrue(report["gates"]["query_plan"])
        self.assertTrue(report["gates"]["incremental_maintenance"])
        self.assertGreater(report["database_bytes"], 0)
        self.assertEqual(
            {
                "candidate_recall_hit",
                "candidate_recall_miss",
                "generic_symbol_abstention",
                "exact_log_fts",
                "qualified_symbol_lookup",
                "file_symbols",
                "outgoing_edges",
                "incoming_edges",
            },
            set(report["operations"]),
        )
        self.assertTrue(all(item["pass"] for item in report["query_plans"].values()))
        maintenance = report["incremental_maintenance"]
        self.assertEqual("pass", maintenance["status"])
        self.assertEqual(
            {
                "incremental_no_change",
                "incremental_outside_scope",
                "incremental_single_file",
                "incremental_large_method_file",
            },
            set(maintenance["operations"]),
        )
        self.assertTrue(
            all(item["evidence_pass"] for item in maintenance["operations"].values())
        )

    def test_generic_method_term_abstains_and_camel_case_is_indexable(self) -> None:
        from unittest.mock import MagicMock

        from tools.agent_memory_runtime.code_wiki_extractors import summarize_symbol
        from tools.agent_memory_runtime.query_candidate_recall import (
            fts_match_expression,
            like_fallback_allowed,
        )

        self.assertIsNone(fts_match_expression("method"))
        summary = summarize_symbol(
            "src/Payment.ets", "CriticalPaymentRetryHandler", "function", "ArkTS"
        )
        self.assertIn("critical payment retry handler", summary)
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = {"high_watermark": 50_001}
        self.assertFalse(like_fallback_allowed(conn, "code_symbols"))

    def test_cli_exposes_scale_profiles_without_new_skill(self) -> None:
        parser = build_parser(command_handlers())

        args = parser.parse_args(["eval-scale", "--profile", "million", "--json"])

        self.assertEqual("eval-scale", args.command)
        self.assertEqual("million", args.profile)
        self.assertTrue(args.json)

    def test_qualified_symbol_lookup_index_is_installed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            project = resolve_project(str(root), str(Path(directory) / "memory"))
            ensure_initialized(project)
            with connect(project) as conn:
                indexes = {
                    str(row[1]) for row in conn.execute("PRAGMA index_list(code_symbols)")
                }

        self.assertIn("idx_code_symbols_project_qualified_lookup", indexes)


if __name__ == "__main__":
    unittest.main()
