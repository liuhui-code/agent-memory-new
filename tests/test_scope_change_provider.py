# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


class ScopeChangeProviderTests(AgentMemoryTestBase):
    def git(self, project: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(project), *args],
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()

    def init_repo(self, project: Path) -> str:
        self.git(project, "init", "-q")
        self.git(project, "config", "user.email", "tests@example.com")
        self.git(project, "config", "user.name", "Agent Memory Tests")
        self.git(project, "add", ".")
        self.git(project, "commit", "-q", "-m", "initial")
        return self.git(project, "rev-parse", "HEAD")

    def write(self, project: Path, relative: str, content: str) -> None:
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def refresh(self, project: Path) -> dict:
        result = self.run_memory(
            project, "maintain-refresh-scope", "--changed-only", "--json"
        )
        return json.loads(result.stdout)["scopes"][0]

    def test_git_candidates_are_scope_filtered_and_commits_are_coalesced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write(project, "business/Profile.ets", "export const value = 'v1'\n")
            self.write(project, "noise/Other.ets", "export const noise = 'v1'\n")
            baseline = self.init_repo(project)
            self.run_memory(project, "learn-path", "--path", "business", "--json")

            self.write(project, "business/Profile.ets", "export const value = 'v2'\n")
            self.write(project, "noise/Other.ets", "export const noise = 'v2'\n")
            self.git(project, "add", ".")
            self.git(project, "commit", "-q", "-m", "team change one")
            self.write(project, "business/Profile.ets", "export const value = 'v3'\n")
            self.write(project, "noise/Second.ets", "export const noise2 = 'v1'\n")
            self.git(project, "add", ".")
            self.git(project, "commit", "-q", "-m", "team change two")
            self.write(project, "business/Profile.ets", "export const value = 'v4'\n")
            self.write(project, "business/New.ets", "export const added = true\n")

            scope = self.refresh(project)
            repeated = self.refresh(project)

        change_set = scope["change_set"]
        self.assertEqual("git/v1", change_set["provider"])
        self.assertEqual(baseline, change_set["baseline_revision"])
        self.assertEqual(
            ["business/New.ets", "business/Profile.ets"],
            change_set["candidate_paths"],
        )
        self.assertEqual(["business/New.ets"], scope["added_files"])
        self.assertEqual(["business/Profile.ets"], scope["changed_files"])
        self.assertEqual([], repeated["changed_files"])
        self.assertEqual([], repeated["refreshed_files"])

    def test_outside_only_commit_advances_checkpoint_without_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write(project, "business/Profile.ets", "export const value = 'v1'\n")
            self.write(project, "noise/Other.ets", "export const noise = 'v1'\n")
            baseline = self.init_repo(project)
            self.run_memory(project, "learn-path", "--path", "business", "--json")
            self.write(project, "noise/Other.ets", "export const noise = 'v2'\n")
            self.git(project, "add", "noise/Other.ets")
            self.git(project, "commit", "-q", "-m", "unrelated team change")
            current = self.git(project, "rev-parse", "HEAD")

            scope = self.refresh(project)
            learned_scope = self.list_records(project, "learn-scope")[0]

        self.assertNotEqual(baseline, current)
        self.assertEqual([], scope["change_set"]["candidate_paths"])
        self.assertEqual([], scope["refreshed_files"])
        self.assertEqual(current, learned_scope["baseline_revision"])
        self.assertEqual("current", learned_scope["refresh_state"])

    def test_missing_git_baseline_falls_back_to_snapshot_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write(project, "business/Profile.ets", "export const value = 'v1'\n")
            self.init_repo(project)
            self.run_memory(project, "learn-path", "--path", "business", "--json")
            db_path = self.project_memory_dir(project) / "memory.db"
            with sqlite3.connect(db_path) as conn:
                conn.execute("UPDATE learn_scopes SET baseline_revision = NULL")
                conn.commit()
            self.write(project, "business/Profile.ets", "export const value = 'v2'\n")

            scope = self.refresh(project)

        self.assertEqual("snapshot/v1", scope["change_set"]["provider"])
        self.assertEqual("baseline_missing", scope["change_set"]["fallback_reason"])
        self.assertEqual(["business/Profile.ets"], scope["changed_files"])

    def test_relevant_change_overflow_keeps_previous_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write(project, "business/Profile.ets", "export const value = 'v1'\n")
            baseline = self.init_repo(project)
            self.run_memory(project, "learn-path", "--path", "business", "--json")
            for index in range(201):
                self.write(
                    project,
                    f"business/New{index:03d}.ets",
                    f"export const value{index} = true\n",
                )
            self.git(project, "add", "business")
            self.git(project, "commit", "-q", "-m", "large relevant change")
            current = self.git(project, "rev-parse", "HEAD")

            scope = self.refresh(project)
            learned_scope = self.list_records(project, "learn-scope")[0]
            code_files = self.list_records(project, "code-file")
            health = json.loads(
                self.run_memory(project, "maintain-health", "--json").stdout
            )
            recovered = json.loads(
                self.run_memory(
                    project,
                    "maintain-refresh-scope",
                    "--scope-id",
                    str(scope["scope_id"]),
                    "--json",
                ).stdout
            )["scopes"][0]
            recovered_scope = self.list_records(project, "learn-scope")[0]
            with sqlite3.connect(self.project_memory_dir(project) / "memory.db") as conn:
                recovered_file_count = conn.execute(
                    "SELECT COUNT(*) FROM code_files"
                ).fetchone()[0]

        self.assertEqual("overflow", scope["status"])
        self.assertEqual(201, scope["change_set"]["candidate_file_count"])
        self.assertTrue(scope["change_set"]["overflow"])
        self.assertEqual(baseline, learned_scope["baseline_revision"])
        self.assertEqual(current, learned_scope["last_checked_revision"])
        self.assertEqual("overflow", learned_scope["refresh_state"])
        self.assertEqual(["business/Profile.ets"], [row["file_path"] for row in code_files])
        self.assertEqual(1, health["counts"]["scope_overflow"])
        self.assertEqual("overflow", health["scope_health"][0]["health_status"])
        self.assertTrue(
            any("overflow learn scopes" in item for item in health["recommended_actions"])
        )
        self.assertEqual("refreshed", recovered["status"])
        self.assertEqual("full-scan/v1", recovered["change_set"]["provider"])
        self.assertEqual(current, recovered_scope["baseline_revision"])
        self.assertEqual("current", recovered_scope["refresh_state"])
        self.assertEqual(202, recovered_file_count)

    def test_entry_scope_recomputes_import_closure_after_git_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write(
                project,
                "src/Entry.ts",
                "import { old } from './Old'\nexport const entry = old\n",
            )
            self.write(project, "src/Old.ts", "export const old = true\n")
            self.write(project, "src/New.ts", "export const next = true\n")
            self.init_repo(project)
            self.run_memory(
                project, "learn-entry", "--entry", "src/Entry.ts", "--depth", "1", "--json"
            )
            self.write(
                project,
                "src/Entry.ts",
                "import { next } from './New'\nexport const entry = next\n",
            )
            self.git(project, "add", "src/Entry.ts")
            self.git(project, "commit", "-q", "-m", "switch dependency")

            scope = self.refresh(project)
            code_files = {row["file_path"] for row in self.list_records(project, "code-file")}

        self.assertEqual(["src/Entry.ts"], scope["change_set"]["candidate_paths"])
        self.assertEqual(["src/New.ts"], scope["added_files"])
        self.assertEqual(["src/Old.ts"], scope["removed_files"])
        self.assertEqual({"src/Entry.ts", "src/New.ts"}, code_files)

    def test_external_source_subdirectory_keeps_git_paths_source_relative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            repository = workspace / "repository"
            source = repository / "source"
            archive = workspace / "archive"
            archive.mkdir()
            self.write(source, "business/Profile.ets", "export const value = 'v1'\n")
            self.write(repository, "other/Noise.ets", "export const noise = 'v1'\n")
            self.init_repo(repository)
            self.run_memory(
                archive,
                "learn-path",
                "--source",
                str(source),
                "--path",
                "business",
                "--json",
            )
            self.write(source, "business/Profile.ets", "export const value = 'v2'\n")
            self.write(repository, "other/Noise.ets", "export const noise = 'v2'\n")
            self.git(repository, "add", ".")
            self.git(repository, "commit", "-q", "-m", "mixed repository update")

            scope = self.refresh(archive)

        self.assertEqual(["business/Profile.ets"], scope["change_set"]["candidate_paths"])
        self.assertEqual(["business/Profile.ets"], scope["changed_files"])

    def test_previously_learned_ignored_file_still_uses_digest_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.write(project, ".gitignore", "business/Generated.ets\n")
            self.write(project, "business/Profile.ets", "export const value = 'v1'\n")
            self.write(project, "business/Generated.ets", "export const generated = 'v1'\n")
            self.init_repo(project)
            self.run_memory(project, "learn-path", "--path", "business", "--json")
            self.write(project, "business/Generated.ets", "export const generated = 'v2'\n")

            scope = self.refresh(project)

        self.assertEqual(["business/Generated.ets"], scope["change_set"]["candidate_paths"])
        self.assertEqual(["business/Generated.ets"], scope["changed_files"])


if __name__ == "__main__":
    import unittest

    unittest.main()
