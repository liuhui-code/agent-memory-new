# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import sqlite3
import tempfile
import hashlib
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase, REPO_ROOT
from tools.agent_memory_runtime.semantic_provider_metrics import (
    METRIC_LIMIT,
    append_provider_metric,
    build_semantic_provider_actions,
    read_provider_metrics,
    semantic_provider_health,
)
from tools.agent_memory_runtime.semantic_provider_process import run_external_provider
from tools.agent_memory_runtime.semantic_provider_protocol import ProviderFailure
from tools.agent_memory_runtime.semantic_provider_protocol import build_provider_request
from tools.agent_memory_runtime.semantic_runtime import run_semantic_adapter
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.impact_scope import _unique_links


PROVIDER = REPO_ROOT / "tests" / "fixtures" / "exact_semantic_provider.py"


class SemanticProviderTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project = Path(self.temp_dir.name) / "provider-demo"
        self.project.mkdir()
        self.source = self.project / "src" / "Demo.ets"
        self.source.parent.mkdir()
        self.source.write_text(
            """
export class Demo {
  helper(): void {}
  run(): void { console.error('demo failed'); this.helper() }
}
""".strip() + "\n",
            encoding="utf-8",
        )
        PROVIDER.chmod(0o755)
        self.run_memory(self.project, "init")
        self.runtime_project = resolve_project(str(self.project), str(self.memory_home(self.project)))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def provider_env(self, mode: str = "success") -> dict[str, str]:
        return {
            "AGENT_MEMORY_SEMANTIC_PROVIDER_ARKTS": str(PROVIDER),
            "PROVIDER_TEST_MODE": mode,
        }

    def db_rows(self, query: str) -> list[sqlite3.Row]:
        with sqlite3.connect(self.project_memory_dir(self.project) / "memory.db") as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(query).fetchall()

    def test_learning_uses_exact_provider_and_persists_exact_edge(self) -> None:
        result = self.run_memory(
            self.project, "learn-path", "--path", ".", "--json", env=self.provider_env(),
        )
        payload = json.loads(result.stdout)
        run = payload["parse_stats"]["semantic_index"]["provider_runs"][0]
        edges = self.db_rows(
            "SELECT * FROM memory_edges WHERE valid_to IS NULL AND evidence_kind = 'exact_semantic_calls'"
        )

        self.assertEqual("exact", run["status"])
        self.assertEqual("external", run["selected"])
        self.assertEqual("test-arkts-exact", run["provider_id"])
        self.assertTrue(edges)
        self.assertTrue(read_provider_metrics(self.runtime_project))

        incident = self.run_memory(
            self.project, "incident-trace", "--symptom", "demo failed",
            "--log-text", "demo failed", "--json", env=self.provider_env(),
        )
        chains = json.loads(incident.stdout)["causal_chain"]
        semantic_steps = [step for chain in chains for step in chain["steps"] if step.get("edge_id")]
        self.assertTrue(semantic_steps)
        self.assertEqual("exact", semantic_steps[0]["evidence_class"])
        self.assertEqual("possible", semantic_steps[0]["evidence_role"])

    def test_unavailable_provider_falls_back_to_static(self) -> None:
        env = {"AGENT_MEMORY_SEMANTIC_PROVIDER_ARKTS": str(self.project / "missing-provider")}

        result = self.run_memory(
            self.project, "learn-path", "--path", ".", "--json", env=env,
        )
        run = json.loads(result.stdout)["parse_stats"]["semantic_index"]["provider_runs"][0]
        edges = self.db_rows(
            "SELECT * FROM memory_edges WHERE valid_to IS NULL AND evidence_kind = 'static_semantic_calls'"
        )

        self.assertEqual("fallback", run["status"])
        self.assertEqual("provider_unavailable", run["fallback_reason"])
        self.assertTrue(edges)

    def test_static_mode_never_invokes_configured_provider(self) -> None:
        selection = run_semantic_adapter(
            self.runtime_project, "ArkTS", [self.source.resolve()], "static", self.provider_env("exit"),
        )

        self.assertEqual("static", selection.telemetry["status"])
        self.assertEqual("arkts-static", selection.batch.adapter_id)

    def test_forced_external_reports_process_failures(self) -> None:
        for mode, code in (("malformed", "invalid_json"), ("exit", "provider_exit")):
            with self.subTest(mode=mode), self.assertRaises(ProviderFailure) as caught:
                run_external_provider(
                    self.runtime_project, "ArkTS", [self.source], self.provider_env(mode),
                )
            self.assertEqual(code, caught.exception.code)

    def test_forced_external_rejects_timeout_and_oversize_output(self) -> None:
        with self.assertRaises(ProviderFailure) as timeout:
            run_external_provider(
                self.runtime_project, "ArkTS", [self.source], self.provider_env("timeout"),
                timeout_seconds=1,
            )
        self.assertEqual("provider_timeout", timeout.exception.code)

        with self.assertRaises(ProviderFailure) as oversized:
            run_external_provider(
                self.runtime_project, "ArkTS", [self.source], self.provider_env(),
                max_output_bytes=200,
            )
        self.assertEqual("provider_output_too_large", oversized.exception.code)

    def test_forced_external_rejects_stale_or_unsafe_results(self) -> None:
        for mode, code in (
            ("stale", "stale_source"),
            ("unsafe", "unsafe_path"),
            ("unstable-key", "unstable_symbol_key"),
            ("nonexact", "non_exact_evidence"),
            ("request-mismatch", "request_mismatch"),
            ("bad-schema", "invalid_schema"),
        ):
            with self.subTest(mode=mode), self.assertRaises(ProviderFailure) as caught:
                run_external_provider(
                    self.runtime_project, "ArkTS", [self.source], self.provider_env(mode),
                )
            self.assertEqual(code, caught.exception.code)

    def test_provider_allows_safe_cross_scope_target_identity(self) -> None:
        batch, _metadata = run_external_provider(
            self.runtime_project, "ArkTS", [self.source], self.provider_env("external-target"),
        )

        identity = "ArkTS:external/Other.ets::Other.work|work():void"
        expected_key = "symbol:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        self.assertEqual(expected_key, batch.relations[0].target_key)
        self.assertEqual("external/Other.ets", batch.relations[0].target_file_path)

    def test_partial_exact_provider_resolves_existing_cross_scope_symbol_key(self) -> None:
        external = self.project / "external" / "Other.ets"
        external.parent.mkdir()
        external.write_text("export class Other {\n  work(): void {}\n}\n", encoding="utf-8")
        self.run_memory(self.project, "learn-path", "--path", ".", "--json")

        self.run_memory(
            self.project, "learn-path", "--path", "src/Demo.ets", "--json",
            env=self.provider_env("external-target"),
        )
        rows = self.db_rows(
            """
            SELECT e.* FROM memory_edges e
            JOIN code_symbols source ON source.id = e.source_id
            JOIN code_symbols target ON target.id = e.target_id
            WHERE e.valid_to IS NULL AND e.evidence_kind = 'exact_semantic_calls'
              AND source.qualified_name = 'Demo.run'
              AND target.qualified_name = 'Other.work'
            """
        )

        self.assertTrue(rows)

    def test_provider_metrics_are_bounded_and_create_review_action(self) -> None:
        for index in range(METRIC_LIMIT + 5):
            append_provider_metric(self.runtime_project, {
                "language": "ArkTS", "mode": "auto", "status": "fallback",
                "selected": "static", "provider_configured": True,
                "fallback_reason": f"failure-{index % 2}",
            })
        summary = semantic_provider_health(self.runtime_project)

        self.assertEqual(METRIC_LIMIT, summary["sample_count"])
        self.assertEqual(1.0, summary["fallback_rate"])
        self.assertEqual("review_semantic_provider_failures", build_semantic_provider_actions(summary)[0]["action"])

        health = json.loads(self.run_memory(self.project, "maintain-health", "--json").stdout)
        plan = json.loads(self.run_memory(self.project, "maintain-plan", "--json").stdout)
        self.assertEqual(METRIC_LIMIT, health["semantic_provider"]["sample_count"])
        self.assertTrue(any(
            item["action"] == "review_semantic_provider_failures" for item in plan["actions"]
        ))

    def test_provider_configuration_is_not_read_from_project_files(self) -> None:
        (self.project / "config.json").write_text(
            json.dumps({"semantic_provider": str(PROVIDER)}), encoding="utf-8"
        )

        selection = run_semantic_adapter(self.runtime_project, "ArkTS", [self.source.resolve()], "auto", {})

        self.assertEqual("static", selection.telemetry["selected"])

    def test_provider_request_handles_many_files_without_global_state(self) -> None:
        files = [self.source.resolve()]
        for index in range(404):
            path = self.project / "src" / f"Generated{index}.ets"
            path.write_text(f"export class Generated{index} {{}}\n", encoding="utf-8")
            files.append(path.resolve())

        request = build_provider_request(self.runtime_project, "ArkTS", files)

        self.assertEqual(405, len(request["files"]))
        self.assertEqual(len(request["files"]), len({item["digest"] + item["path"] for item in request["files"]}))

    def test_impact_deduplication_prefers_exact_evidence(self) -> None:
        common = {"source": "a.ets", "relation": "calls", "target": "b.ets", "confidence": 0.9}
        links = _unique_links([
            {**common, "evidence_class": "static", "extractor_version": "static"},
            {**common, "evidence_class": "exact", "extractor_version": "compiler"},
        ])

        self.assertEqual(1, len(links))
        self.assertEqual("exact", links[0]["evidence_class"])


if __name__ == "__main__":
    import unittest

    unittest.main()
