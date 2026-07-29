# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.agent_memory_runtime.context_source_excerpt import (
    focused_source_range,
    selected_ranges,
)
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_budget import finalize_budget
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens


class ContextSourceExcerptQualityTests(unittest.TestCase):
    def test_finalizer_does_not_repeat_coarse_anchor_reduction(self) -> None:
        anchors = [
            {
                "file_path": f"src/Owner{index}.ets",
                "role": "primary",
                "source_excerpts": [{
                    "content": "bounded source evidence " * 80,
                    "start_line": 1,
                    "end_line": 20,
                    "selection_reason": "anchor_range",
                }],
            }
            for index in range(3)
        ]
        payload = {
            "query": "retain all three primary evidence owners",
            "query_handoff": {
                "code_anchors": anchors,
                "log_keywords": [],
                "log_anchors": [],
                "relation_hints": [],
                "semantic_refs": [],
                "experience_refs": [],
                "next_queries": [],
                "path_context": {"path_candidates": []},
            },
            "source_freshness": {},
            "blocked_memory_notes": [],
            "conflict_notes": [],
            "semantic_patch_notes": [],
        }

        finalize_budget(payload, 1500)

        self.assertEqual(3, len(payload["query_handoff"]["code_anchors"]))
        self.assertLessEqual(payload["output_budget"]["estimated_tokens"], 1500)
        self.assertEqual(
            estimate_payload_tokens(payload),
            payload["output_budget"]["estimated_tokens"],
        )

    def test_finalizer_drops_static_expansion_before_main_experience(self) -> None:
        payload = {
            "query": "apply bounded session recovery experience",
            "query_handoff": {
                "code_anchors": [],
                "log_keywords": [],
                "log_anchors": [],
                "relation_hints": [],
                "semantic_refs": [],
                "experience_refs": [
                    {"task": "bounded session retry workflow", "lesson": "refresh once"},
                    {"task": "session recovery guard", "lesson": "require login"},
                ],
                "next_queries": [],
                "path_context": {"path_candidates": []},
            },
            "source_freshness": {},
            "blocked_memory_notes": [],
            "conflict_notes": [],
            "semantic_patch_notes": [],
            "expansion": {
                "command": "python tools/agent_memory.py context --project . --query <term>",
                "use_when": "inspect ranking audit and unresolved candidates",
            },
        }
        target = estimate_payload_tokens(payload) + 5

        finalize_budget(payload, target)

        self.assertNotIn("expansion", payload)
        self.assertEqual(2, len(payload["query_handoff"]["experience_refs"]))
        self.assertLessEqual(payload["output_budget"]["estimated_tokens"], target)

    def test_finalizer_can_shrink_small_excerpts_without_dropping_anchors(self) -> None:
        anchors = [
            {
                "file_path": f"src/SmallOwner{index}.ets",
                "role": "primary",
                "read_window": {"start_line": 1, "end_line": 40},
                "source_ranges": [{
                    "symbol": f"owner{index}", "start_line": 10, "end_line": 12,
                }],
                "source_excerpts": [{
                    "content": "source evidence " * 10,
                    "source": "current_worktree",
                    "symbol": f"owner{index}",
                    "start_line": 10,
                    "end_line": 12,
                    "selection_reason": "anchor_range",
                    "truncated": False,
                }],
            }
            for index in range(3)
        ]
        payload = {
            "query": "retain three bounded source owners",
            "query_handoff": {
                "code_anchors": anchors,
                "log_keywords": [],
                "log_anchors": [],
                "relation_hints": [],
                "semantic_refs": [],
                "experience_refs": [],
                "next_queries": [],
                "path_context": {"path_candidates": []},
            },
            "source_freshness": {},
            "blocked_memory_notes": [],
            "conflict_notes": [],
            "semantic_patch_notes": [],
        }
        target = estimate_payload_tokens(payload) + 5

        finalize_budget(payload, target)

        self.assertEqual(3, len(payload["query_handoff"]["code_anchors"]))
        self.assertTrue(all(anchor.get("source_excerpts") for anchor in anchors))
        self.assertLessEqual(payload["output_budget"]["estimated_tokens"], target)

    def test_event_owner_reason_survives_duplicate_mechanism_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Owner.ets"
            source.write_text("\n".join("const value = 1;" for _ in range(30)), encoding="utf-8")
            owner = {
                "symbol": "restore",
                "start_line": 10,
                "end_line": 20,
                "selection_reason": "selected_log_event_owner",
                "focus_line": 15,
            }
            with patch(
                "tools.agent_memory_runtime.context_source_excerpt.mechanism_callable_ranges",
                return_value=[{"symbol": "restore", "start_line": 10, "end_line": 20}],
            ):
                ranges = selected_ranges(
                    {"source_ranges": [owner]}, source, "restore rejected payload"
                )

        self.assertEqual("selected_log_event_owner", ranges[0]["selection_reason"])
        self.assertEqual(15, ranges[0]["focus_line"])

    def test_exact_log_event_owner_controls_source_passage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src" / "RestoreCoordinator.ets"
            source.parent.mkdir(parents=True)
            lines = ["const unrelatedRestoreContext = true;" for _ in range(120)]
            lines[14] = "export class RestoreCoordinator {"
            lines[68] = "  async restoreSnapshot(snapshotId: string): Promise<void> {"
            lines[72] = (
                "    Logger.error(`RESTORE_EVENT_71A9 rejected snapshot ${snapshotId}`);"
            )
            lines[76] = "  }"
            source.write_text("\n".join(lines) + "\n", encoding="utf-8")

            compact = compact_context({
                "project_path": str(root),
                "query": (
                    "RESTORE_EVENT_71A9 rejected snapshot snap-44 while a later "
                    "runtime observation mentions stale archive metadata"
                ),
                "query_handoff": {
                    "log_keywords": ["RESTORE_EVENT_71A9"],
                    "log_anchors": [{
                        "message_template": "RESTORE_EVENT_71A9 rejected snapshot ${snapshotId}",
                        "file_path": "src/RestoreCoordinator.ets",
                        "function": "restoreSnapshot",
                        "line": 73,
                        "evidence_class": "static_wrapped",
                    }],
                    "code_anchors": [{
                        "source": "wiki",
                        "file_path": "src/RestoreCoordinator.ets",
                        "symbol": "RestoreCoordinator",
                        "symbol_type": "class",
                        "start_line": 1,
                        "end_line": 120,
                    }],
                    "path_context": {"activated": False, "path_candidates": []},
                },
            })

        excerpt = compact["query_handoff"]["code_anchors"][0]["source_excerpts"][0]
        self.assertLessEqual(excerpt["start_line"], 73)
        self.assertGreaterEqual(excerpt["end_line"], 73)
        self.assertEqual("selected_log_event_owner", excerpt["selection_reason"])
        self.assertIn("RESTORE_EVENT_71A9", excerpt["content"])

    def test_final_budget_accounts_for_output_metadata_and_keeps_event_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src" / "BudgetedEmitter.ets"
            source.parent.mkdir(parents=True)
            lines = [f"const verboseLine{index} = '{'bounded context ' * 8}';" for index in range(140)]
            lines[79] = "Logger.error('BUDGET_EVENT_82B4 persistence failed');"
            source.write_text("\n".join(lines) + "\n", encoding="utf-8")
            long_text = "persistence failure transaction recovery context " * 18
            compact = compact_context({
                "project_path": str(root),
                "query": f"BUDGET_EVENT_82B4 persistence failed {long_text}",
                "query_handoff": {
                    "log_keywords": long_text.split(),
                    "log_anchors": [{
                        "message_template": "BUDGET_EVENT_82B4 persistence failed",
                        "file_path": "src/BudgetedEmitter.ets",
                        "function": "persist",
                        "line": 80,
                        "evidence_class": "static_wrapped",
                    } for _ in range(3)],
                    "code_anchors": [{
                        "source": "wiki",
                        "file_path": "src/BudgetedEmitter.ets",
                        "symbol": "BudgetedEmitter",
                        "start_line": 1,
                        "end_line": 140,
                        "summary": long_text,
                    }],
                    "path_context": {"activated": False, "path_candidates": []},
                },
            })

        self.assertLessEqual(compact["output_budget"]["estimated_tokens"], 1500)
        self.assertEqual(
            estimate_payload_tokens(compact),
            compact["output_budget"]["estimated_tokens"],
        )
        excerpts = compact["query_handoff"]["code_anchors"][0]["source_excerpts"]
        self.assertEqual("selected_log_event_owner", excerpts[0]["selection_reason"])
        self.assertIn("BUDGET_EVENT_82B4", excerpts[0]["content"])

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
