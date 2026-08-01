# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


MULTILINE_SOURCE = """
export interface TelemetryNotice {
  channel: string
}

export class TelemetryEnvelopeService {
  private static async decodeWrappedSample(
    notice: TelemetryNotice,
    expectedChannel: string
  ): Promise<void> {
    if (notice.channel !== expectedChannel) {
      return
    }
    console.info('wrapped telemetry sample decoded')
  }
}
"""


class CallableRangeGeneralizationTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "callable-range-project"
        self.root.mkdir()
        self.write_file("src/telemetry/TelemetryEnvelopeService.ets", MULTILINE_SOURCE)
        self.write_file("src/playback/PlaybackLeaseCoordinator.ets", dense_source())
        for index in range(10):
            self.write_file(
                f"src/noise/SessionLeaseReference{index}.ets",
                noise_source(index),
            )
        self.run_memory(self.root, "init")
        self.run_memory(self.root, "learn-path", "--path", ".", "--json")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_file(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")

    def test_multiline_method_header_is_persisted_as_callable(self) -> None:
        db = self.project_memory_dir(self.root) / "memory.db"
        with sqlite3.connect(db) as conn:
            row = conn.execute(
                """
                SELECT symbol, start_line, end_line, owner_name
                FROM code_symbols
                WHERE project_id = ? AND symbol = 'decodeWrappedSample'
                """,
                (self.project_id(self.root),),
            ).fetchone()

        self.assertEqual(("decodeWrappedSample", 6, 14, "TelemetryEnvelopeService"), row)

    def test_dense_file_tail_method_enters_bounded_callable_pool(self) -> None:
        result = self.run_memory(
            self.root,
            "context",
            "--query",
            "playback lease remains bound to previous session after replacement",
            "--json",
        )
        payload = json.loads(result.stdout)
        localization = payload["query_audit"]["hierarchical_localization"]
        file_paths = {
            item["file_path"] for item in localization["file_candidates"]
        }
        symbols = {
            (item["file_path"], item["symbol"])
            for item in localization["callable_candidates"]
        }

        target = "src/playback/PlaybackLeaseCoordinator.ets"
        self.assertIn(target, file_paths)
        self.assertIn(
            (target, "applyTransition"),
            symbols,
        )
        self.assertLessEqual(
            len(localization["callable_candidates"]),
            localization["limits"]["callables"],
        )


def dense_source() -> str:
    methods = "\n\n".join(
        f"  public catalogStep{index}(): void {{ console.info('catalog step {index}') }}"
        for index in range(21)
    )
    return f"""
export class PlaybackLeaseCoordinator {{
  private activeLease: string = ''

{methods}

  public applyTransition(previousSession: string, nextSession: string): void {{
    if (this.activeLease === previousSession) {{
      this.activeLease = nextSession
    }}
    console.info('transition applied')
  }}
}}
"""


def noise_source(index: int) -> str:
    return f"""
export class SessionLeaseReference{index} {{
  public describeReplacementSession(): string {{
    return 'playback lease previous session replacement reference {index}'
  }}
}}
"""
