# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import unittest

from tools.agent_memory_runtime.log_event_identity import (
    event_match,
    select_event_matches,
    template_literal_segments,
)


class LogEventIdentityTests(unittest.TestCase):
    def test_dynamic_template_exposes_only_stable_literal_segments(self) -> None:
        self.assertEqual(
            ["upload_event_913a transfer failed", "session"],
            template_literal_segments(
                "UPLOAD_EVENT_913A transfer failed: ${error.message}; session=${sessionId}"
            ),
        )

    def test_distinctive_dynamic_literal_selects_one_event_and_all_its_paths(self) -> None:
        expected = [
            log("UPLOAD_EVENT_913A transfer failed: ${error.message}", "src/Upload.ets", 1),
            log("UPLOAD_EVENT_913A transfer failed: ${error.message}", "src/Upload.ets", 2),
        ]
        decoy = log("UPLOAD_EVENT_913B transfer retry failed: ${error.message}", "src/Retry.ets", 3)

        selected = select_event_matches(
            [*expected, decoy],
            "Receiver closed early after UPLOAD_EVENT_913A transfer failed: socket reset",
        )

        self.assertEqual(expected, selected)
        self.assertEqual("distinctive_literal", event_match(expected[0], "UPLOAD_EVENT_913A transfer failed")["band"])

    def test_long_symptom_context_cannot_dilute_distinctive_literal(self) -> None:
        target = log("文件写入出错: ${Errors.getErrorMessage(error)}", "src/Flush.ets", 1)
        decoys = [
            log("文件写入已完成: ${fileId}", "src/History.ets", 2),
            log("接收文件状态出错: ${state}", "src/Receive.ets", 3),
        ]

        selected = select_event_matches(
            [*decoys, target],
            "多个文件同时接收时队列状态异常，流水日志出现 文件写入出错，请返回对应源码和包装路径",
        )

        self.assertEqual([target], selected)

    def test_short_generic_dynamic_literal_preserves_broad_fallback(self) -> None:
        logs = [
            log("load failed: ${error}", "src/A.ets", 1),
            log("save failed: ${error}", "src/B.ets", 2),
        ]

        self.assertEqual(logs, select_event_matches(logs, "failed"))
        self.assertEqual("none", event_match(logs[0], "failed")["band"])

    def test_complete_static_template_remains_an_exact_identity(self) -> None:
        item = log("DISPATCH_PROFILE_8A21 load failed", "src/Dispatch.ets", 1)

        match = event_match(item, "Observed DISPATCH_PROFILE_8A21 load failed in runtime logs")

        self.assertEqual("exact_template", match["band"])
        self.assertEqual("dispatch_profile_8a21 load failed", match["matched_literal"])


def log(message: str, file_path: str, effect_id: int) -> dict:
    return {
        "effect_id": effect_id,
        "message_template": message,
        "file_path": file_path,
        "function": "run",
        "level": "warning",
        "logger": "logger",
        "evidence_class": "static_wrapped",
    }


if __name__ == "__main__":
    unittest.main()
