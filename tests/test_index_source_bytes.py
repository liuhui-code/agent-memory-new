# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Development fixtures for raw source identity, not sealed evaluation cases."""

import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase, REPO_ROOT
from tools.agent_memory_runtime.semantic_adapters import adapter_for
from tools.agent_memory_runtime.semantic_ecma import parse_source
from tools.agent_memory_runtime.semantic_provider_protocol import build_provider_request
from tools.agent_memory_runtime.storage import resolve_project


SOURCE = (
    b"export class TransferQueue {\n"
    b"  drainPending(): string {\n"
    b"    console.info('transfer queue drained')\n"
    b"    return this.ready()\n"
    b"  }\n"
    b"  ready(): string { return 'ready' }\n"
    b"}\n"
)


class SourceByteFreshnessTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / "source"
        self.project.mkdir()
        self.source = self.project / "transfer.ts"
        self.source.write_bytes(SOURCE.replace(b"\n", b"\r\n"))

    def learn(self, **kwargs) -> dict:
        return json.loads(self.run_memory(self.project, "learn-path", "--path", ".",
                                          "--json", **kwargs).stdout)

    def query(self) -> dict:
        result = self.run_memory(self.project, "context", "--query",
                                 "TransferQueue.drainPending", "--compact", "--json")
        return json.loads(result.stdout)

    def database(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.project_memory_dir(self.project) / "memory.db")
        conn.row_factory = sqlite3.Row
        return conn

    def assert_current_handoff(self, payload: dict) -> None:
        self.assertEqual("current", payload["source_freshness"]["status"],
                         json.dumps(payload, ensure_ascii=False))
        handoff = payload["query_handoff"]
        primary = handoff["callable_evidence"]["primary"]
        self.assertEqual("drainPending", primary["symbol"])
        self.assertEqual((2, 5), (primary["source_range"]["start_line"],
                                 primary["source_range"]["end_line"]))
        self.assertTrue(handoff["code_anchors"])

    def assert_stale_handoff(self, payload: dict) -> None:
        freshness = payload["source_freshness"]
        self.assertEqual("partial_current", freshness["status"])
        self.assertGreater(freshness["blocked_rows"], 0)
        self.assertEqual([self.source.name], freshness["stale_paths"])
        self.assertEqual([], payload["query_handoff"]["code_anchors"])
        self.assertIsNone(payload["query_handoff"]["callable_evidence"]["primary"])

    def assert_stored_bytes(self, expect_edges: bool = True) -> None:
        expected = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.database() as conn:
            for table in ("code_files", "code_symbols", "code_log_statements"):
                rows = conn.execute(f"SELECT source_digest FROM {table}").fetchall()
                self.assertTrue(rows, table)
                self.assertEqual({expected}, {row["source_digest"] for row in rows}, table)
            edges = conn.execute(
                "SELECT evidence FROM memory_edges WHERE extractor_version LIKE 'semantic-index:%' "
                "AND valid_to IS NULL AND source_type = 'code_symbol'"
            ).fetchall()
            if not expect_edges:
                return
            self.assertTrue(edges)
            self.assertEqual({expected}, {json.loads(row["evidence"])["source_digest"]
                                         for row in edges})

    def test_new_crlf_index_is_current_in_actual_query_handoff(self) -> None:
        self.learn()
        self.assert_current_handoff(self.query())
        self.assert_stored_bytes()

    def test_new_lf_index_is_current_in_actual_query_handoff(self) -> None:
        self.source.write_bytes(SOURCE)
        self.learn()
        self.assert_current_handoff(self.query())
        self.assert_stored_bytes()

    def test_line_endings_and_code_edits_still_block_until_relearn(self) -> None:
        self.learn()
        self.assert_current_handoff(self.query())
        self.source.write_bytes(SOURCE)
        self.assert_stale_handoff(self.query())
        self.source.write_bytes(SOURCE.replace(b"\n", b"\r\n"))
        self.assert_current_handoff(self.query())
        self.source.write_bytes(self.source.read_bytes().replace(b"ready", b"done"))
        self.assert_stale_handoff(self.query())
        self.learn()
        self.assert_current_handoff(self.query())
        self.assert_stored_bytes()

    def test_ignored_utf8_byte_edits_are_not_normalized_away(self) -> None:
        self.source.write_bytes(self.source.read_bytes() + b"// legacy byte: \xff\r\n")
        self.learn()
        self.assert_current_handoff(self.query())
        self.assert_stored_bytes()
        self.source.write_bytes(self.source.read_bytes().replace(b"\xff", b"\xfe"))
        self.assert_stale_handoff(self.query())

    def test_merge_relearn_repairs_legacy_digest_without_losing_memory(self) -> None:
        self.learn()
        self.run_memory(self.project, "update", "--type", "semantic", "--fact",
                        "TransferQueue dispatch is explicit and bounded.")
        self.run_memory(self.project, "learn-business", "--payload", json.dumps({
            "files": [{"file_path": self.source.name, "business_summary": "Transfer queue owner"}],
        }), "--json")
        before_facts = self.list_records(self.project, "semantic")
        before = self.query()["source_freshness"]["generation"]
        # Reproduce the exact legacy bug: only semantic-enriched rows use text hashes.
        legacy_digest = hashlib.sha256(SOURCE).hexdigest()
        with self.database() as conn:
            conn.execute("UPDATE code_symbols SET source_digest = ?", (legacy_digest,))
        self.assert_stale_handoff(self.query())
        # Unchanged-file maintenance is not a schema/data migration.
        self.run_memory(self.project, "maintain-refresh-scope", "--changed-only", "--json")
        self.assert_stale_handoff(self.query())
        self.learn()  # merge, deliberately not --replace
        after = self.query()
        self.assert_current_handoff(after)
        self.assertGreater(after["source_freshness"]["generation"], before)
        self.assert_stored_bytes()
        after_facts = self.list_records(self.project, "semantic")
        for rows in (before_facts, after_facts):
            for row in rows:
                row.pop("last_used_at", None)
                row.pop("use_count", None)
        self.assertEqual(before_facts, after_facts)
        with self.database() as conn:
            self.assertEqual("Transfer queue owner", conn.execute(
                "SELECT business_summary FROM code_files"
            ).fetchone()[0])

    def test_external_provider_crlf_uses_same_raw_digest(self) -> None:
        self.source.write_bytes(self.source.read_bytes().replace(b"this.ready()", b"'ready'"))
        self.source.rename(self.project / "transfer.ets")
        self.source = self.project / "transfer.ets"
        provider = REPO_ROOT / "tests/fixtures/exact_semantic_provider.py"
        provider.chmod(0o755)
        learned = self.learn(env={"AGENT_MEMORY_SEMANTIC_PROVIDER_ARKTS": str(provider)})
        run = learned["parse_stats"]["semantic_index"]["provider_runs"][0]
        self.assertEqual("exact", run["status"])
        self.assertEqual("external", run["selected"])
        # This test provider deliberately supplies declaration-only source ranges.
        self.assertEqual("current", self.query()["source_freshness"]["status"])
        self.assert_stored_bytes(expect_edges=False)


class SourceByteAdapterTests(AgentMemoryTestBase):
    def test_adapters_preserve_source_bytes_and_newline_semantics(self) -> None:
        cases = [
            ("TypeScript", "queue.ts", SOURCE),
            ("ArkTS", "queue.ets", SOURCE),
            ("C/C++", "queue.cpp", b"int drainPending() {\n  return 1;\n}\n"),
            ("Build Artifact", "CMakeLists.txt", b"add_library(queue STATIC\n  queue.cpp\n)\n"),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            project = resolve_project(str(root), str(Path(temporary) / "memory"))
            for language, filename, raw in cases:
                path = root / filename
                baseline = None
                for newline in (b"\n", b"\r\n", b"\r"):
                    with self.subTest(language=language, newline=newline):
                        data = raw.replace(b"\n", newline)
                        path.write_bytes(data)
                        batch = adapter_for(language).index(project, [path])
                        self.assertEqual({filename: hashlib.sha256(data).hexdigest()},
                                         batch.source_digests)
                        self.assertTrue(batch.entities)
                        payload = batch.to_dict()
                        del payload["source_digests"]
                        if baseline is None:
                            baseline = payload
                        else:
                            self.assertEqual(baseline, payload)
                data = raw + b"// ignored: \xff\n"
                path.write_bytes(data)
                batch = adapter_for(language).index(project, [path])
                self.assertEqual(hashlib.sha256(data).hexdigest(), batch.source_digests[filename])
                request = build_provider_request(project, language, [path])
                self.assertEqual(batch.source_digests[filename], request["files"][0]["digest"])

    def test_parse_source_text_remains_available_for_revision_deltas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = resolve_project(str(root), str(root / "memory"))
            parsed = parse_source(project, root / "queue.ts", SOURCE.decode(), "TypeScript", False)
            self.assertEqual(hashlib.sha256(SOURCE).hexdigest(), parsed.digest)
            self.assertTrue(parsed.entities)


if __name__ == "__main__":
    import unittest
    unittest.main()
