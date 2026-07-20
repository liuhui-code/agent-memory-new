# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.scope_boundaries import surface_digest


class ScopeBoundaryTests(AgentMemoryTestBase):
    def write(self, project: Path, relative: str, content: str) -> None:
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def git(self, project: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(project), *args],
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()

    def init_repo(self, project: Path) -> None:
        self.git(project, "init", "-q")
        self.git(project, "config", "user.email", "tests@example.com")
        self.git(project, "config", "user.name", "Agent Memory Tests")
        self.git(project, "add", ".")
        self.git(project, "commit", "-q", "-m", "initial")

    def rows(self, project: Path, sql: str) -> list[dict]:
        with sqlite3.connect(self.project_memory_dir(project) / "memory.db") as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(sql).fetchall()]

    def test_surface_digest_tracks_symbol_shape_not_function_body(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            source = project / "Auth.ts"
            source.write_text(
                "export function authorize() { return 'v1' }\n",
                encoding="utf-8",
            )
            original = surface_digest(source)
            source.write_text(
                "export function authorize() { return 'v2' }\n",
                encoding="utf-8",
            )
            body_only = surface_digest(source)
            source.write_text(
                "export function authorizeV2() { return 'v2' }\n",
                encoding="utf-8",
            )
            renamed = surface_digest(source)

        self.assertEqual(original, body_only)
        self.assertNotEqual(original, renamed)

    def test_boundary_change_is_reported_without_expanding_learned_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write(
                project,
                "business/Profile.ts",
                "import { authorize } from '../shared/Auth'\n"
                "export function loadProfile() { return authorize() }\n",
            )
            self.write(
                project,
                "shared/Auth.ts",
                "export function authorize() { return 'v1' }\n",
            )
            self.write(project, "noise/Other.ts", "export const noise = 'v1'\n")
            self.init_repo(project)
            learn = json.loads(
                self.run_memory(
                    project, "learn-path", "--path", "business", "--json"
                ).stdout
            )
            boundaries = self.rows(
                project, "SELECT * FROM scope_boundary_dependencies"
            )
            self.write(
                project,
                "shared/Auth.ts",
                "export function authorize() { return 'v2' }\n",
            )
            self.write(project, "noise/Other.ts", "export const noise = 'v2'\n")
            self.git(project, "add", ".")
            self.git(project, "commit", "-q", "-m", "shared and unrelated changes")

            refreshed = json.loads(
                self.run_memory(
                    project, "maintain-refresh-scope", "--changed-only", "--json"
                ).stdout
            )["scopes"][0]
            context = json.loads(
                self.run_memory(
                    project,
                    "context",
                    "--query",
                    "Profile loadProfile",
                    "--compact",
                    "--json",
                ).stdout
            )
            health = json.loads(
                self.run_memory(project, "maintain-health", "--json").stdout
            )
            code_files = {
                row["file_path"] for row in self.list_records(project, "code-file")
            }
            self.run_memory(
                project,
                "maintain-refresh-scope",
                "--scope-id",
                str(learn["scope_id"]),
                "--json",
            )
            recovered_context = json.loads(
                self.run_memory(
                    project,
                    "context",
                    "--query",
                    "Profile loadProfile",
                    "--compact",
                    "--json",
                ).stdout
            )
            recovered_health = json.loads(
                self.run_memory(project, "maintain-health", "--json").stdout
            )

        self.assertEqual(1, len(boundaries))
        self.assertEqual("business/Profile.ts", boundaries[0]["consumer_path"])
        self.assertEqual("shared/Auth.ts", boundaries[0]["dependency_path"])
        self.assertEqual([], refreshed["change_set"]["scope_candidate_paths"])
        self.assertEqual(
            ["shared/Auth.ts"],
            refreshed["change_set"]["boundary_candidate_paths"],
        )
        self.assertEqual([], refreshed["refreshed_files"])
        self.assertEqual("shared/Auth.ts", refreshed["boundary_changes"][0]["dependency_path"])
        self.assertFalse(refreshed["boundary_changes"][0]["surface_changed"])
        self.assertEqual({"business/Profile.ts"}, code_files)
        self.assertEqual("boundary_drift", context["source_freshness"]["status"])
        self.assertEqual([learn["scope_id"]], context["source_freshness"]["boundary_drift_scope_ids"])
        self.assertEqual(1, health["counts"]["scope_boundary_drift"])
        self.assertEqual("current", recovered_context["source_freshness"]["status"])
        self.assertEqual(0, recovered_health["counts"]["scope_boundary_drift"])


if __name__ == "__main__":
    import unittest

    unittest.main()
