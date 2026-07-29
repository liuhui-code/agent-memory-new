# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_collect import collect_matches
from tools.agent_memory_runtime.storage import resolve_project


class LogEffectTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "log-effect-demo"
        self.project.mkdir()
        self.write_source("payment authorization failed")
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_source(self, message: str) -> None:
        source = self.project / "PaymentService.ets"
        source.write_text(
            """
export class PaymentService {
  private emitFailure(message: string): void {
    Logger.error(message)
  }

  private reportFailure(message: string): void {
    this.emitFailure(message)
  }

  submit(): void {
    this.reportFailure('%s')
  }

  exampleOnly(): void {
    const sample = "this.emitFailure('fake example')"
  }

  cycleA(): void {
    this.cycleB()
  }

  cycleB(): void {
    this.cycleA()
  }
}
""".strip() % message + "\n",
            encoding="utf-8",
        )

    def write_file(self, relative: str, content: str) -> None:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")

    def write_cross_file_wrappers(self, sink_message: str = "message") -> None:
        self.write_file(
            "cross/log/LogSink.ets",
            f"""
export class LogSink {{
  emit(message: string): void {{
    Logger.error({sink_message})
  }}
}}
""",
        )
        self.write_file(
            "cross/log/DomainLogger.ets",
            """
import { LogSink } from './LogSink'
export class DomainLogger {
  private sink: LogSink = new LogSink()
  report(message: string): void {
    this.sink.emit(message)
  }
}
""",
        )
        self.write_file(
            "cross/ProfileService.ets",
            """
import { DomainLogger } from './log/DomainLogger'
export class CrossProfileService {
  private logger: DomainLogger = new DomainLogger()
  load(): void {
    this.logger.report('cross profile failed')
  }
}
""",
        )

    def learn(self) -> dict:
        result = self.run_memory(
            self.project, "learn-path", "--path", "PaymentService.ets", "--json"
        )
        return json.loads(result.stdout)

    def rows(self, sql: str, params: tuple | None = None) -> list[sqlite3.Row]:
        database = self.project_memory_dir(self.project) / "memory.db"
        with sqlite3.connect(database) as conn:
            conn.row_factory = sqlite3.Row
            values = (self.project_id(self.project),) if params is None else params
            return conn.execute(sql, values).fetchall()

    def test_learning_derives_bounded_multi_hop_wrapped_log_effect(self) -> None:
        payload = self.learn()
        effects = self.rows(
            "SELECT * FROM code_log_effects WHERE project_id = ? ORDER BY id"
        )
        direct_logs = self.rows(
            "SELECT * FROM code_log_statements WHERE project_id = ? ORDER BY id"
        )

        self.assertEqual(1, len(direct_logs))
        self.assertEqual(2, len(effects))
        effect = next(row for row in effects if row["function"] == "submit")
        self.assertEqual("submit", effect["function"])
        self.assertEqual("reportFailure", effect["wrapper_symbol"])
        self.assertEqual("payment authorization failed", effect["message_template"])
        self.assertEqual("static_wrapped", effect["evidence_class"])
        self.assertEqual(2, effect["wrapper_depth"])
        self.assertEqual(
            ["submit", "reportFailure", "emitFailure", "logger.error"],
            json.loads(effect["call_path"]),
        )
        self.assertEqual(
            2, payload["parse_stats"]["semantic_index"]["log_effects"]["effects_emitted"]
        )

    def test_context_exposes_wrapper_as_advisory_call_path(self) -> None:
        self.learn()
        self.assertEqual(
            2,
            len(self.rows("SELECT rowid FROM code_log_effect_fts WHERE project_id = ?")),
        )
        project = resolve_project(str(self.project), str(self.memory_home(self.project)))
        collected_logs = collect_matches(project, "payment authorization failed")["code_log_matches"]
        self.assertTrue(collected_logs, "log effect was not scored by query collection")
        result = self.run_memory(
            self.project,
            "context",
            "--query",
            "payment authorization failed",
            "--compact",
            "--json",
        )
        context = json.loads(result.stdout)
        anchors = context["query_handoff"]["log_anchors"]
        wrapped_anchors = [
            item for item in anchors if item.get("evidence_class") == "static_wrapped"
        ]
        self.assertTrue(wrapped_anchors, context.get("code_log_matches"))
        wrapped = wrapped_anchors[0]

        self.assertEqual("reportFailure", wrapped["wrapper_symbol"])
        self.assertEqual(
            ["submit", "reportFailure", "emitFailure", "logger.error"],
            wrapped["call_path"],
        )
        self.assertIsNotNone(wrapped["log_id"])

    def test_relearn_replaces_stale_wrapped_message(self) -> None:
        self.learn()
        self.write_source("payment retry exhausted")
        self.learn()
        effects = self.rows(
            "SELECT function, message_template FROM code_log_effects WHERE project_id = ? ORDER BY id"
        )

        submit = next(row for row in effects if row["function"] == "submit")
        self.assertEqual("payment retry exhausted", submit["message_template"])

    def test_compact_context_exposes_persisted_effect_truncation(self) -> None:
        self.learn()
        database = self.project_memory_dir(self.project) / "memory.db"
        with sqlite3.connect(database) as conn:
            conn.execute(
                "UPDATE code_log_effects SET truncated = 1 "
                "WHERE project_id = ? AND function = 'submit'",
                (self.project_id(self.project),),
            )
        context = json.loads(self.run_memory(
            self.project,
            "context",
            "--query",
            "payment authorization failed",
            "--compact",
            "--json",
        ).stdout)
        wrapped = next(
            item for item in context["query_handoff"]["log_anchors"]
            if item.get("function") == "submit"
        )

        self.assertTrue(wrapped["truncated"])

    def test_cross_file_wrappers_refresh_all_transitive_callers(self) -> None:
        self.write_cross_file_wrappers()
        self.run_memory(self.project, "learn-path", "--path", "cross", "--json")
        effects = self.rows(
            "SELECT * FROM code_log_effects WHERE project_id = ? AND function = 'load'"
        )
        self.assertEqual(1, len(effects))
        old_sink_id = int(effects[0]["sink_log_id"])
        self.assertEqual(
            ["load", "report", "emit", "logger.error"],
            json.loads(effects[0]["call_path"]),
        )
        self.assertEqual(
            [
                "cross/ProfileService.ets#load",
                "cross/log/DomainLogger.ets#report",
                "cross/log/LogSink.ets#emit",
                "cross/log/LogSink.ets#logger.error",
            ],
            json.loads(effects[0]["call_path_locations"]),
        )

        self.write_cross_file_wrappers("'sink implementation changed'")
        self.run_memory(
            self.project,
            "learn-path",
            "--path",
            "cross/log/LogSink.ets",
            "--json",
        )
        refreshed = self.rows(
            "SELECT * FROM code_log_effects WHERE project_id = ? AND function = 'load'"
        )

        self.assertEqual(1, len(refreshed))
        self.assertNotEqual(old_sink_id, int(refreshed[0]["sink_log_id"]))
        self.assertEqual("cross profile failed", refreshed[0]["message_template"])
        context = json.loads(self.run_memory(
            self.project, "context", "--query", "cross profile failed",
            "--compact", "--json",
        ).stdout)
        anchor = next(
            item for item in context["query_handoff"]["log_anchors"]
            if item.get("message_template") == "cross profile failed"
        )
        self.assertEqual(
            "cross/log/DomainLogger.ets#report",
            anchor["call_path_locations"][1],
        )

    def test_relearning_only_outer_caller_keeps_cross_file_sink_reachable(self) -> None:
        self.write_cross_file_wrappers()
        self.run_memory(self.project, "learn-path", "--path", "cross", "--json")
        self.write_file(
            "cross/ProfileService.ets",
            """
import { DomainLogger } from './log/DomainLogger'
export class CrossProfileService {
  private logger: DomainLogger = new DomainLogger()
  load(): void {
    this.logger.report('cross profile retry exhausted')
  }
}
""",
        )

        self.run_memory(
            self.project,
            "learn-path",
            "--path",
            "cross/ProfileService.ets",
            "--json",
        )
        effects = self.rows(
            "SELECT * FROM code_log_effects WHERE project_id = ? AND function = 'load'"
        )

        self.assertEqual(1, len(effects))
        self.assertEqual("cross profile retry exhausted", effects[0]["message_template"])
        self.assertEqual(2, effects[0]["wrapper_depth"])

    def test_interface_dispatch_keeps_parallel_inferred_log_paths(self) -> None:
        self.write_file(
            "dispatch/Reporter.ets",
            """
export interface Reporter {
}
""",
        )
        for implementation in ("ConsoleReporter", "FileReporter"):
            self.write_file(
                f"dispatch/{implementation}.ets",
                f"""
import {{ Reporter }} from './Reporter'
export class {implementation} implements Reporter {{
  report(message: string): void {{
    Logger.error(message)
  }}
}}
""",
            )
        self.write_file(
            "dispatch/AuditReporter.ets",
            """
import { Reporter } from './Reporter'
export class AuditReporter implements Reporter {
  report(message: string, code: number): void {
    Logger.error(message)
  }
}
""",
        )
        self.write_file(
            "dispatch/DispatchService.ets",
            """
import { Reporter } from './Reporter'
export class DispatchService {
  private reporter: Reporter
  run(): void {
    this.reporter.report('dispatch report failed')
  }
}
""",
        )

        self.run_memory(self.project, "learn-path", "--path", "dispatch", "--json")
        edges = self.rows(
            """
            SELECT target.symbol, edge.evidence_kind
            FROM memory_edges edge
            JOIN code_symbols source ON source.id = edge.source_id
            JOIN code_symbols target ON target.id = edge.target_id
            WHERE edge.project_id = ? AND edge.relation = 'calls'
              AND edge.valid_to IS NULL AND source.symbol = 'run'
            ORDER BY target.file_path
            """
        )
        effects = self.rows(
            "SELECT * FROM code_log_effects WHERE project_id = ? AND function = 'run' ORDER BY call_path"
        )

        self.assertEqual(["report", "report"], [row["symbol"] for row in edges])
        self.assertTrue(all(row["evidence_kind"] == "inferred_semantic_calls" for row in edges))
        self.assertEqual(2, len(effects))
        self.assertTrue(all(row["evidence_class"] == "inferred_wrapped" for row in effects))
        self.assertTrue(all(row["message_template"] == "dispatch report failed" for row in effects))

        self.write_file(
            "dispatch/RemoteReporter.ets",
            """
import { Reporter } from './Reporter'
export class RemoteReporter implements Reporter {
  report(message: string): void {
    Logger.error(message)
  }
}
""",
        )
        added = json.loads(self.run_memory(
            self.project, "learn-path", "--path", "dispatch/RemoteReporter.ets", "--json",
        ).stdout)
        refreshed_paths = added["parse_stats"]["dispatch_dependents_reindexed"]
        expanded = self.rows(
            "SELECT * FROM code_log_effects WHERE project_id = ? AND function = 'run'"
        )

        self.assertIn("dispatch/DispatchService.ets", refreshed_paths)
        self.assertEqual(3, len(expanded))

        self.write_file(
            "dispatch/FileReporter.ets",
            """
export class FileReporter {
  report(message: string): void {
    Logger.error(message)
  }
}
""",
        )
        self.run_memory(
            self.project, "learn-path", "--path", "dispatch/FileReporter.ets", "--json",
        )
        contracted = self.rows(
            "SELECT * FROM code_log_effects WHERE project_id = ? AND function = 'run'"
        )

        self.assertEqual(2, len(contracted))
        self.assertFalse(any(
            "FileReporter.ets" in row["call_path_locations"] for row in contracted
        ))
        runtime_project = resolve_project(
            str(self.project), str(self.memory_home(self.project)),
        )
        recalled = collect_matches(
            runtime_project, "dispatch report failed",
        )["code_log_matches"]
        self.assertTrue(
            any(item.get("evidence_class") == "inferred_wrapped" for item in recalled),
            recalled,
        )
        compact = json.loads(self.run_memory(
            self.project, "context", "--query", "dispatch report failed",
            "--compact", "--json",
        ).stdout)
        inferred = [
            item for item in compact["query_handoff"]["log_anchors"]
            if item.get("evidence_class") == "inferred_wrapped"
        ]
        self.assertEqual(2, len(inferred), compact["query_handoff"]["log_anchors"])
        self.assertTrue(all(len(item["call_path_locations"]) == 3 for item in inferred))

    def test_search_schema_migrates_pre_location_log_effect_index(self) -> None:
        database = self.project_memory_dir(self.project) / "memory.db"
        with sqlite3.connect(database) as conn:
            conn.executescript(
                """
                DROP TRIGGER IF EXISTS code_log_effect_fts_ai;
                DROP TRIGGER IF EXISTS code_log_effect_fts_ad;
                DROP TRIGGER IF EXISTS code_log_effect_fts_au;
                DROP TABLE code_log_effect_fts;
                CREATE VIRTUAL TABLE code_log_effect_fts USING fts5(
                  project_id UNINDEXED, file_path, function, wrapper_symbol,
                  level, logger, message_template, evidence_class, call_path, raw_call
                );
                UPDATE runtime_schema_versions SET version = 'fts-v5'
                WHERE component = 'search';
                """
            )
        self.run_memory(self.project, "context", "--query", "profile", "--json")

        columns = self.rows("PRAGMA table_info(code_log_effect_fts)", ())
        self.assertIn("call_path_locations", {row["name"] for row in columns})


if __name__ == "__main__":
    import unittest

    unittest.main()
