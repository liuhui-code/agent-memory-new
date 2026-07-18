# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.agent_memory_runtime.context_source_excerpt import (
    focused_source_range,
    selected_ranges,
)
from tools.agent_memory_runtime.context_compact import compact_context


class ContextSourceExcerptQualityTests(unittest.TestCase):
    def test_query_terms_focus_excerpt_away_from_weak_anchor_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Login.ets"
            lines = ["const filler = 1;" for _ in range(50)]
            lines[34] = "Button('Sign in').onClick(async () => {"
            lines[39] = "const result = await login(this.phone);"
            lines[42] = "this.pageInfo.pushPath({ name: 'VerifyCode' });"
            source.write_text("\n".join(lines) + "\n", encoding="utf-8")

            focused = focused_source_range(
                source,
                {"symbol": "Stack", "start_line": 2, "end_line": 2},
                "duplicate login request causes conflicting navigation",
            )

        self.assertLessEqual(focused["start_line"], 40)
        self.assertGreaterEqual(focused["end_line"], 40)
        self.assertEqual("query_term_window", focused["selection_reason"])
        self.assertNotIn("symbol", focused)

    def test_no_query_match_preserves_original_anchor_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Profile.ets"
            source.write_text("const value = 1;\n", encoding="utf-8")
            anchor = {"source_ranges": [{"symbol": "Profile", "start_line": 1, "end_line": 1}]}

            ranges = selected_ranges(anchor, source, "unmatched-zxqv identifier")

        self.assertEqual(1, ranges[0]["start_line"])
        self.assertEqual("Profile", ranges[0]["symbol"])

    def test_action_window_outranks_matching_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Password.ets"
            lines = ["import { LoginState } from 'auth';", *("const filler = 1;" for _ in range(50))]
            lines[34] = "Button('Sign in').onClick(async () => {"
            lines[38] = "Logger.debug('Login/Password');"
            lines[39] = "const result = await password(this.password);"
            source.write_text("\n".join(lines) + "\n", encoding="utf-8")

            focused = focused_source_range(
                source,
                {"symbol": "Password", "start_line": 1, "end_line": 50},
                "Repeated login actions can start duplicate requests.",
            )

        self.assertGreater(focused["start_line"], 20)
        self.assertLessEqual(focused["start_line"], 35)

    def test_log_dense_context_reserves_one_current_source_window(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src" / "AttachmentTile.ets"
            source.parent.mkdir(parents=True)
            lines = ["const filler = 'bounded';" for _ in range(100)]
            lines[64] = "Logger.error('attachment download failed after cache write');"
            lines[68] = "this.mediaLoaded = fileExists(this.cachedPath);"
            source.write_text("\n".join(lines) + "\n", encoding="utf-8")
            long_text = "download failure cache state async boundary " * 12
            path = {
                "path_id": "attachment-path",
                "entry": {"file_path": "src/AttachmentTile.ets", "name": "AttachmentTile"},
                "emitter": {"file_path": "src/AttachmentTile.ets", "name": "loadAttachment"},
                "nodes": [
                    {"file_path": "src/AttachmentTile.ets", "name": f"node{index}"}
                    for index in range(6)
                ],
                "edges": [
                    {"relation": "calls", "evidence_class": "static", "confidence": 0.8}
                    for _ in range(5)
                ],
                "expected_log_anchors": [
                    {"message_template": long_text, "function": "loadAttachment"}
                    for _ in range(4)
                ],
                "uncertainty": [long_text, long_text],
            }
            compact = compact_context({
                "project_path": str(root),
                "query": "attachment download reports failure after cached file is usable",
                "query_handoff": {
                    "log_keywords": long_text.split(),
                    "log_anchors": [
                        {
                            "message_template": long_text,
                            "file_path": "src/AttachmentTile.ets",
                            "function": "loadAttachment",
                        }
                        for _ in range(3)
                    ],
                    "code_anchors": [{
                        "source": "wiki",
                        "file_path": "src/AttachmentTile.ets",
                        "symbol": "AttachmentTile",
                        "symbol_type": "component",
                        "start_line": 1,
                        "end_line": 100,
                    }],
                    "path_context": {
                        "activated": True,
                        "path_candidates": [path, {**path, "path_id": "second"}],
                    },
                },
            })

        anchors = compact["query_handoff"]["code_anchors"]
        self.assertTrue(anchors[0].get("source_excerpts"))
        self.assertLessEqual(compact["output_budget"]["estimated_tokens"], 1500)


if __name__ == "__main__":
    unittest.main()
