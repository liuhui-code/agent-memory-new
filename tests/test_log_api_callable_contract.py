# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.arkts_source_ranges import arkts_line_ranges
from tools.agent_memory_runtime.code_wiki_extractors import (
    extract_log_statements,
    message_template_for_args,
)
from tools.agent_memory_runtime.ecma_callable_ranges import callable_symbols_by_line
from tools.agent_memory_runtime.log_event_identity import has_literal_event_identity


class LogApiCallableContractTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "log-callable-contract"
        self.project.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write(self, relative: str, source: str) -> Path:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source.strip() + "\n", encoding="utf-8")
        return path

    def rows(self, query: str) -> list[sqlite3.Row]:
        database = self.project_memory_dir(self.project) / "memory.db"
        with sqlite3.connect(database) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(query, (self.project_id(self.project),)).fetchall()

    def test_typescript_hilog_sink_uses_the_shared_log_api_contract(self) -> None:
        source = self.write(
            "src/logging/PlatformLog.ts",
            """
import hilog from '@ohos.hilog'
export class PlatformLog {
  static error(message: string): void {
    hilog.error(0x1200, 'ContractFixture', 'platform sink failed')
  }
}
""",
        )

        logs = extract_log_statements(source, "TypeScript")

        self.assertEqual(1, len(logs))
        self.assertEqual("error", logs[0]["function"])
        self.assertEqual("hilog", logs[0]["logger"])
        self.assertEqual("platform sink failed", logs[0]["message_template"])

    def test_callable_ranges_include_property_and_member_callbacks(self) -> None:
        lines = """
struct EditorPanel {
  bridge = {
    onImageReady: (path: string) => {
      PlatformLog.info('image ready:' + path)
    }
  }

  build() {
    Web({ src: this.url })
      .onPageEnd((event) => {
        PlatformLog.info('page load completed')
      })
  }
}
""".strip().splitlines()

        ranges = arkts_line_ranges(lines)
        by_symbol = {str(item["symbol"]): item for item in ranges}

        self.assertEqual((3, 5), span(by_symbol["onImageReady"]))
        self.assertEqual((10, 12), span(by_symbol["onPageEnd"]))

    def test_anonymous_promise_callback_keeps_stable_method_owner(self) -> None:
        lines = """
class RegistrationService {
  register(response: string): void {
    Promise.resolve(response).then((value: string) => {
      logger.info(`accepted: ${value}`)
    })
  }
}
""".strip().splitlines()

        owners = callable_symbols_by_line(lines, "ArkTS")
        symbols = {str(item["symbol"]) for item in arkts_line_ranges(lines)}

        self.assertEqual("register", owners[4])
        self.assertNotIn("resolve", symbols)
        self.assertNotIn("then", symbols)

    def test_dynamic_log_argument_is_a_value_not_an_event_literal(self) -> None:
        self.assertEqual(
            "{message}",
            message_template_for_args("hilog", "0x1200, TAG, message", 2),
        )
        self.assertFalse(has_literal_event_identity({
            "message_template": "message",
            "raw_statement": "hilog.error(0x1200, TAG, message)",
        }))
        self.assertTrue(has_literal_event_identity({
            "message_template": "message",
            "raw_statement": "console.info('message')",
        }))

    def test_learning_persists_callback_owner_and_wrapped_log_effect(self) -> None:
        self.write(
            "src/logging/PlatformLog.ts",
            """
import hilog from '@ohos.hilog'
export class PlatformLog {
  static info(message: string): void {
    hilog.info(0x1200, 'ContractFixture', 'platform log sink')
  }
}
""",
        )
        self.write(
            "src/editor/EditorPanel.ets",
            """
import { PlatformLog } from '../logging/PlatformLog'
@Component
export struct EditorPanel {
  bridge = {
    onImageReady: (path: string) => {
      PlatformLog.info('image ready:' + path)
    }
  }

  build() {
    Web({ src: 'editor.html' })
      .onPageEnd((event) => {
        PlatformLog.info('page load completed')
      })
  }
}
""",
        )
        self.run_memory(self.project, "init")
        learned = json.loads(self.run_memory(
            self.project, "learn-path", "--path", "src", "--json",
        ).stdout)

        callbacks = self.rows(
            "SELECT symbol, start_line, end_line, semantic_adapter "
            "FROM code_symbols WHERE project_id = ? "
            "AND symbol IN ('onImageReady', 'onPageEnd') ORDER BY symbol"
        )
        effects = self.rows(
            "SELECT function, message_template, evidence_class "
            "FROM code_log_effects WHERE project_id = ? ORDER BY function"
        )

        self.assertEqual(["onImageReady", "onPageEnd"], [row["symbol"] for row in callbacks])
        self.assertTrue(all(row["start_line"] and row["end_line"] for row in callbacks))
        self.assertTrue(all(row["semantic_adapter"] for row in callbacks))
        self.assertEqual(
            [("onImageReady", "image ready:"), ("onPageEnd", "page load completed")],
            [(row["function"], row["message_template"]) for row in effects],
        )
        self.assertTrue(all(row["evidence_class"] == "static_wrapped" for row in effects))
        self.assertEqual(2, learned["parse_stats"]["semantic_index"]["log_effects"]["effects_emitted"])

        context = json.loads(self.run_memory(
            self.project, "context", "--query", "page load completed", "--compact", "--json",
        ).stdout)
        handoff = context["query_handoff"]
        log_anchor = next(
            item for item in handoff["log_anchors"]
            if item.get("message_template") == "page load completed"
        )
        code_anchor = next(
            item for item in handoff["code_anchors"]
            if item.get("file_path") == "src/editor/EditorPanel.ets"
        )

        self.assertEqual("onPageEnd", log_anchor["function"])
        self.assertEqual("static_wrapped", log_anchor["evidence_class"])
        self.assertTrue(any(
            int(item["start_line"]) <= 12 and int(item["end_line"]) >= 14
            for item in code_anchor["source_ranges"]
        ), code_anchor)


def span(item: dict[str, object]) -> tuple[int, int]:
    return int(item["start_line"]), int(item["end_line"])
