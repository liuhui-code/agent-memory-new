# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.context_anchor_selection import (
    exact_log_identity,
    path_scoped_code_anchors,
    relevant_log_anchors,
)
from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors
from tools.agent_memory_runtime.context_budget import bounded_log_evidence


class ContextLogAlignmentTests(unittest.TestCase):
    def test_exact_log_phrase_keeps_all_matching_paths_and_drops_other_messages(self) -> None:
        logs = [
            log("DISPATCH_PROFILE_8A21 load failed", "src/Dispatch.ets", "run", "inferred_wrapped"),
            log("DISPATCH_PROFILE_8A21 load failed", "src/Dispatch.ets", "run", "inferred_wrapped"),
            log("WRAP_PROFILE_7F19 load failed", "src/Wrapped.ets", "load", "static_wrapped"),
        ]

        selected = relevant_log_anchors(
            logs,
            "The observed runtime line is DISPATCH_PROFILE_8A21 load failed; return candidates.",
        )

        self.assertEqual(logs[:2], selected)
        self.assertTrue(exact_log_identity(logs[0], "DISPATCH_PROFILE_8A21 load failed"))

    def test_short_generic_message_does_not_trigger_exact_cascade(self) -> None:
        logs = [
            log("error", "src/A.ets", "a", "direct"),
            log("error while loading", "src/B.ets", "b", "direct"),
        ]

        self.assertEqual(logs, relevant_log_anchors(logs, "runtime error"))
        self.assertFalse(exact_log_identity(logs[0], "runtime error"))

    def test_exact_log_callers_scope_code_anchors_before_callable_focus(self) -> None:
        logs = [
            log("DISPATCH_PROFILE_8A21 load failed", "src/Dispatch.ets", "run", "inferred_wrapped"),
            log("DISPATCH_PROFILE_8A21 load failed", "src/Dispatch.ets", "run", "inferred_wrapped"),
        ]
        anchors = [
            anchor("src/Wrapped.ets", "load"),
            anchor("src/Dispatch.ets", "run", source="wrapped_log_caller"),
        ]
        query = "DISPATCH_PROFILE_8A21 load failed"

        scoped = path_scoped_code_anchors(anchors, inactive_path(), logs, query)
        focused = focus_callable_anchors(
            scoped,
            {
                "certainty": "bounded",
                "primary": {
                    "file_path": "src/Wrapped.ets",
                    "source_range": {"start_line": 1, "end_line": 4},
                },
            },
            False,
        )

        self.assertEqual(["src/Dispatch.ets"], [item["file_path"] for item in scoped])
        self.assertTrue(scoped[0]["log_identity_match"])
        self.assertEqual(scoped, focused)

    def test_activated_structural_path_remains_the_primary_scope(self) -> None:
        anchors = [anchor("src/Entry.ets", "start"), anchor("src/Log.ets", "emit")]
        path = {
            "activated": True,
            "path_candidates": [{
                "entry": {"file_path": "src/Entry.ets"},
                "emitter": {"file_path": "src/Log.ets"},
                "nodes": [],
            }],
        }
        unrelated_log = [log("OTHER_123456 failure", "src/Other.ets", "run", "static_wrapped")]

        scoped = path_scoped_code_anchors(
            anchors, path, unrelated_log, "OTHER_123456 failure",
        )

        self.assertEqual(anchors, scoped)
        self.assertFalse(any(item.get("log_identity_match") for item in scoped))

    def test_budget_keeps_emitter_with_one_of_multiple_wrapped_callers(self) -> None:
        logs = [
            log("profile load failed", "src/Ability.ets", "onCreate", "static_wrapped", log_id=7),
            log("profile load failed", "src/Page.ets", "aboutToAppear", "static_wrapped", log_id=7),
            log("profile load failed", "src/ProfileService.ets", "load", "direct", log_id=7),
        ]

        selected = bounded_log_evidence(logs, 2)

        self.assertEqual(
            ["src/ProfileService.ets", "src/Ability.ets"],
            [item["file_path"] for item in selected],
        )


def log(
    message: str,
    file_path: str,
    function: str,
    evidence_class: str,
    log_id: int | None = None,
) -> dict:
    return {
        "log_id": log_id,
        "message_template": message,
        "file_path": file_path,
        "function": function,
        "evidence_class": evidence_class,
    }


def anchor(file_path: str, symbol: str, source: str = "wiki") -> dict:
    return {"file_path": file_path, "symbol": symbol, "source": source}


def inactive_path() -> dict:
    return {"activated": False, "path_candidates": []}


if __name__ == "__main__":
    unittest.main()
