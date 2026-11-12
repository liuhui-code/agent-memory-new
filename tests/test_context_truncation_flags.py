# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Independent development regressions for truthful Context truncation metadata."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.agent_memory_runtime.context_budget import enforce_budget, finalize_budget
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_source_excerpt import MAX_EXCERPT_LINES, read_excerpt
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "export function routeMessage(message: string): string {\n"
    "  return message.trim();\n"
    "}\n"
)


class SourceExcerptTruncationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="memory-excerpt-flags-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "source.ts"

    def read(self, content, start, end, budget=10000):
        self.path.write_text(content, encoding="utf-8")
        return read_excerpt(self.path, {"start_line": start, "end_line": end}, budget)

    def test_short_file_fully_returned_past_eof_is_not_truncated(self):
        excerpt = self.read(SOURCE, 1, 10)
        self.assertEqual(excerpt["content"], SOURCE.rstrip("\n"))
        self.assertEqual(excerpt["end_line"], 3)
        self.assertFalse(excerpt["truncated"])

    def test_tail_window_past_eof_is_not_truncated(self):
        excerpt = self.read("one\ntwo\nthree", 2, 12)
        self.assertEqual(excerpt["content"], "two\nthree")
        self.assertFalse(excerpt["truncated"])

    def test_eof_exactly_at_line_cap_is_not_truncated(self):
        excerpt = self.read("x\n" * MAX_EXCERPT_LINES, 1, MAX_EXCERPT_LINES + 10)
        self.assertEqual(excerpt["end_line"], MAX_EXCERPT_LINES)
        self.assertFalse(excerpt["truncated"])

    def test_real_line_cap_omission_is_truncated(self):
        excerpt = self.read("x\n" * (MAX_EXCERPT_LINES + 1), 1, MAX_EXCERPT_LINES + 10)
        self.assertEqual(excerpt["end_line"], MAX_EXCERPT_LINES)
        self.assertTrue(excerpt["truncated"])

    def test_real_character_budget_omission_is_truncated(self):
        excerpt = self.read("one\ntwo\nthree\n", 1, 10, budget=7)
        self.assertEqual(excerpt["content"], "one\ntwo")
        self.assertTrue(excerpt["truncated"])

    def test_exact_character_fit_is_not_truncated(self):
        excerpt = self.read("one\ntwo\n", 1, 2, budget=7)
        self.assertEqual(excerpt["content"], "one\ntwo")
        self.assertFalse(excerpt["truncated"])

    def test_requested_range_does_not_claim_to_return_whole_file(self):
        excerpt = self.read("one\ntwo\nthree\n", 1, 2)
        self.assertEqual(excerpt["content"], "one\ntwo")
        self.assertFalse(excerpt["truncated"])

    def test_start_beyond_eof_still_returns_no_excerpt(self):
        self.assertEqual(self.read("one\n", 2, 10), {})


class OutputBudgetTruncationTests(unittest.TestCase):
    @staticmethod
    def payload(query="message"):
        return {
            "query": query,
            "query_handoff": {
                "path_context": {"path_candidates": []}, "relation_hints": [],
                "code_anchors": [], "log_keywords": [], "log_anchors": [],
                "experience_refs": [], "semantic_refs": [],
            },
            "blocked_memory_notes": [], "conflict_notes": [],
            "correction_guards": [], "semantic_patch_notes": [],
        }

    def test_under_budget_compact_projection_is_not_truncation(self):
        payload = compact_context({"query": "message", "unused_full_record": "full context"})
        self.assertNotIn("unused_full_record", payload)
        self.assertLess(payload["output_budget"]["estimated_tokens"], 1500)
        self.assertFalse(payload["output_budget"]["truncated"])
        self.assertEqual(payload["output_budget"]["estimated_tokens"], estimate_payload_tokens(payload))

    def test_final_budget_reduction_remains_truncated(self):
        payload = {"query_handoff": {}, "query": "a" * 240}
        original = deepcopy(payload)
        finalize_budget(payload, 65)
        self.assertNotEqual(payload["query"], original["query"])
        self.assertTrue(payload["output_budget"]["truncated"])
        self.assertLessEqual(estimate_payload_tokens(payload), 65)

    def test_early_budget_reduction_survives_finalizer_with_room(self):
        payload = self.payload()
        payload["query_handoff"]["relation_hints"] = [{"summary": "x" * 500}] * 3
        reduced = enforce_budget(payload, estimate_payload_tokens(payload) - 50, reserve_tokens=0)
        self.assertTrue(reduced)
        self.assertEqual(len(payload["query_handoff"]["relation_hints"]), 2)
        finalize_budget(payload, 1500, truncated=reduced)
        self.assertLess(payload["output_budget"]["estimated_tokens"], 1500)
        self.assertTrue(payload["output_budget"]["truncated"])

    def test_noop_budget_pass_is_not_truncation_even_over_target(self):
        payload = self.payload(query="x" * 8000)
        original = deepcopy(payload)
        self.assertFalse(enforce_budget(payload, 100, reserve_tokens=0))
        self.assertEqual(payload, original)

    def test_finalizer_reentry_preserves_previous_actual_reduction(self):
        payload = {"query_handoff": {}, "query": "a" * 240}
        finalize_budget(payload, 65)
        finalize_budget(payload, 1500)
        self.assertTrue(payload["output_budget"]["truncated"])
        self.assertEqual(payload["output_budget"]["estimated_tokens"], estimate_payload_tokens(payload))

    def test_only_normalizing_empty_fields_does_not_claim_clipping(self):
        payload = self.payload(query="x" * 8000)
        payload["query_handoff"]["path_context"]["path_candidates"] = [{}]
        self.assertFalse(enforce_budget(payload, 100, reserve_tokens=0))

    def test_compact_context_accumulates_earlier_budget_pass(self):
        module = "tools.agent_memory_runtime.context_compact"
        with patch(f"{module}.has_source_excerpt_candidate", return_value=True), patch(
            f"{module}.enforce_budget", side_effect=[True, False],
        ):
            payload = compact_context({"query": "message"})
        self.assertTrue(payload["output_budget"]["truncated"])


class PublicContextTruncationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="memory-public-flags-")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        self.project.mkdir()
        self.memory = Path(self.temp.name) / "memory"
        (self.project / "routing.ts").write_text(SOURCE, encoding="utf-8")
        self.run_cli("init")

    def run_cli(self, *args):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/agent_memory.py"), *args,
             "--project", str(self.project), "--memory-home", str(self.memory)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout) if "--json" in args else result.stdout

    def test_empty_archive_compact_context_is_not_truncated(self):
        payload = self.run_cli("context", "--query", "routeMessage", "--compact", "--json")
        self.assertEqual(payload["query_handoff"]["code_anchors"], [])
        self.assertLess(payload["output_budget"]["estimated_tokens"], 700)
        self.assertFalse(payload["output_budget"]["truncated"])

    def test_public_handoff_full_short_source_is_not_truncated(self):
        self.run_cli("learn-path", "--path", ".", "--json")
        payload = self.run_cli("context", "--query", "message trim", "--compact", "--json")
        excerpts = [
            excerpt for anchor in payload["query_handoff"]["code_anchors"]
            for excerpt in anchor.get("source_excerpts", [])
        ]
        self.assertEqual(len(excerpts), 1)
        self.assertEqual(excerpts[0]["content"], SOURCE.rstrip("\n"))
        self.assertFalse(excerpts[0]["truncated"])
        self.assertFalse(payload["output_budget"]["truncated"])


if __name__ == "__main__":
    unittest.main()
