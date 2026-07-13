# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"


class RefreshScopeTests(unittest.TestCase):
    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

    def run_memory(
        self,
        project: Path,
        *args: str,
        memory_home: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(RUNTIME), *args, "--project", str(project)]
        command.extend(["--memory-home", str(memory_home or self.memory_home(project))])
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
            env=os.environ.copy(),
        )

    def list_code_files(self, project: Path) -> set[str]:
        result = self.run_memory(project, "list", "--type", "code-file", "--json")
        return {row["file_path"] for row in json.loads(result.stdout)}

    def code_file_rows(self, project: Path) -> list[dict[str, object]]:
        result = self.run_memory(project, "list", "--type", "code-file", "--json")
        return json.loads(result.stdout)

    def test_maintain_refresh_scope_changed_only_reindexes_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text("@Component\nstruct A { build() { console.error('old a'); } }\n", encoding="utf-8")
            (pages / "B.ets").write_text("@Component\nstruct B { build() { console.error('old b'); } }\n", encoding="utf-8")
            (pages / "D.ets").write_text("@Component\nstruct D { build() { console.error('stable d'); } }\n", encoding="utf-8")

            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            (pages / "A.ets").write_text("@Component\nstruct A { build() { console.error('new a'); } }\n", encoding="utf-8")
            (pages / "B.ets").unlink()
            (pages / "C.ets").write_text("@Component\nstruct C { build() { console.error('new c'); } }\n", encoding="utf-8")

            result = self.run_memory(project, "maintain-refresh-scope", "--changed-only", "--json")
            payload = json.loads(result.stdout)
            code_files = self.list_code_files(project)

        scope = payload["scopes"][0]
        self.assertTrue(scope["changed_only"])
        self.assertEqual(["pages/A.ets", "pages/C.ets"], scope["refreshed_files"])
        self.assertEqual(2, scope["parse_stats"]["files_indexed"])
        self.assertIn("pages/B.ets", scope["parse_stats"]["retired_files"])
        edge_rebuild = scope["parse_stats"]["edge_rebuild"]
        self.assertEqual("merge", edge_rebuild["mode"])
        self.assertEqual(["pages/A.ets", "pages/C.ets"], edge_rebuild["scope_files"])
        self.assertGreaterEqual(edge_rebuild["before"]["edge_count"], 1)
        self.assertGreaterEqual(edge_rebuild["after"]["edge_count"], edge_rebuild["before"]["edge_count"])
        self.assertIn("contains", edge_rebuild["after"]["relation_counts"])
        self.assertEqual({"pages/A.ets", "pages/C.ets", "pages/D.ets"}, code_files)

    def test_changed_refresh_preserves_business_summary_and_records_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "Profile.ets").write_text(
                "@Component\nstruct Profile { build() { console.error('load profile'); } }\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            business_payload = {
                "files": [
                    {
                        "file_path": "pages/Profile.ets",
                        "business_summary": "用户资料详情页，展示头像和昵称",
                        "business_terms": ["用户资料", "头像", "昵称"],
                    }
                ]
            }
            self.run_memory(project, "learn-business", "--payload", json.dumps(business_payload), "--json")

            (pages / "Profile.ets").write_text(
                "@Component\nstruct Profile { build() { console.error('refresh profile avatar'); } }\n",
                encoding="utf-8",
            )
            result = self.run_memory(project, "maintain-refresh-scope", "--changed-only", "--json")
            payload = json.loads(result.stdout)
            file_rows = self.code_file_rows(project)
            conflicts = json.loads(
                self.run_memory(project, "list", "--type", "semantic-conflict", "--json").stdout
            )

        profile_row = next(row for row in file_rows if row["file_path"] == "pages/Profile.ets")
        scope = payload["scopes"][0]
        self.assertEqual("用户资料详情页，展示头像和昵称", profile_row["business_summary"])
        self.assertEqual(1, scope["parse_stats"]["business_semantics_restored"]["code_files"])
        self.assertEqual("maintain-refresh-scope", scope["semantic_conflicts"][0]["source_command"])
        self.assertEqual("pages/Profile.ets", scope["semantic_conflicts"][0]["target"])
        self.assertIn("logs added: refresh profile avatar", scope["semantic_conflicts"][0]["incoming"])
        self.assertIn("logs removed: load profile", scope["semantic_conflicts"][0]["incoming"])
        self.assertTrue(
            any(
                row["target"] == "pages/Profile.ets"
                and row["existing"] == "用户资料详情页，展示头像和昵称"
                and row["source_command"] == "maintain-refresh-scope"
                and "logs added: refresh profile avatar" in row["incoming"]
                for row in conflicts
            )
        )


if __name__ == "__main__":
    unittest.main()
