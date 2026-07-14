# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart01Tests(AgentMemoryTestBase):
    def test_runtime_modules_expose_project_and_text_helpers(self) -> None:
        from tools.agent_memory_runtime.cli import build_parser
        from tools.agent_memory_runtime.code_wiki import language_for
        from tools.agent_memory_runtime.governance import reflection_quality_action
        from tools.agent_memory_runtime.models import Project
        from tools.agent_memory_runtime.query import network_limits
        from tools.agent_memory_runtime.records import table_for_type
        from tools.agent_memory_runtime.storage import resolve_project
        from tools.agent_memory_runtime.text import json_list, query_tokens
        from tools.agent_memory_runtime.vault import slugify

        self.assertEqual(Project.__name__, "Project")
        self.assertEqual(build_parser({}).prog, "agent_memory.py")
        self.assertEqual(language_for(Path("entry/src/main/ets/pages/Home.ets")), "ArkTS")
        self.assertEqual(reflection_quality_action(["missing_scope"]), "rewrite")
        self.assertEqual(network_limits()["max_depth"], 1)
        self.assertEqual(table_for_type("code-log"), "code_log_statements")
        self.assertEqual(table_for_type("learn-scope"), "learn_scopes")
        self.assertEqual(table_for_type("reflection-reuse"), "reflection_reuse_events")
        self.assertEqual(resolve_project(".", None).project_name, "agent-memory-new")
        self.assertEqual(slugify("Hello Agent Memory!", "fallback"), "hello-agent-memory")
        self.assertEqual(json_list('["profile", "avatar"]'), ["profile", "avatar"])
        self.assertIn("router", query_tokens("页面跳转后白屏"))

    def test_all_project_python_files_include_public_fingerprint(self) -> None:
        python_files = [
            path for path in REPO_ROOT.rglob("*.py")
            if ".pycache" not in path.parts
            and ".agent-memory" not in path.parts
            and "node_modules" not in path.parts
        ]

        missing = [
            str(path.relative_to(REPO_ROOT))
            for path in python_files
            if PROJECT_FINGERPRINT not in path.read_text(encoding="utf-8")
        ]

        self.assertEqual([], missing)

    def test_experience_phase_one_docs_define_candidate_protocol(self) -> None:
        plan = (REPO_ROOT / "docs" / "experience-system-plan.md").read_text(encoding="utf-8")
        reflect_skill = (REPO_ROOT / "skills" / "agent-memory-reflect" / "SKILL.md").read_text(encoding="utf-8")
        query_skill = (REPO_ROOT / "skills" / "agent-memory-query" / "SKILL.md").read_text(encoding="utf-8")

        for required in [
            "Experience Candidate Loop",
            "hidden_assumptions",
            "negative_preconditions",
            "verification_method",
            "reuse_feedback",
            "source_cases",
            "skill_candidate",
        ]:
            self.assertIn(required, plan)

        for required in [
            "experience candidate",
            "hidden_assumptions",
            "verification_method",
            "reuse_feedback",
            "negative_preconditions",
        ]:
            self.assertIn(required, reflect_skill)

        self.assertIn("experience candidates", query_skill)
        self.assertIn("verify them against current source, logs, tests, and code wiki evidence", query_skill)

    def test_init_uses_configured_global_memory_home_without_project_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            memory_home = root / "global-memory"
            project.mkdir()

            self.run_memory(project, "init", memory_home=memory_home)

            project_memory = memory_home / "projects" / self.project_id(project)
            self.assertTrue((project_memory / "memory.db").exists())
            self.assertTrue((project_memory / "runtime").exists())
            self.assertTrue((project_memory / "vault").exists())
            self.assertFalse((project / ".agent-memory").exists())

    def test_environment_memory_home_is_used_when_cli_option_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "app"
            memory_home = root / "env-memory"
            project.mkdir()

            self.run_memory(
                project,
                "init",
                use_memory_home_arg=False,
                env={"AGENT_MEMORY_HOME": str(memory_home)},
            )

            self.assertTrue((memory_home / "projects" / self.project_id(project) / "memory.db").exists())
            self.assertFalse((project / ".agent-memory").exists())

    def test_default_memory_home_is_current_workspace_agent_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            project = workspace / "app"
            project.mkdir()

            command = [sys.executable, str(RUNTIME), "init", "--project", str(project)]
            process_env = os.environ.copy()
            process_env.pop("AGENT_MEMORY_HOME", None)
            subprocess.run(
                command,
                cwd=workspace,
                text=True,
                capture_output=True,
                check=True,
                env=process_env,
            )

            self.assertTrue((workspace / ".agent-memory" / "projects" / self.project_id(project) / "memory.db").exists())
            self.assertFalse((Path.home() / ".agent-memory" / "projects" / self.project_id(project) / "memory.db").exists())

    def test_global_memory_home_keeps_project_databases_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory_home = root / "memory"
            project_a = root / "app-a"
            project_b = root / "app-b"
            project_a.mkdir()
            project_b.mkdir()

            self.run_memory(
                project_a,
                "update",
                "--type",
                "semantic",
                "--fact",
                "Project A fact",
                "--source",
                "test",
                memory_home=memory_home,
            )
            self.run_memory(
                project_b,
                "update",
                "--type",
                "semantic",
                "--fact",
                "Project B fact",
                "--source",
                "test",
                memory_home=memory_home,
            )

            facts_a = self.list_records(project_a, "semantic", memory_home=memory_home)
            facts_b = self.list_records(project_b, "semantic", memory_home=memory_home)
            self.assertEqual([row["fact"] for row in facts_a], ["Project A fact"])
            self.assertEqual([row["fact"] for row in facts_b], ["Project B fact"])

    def test_learn_path_merges_index_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "a").mkdir()
            (project / "b").mkdir()
            (project / "a" / "one.py").write_text("def one():\n    return 1\n", encoding="utf-8")
            (project / "b" / "two.py").write_text("def two():\n    return 2\n", encoding="utf-8")

            self.run_memory(project, "learn-path", "--path", "a")
            self.run_memory(project, "learn-path", "--path", "b")

            self.assertEqual(self.list_code_files(project), {"a/one.py", "b/two.py"})

    def test_learn_path_can_archive_external_source_into_current_project_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "memory-archive"
            source = root / "external-app"
            archive.mkdir()
            (source / "lib").mkdir(parents=True)
            (source / "lib" / "main.py").write_text(
                "def bootstrap():\n"
                "    return 'external app'\n",
                encoding="utf-8",
            )

            self.run_memory(archive, "learn-path", "--source", str(source), "--path", "lib", "--json")

            self.assertEqual(self.list_code_files(archive), {"lib/main.py"})
            self.assertEqual(self.list_code_files(source, memory_home=self.memory_home(archive)), set())
            result = self.run_memory(archive, "context", "--query", "bootstrap external app", "--json")
            payload = json.loads(result.stdout)
            self.assertTrue(any(row["file_path"] == "lib/main.py" for row in payload["wiki_matches"]))

    def test_learn_entry_follows_imports_inside_external_source_but_archives_current_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "memory-archive"
            source = root / "external-harmony"
            archive.mkdir()
            (source / "pages").mkdir(parents=True)
            (source / "model").mkdir()
            (source / "pages" / "Index.ets").write_text(
                "import { UserModel } from '../model/UserModel';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index { build() {} }\n",
                encoding="utf-8",
            )
            (source / "model" / "UserModel.ets").write_text(
                "export class UserModel {}\n",
                encoding="utf-8",
            )

            self.run_memory(
                archive,
                "learn-entry",
                "--source",
                str(source),
                "--entry",
                "pages/Index.ets",
                "--depth",
                "1",
                "--json",
            )

            self.assertEqual(self.list_code_files(archive), {"pages/Index.ets", "model/UserModel.ets"})
            self.assertEqual(self.list_code_files(source, memory_home=self.memory_home(archive)), set())

    def test_wiki_index_can_replace_archive_from_external_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "memory-archive"
            source = root / "external-app"
            archive.mkdir()
            (source / "feature").mkdir(parents=True)
            (source / "feature" / "page.ets").write_text(
                "@Component\n"
                "struct FeaturePage { build() {} }\n",
                encoding="utf-8",
            )

            self.run_memory(archive, "wiki-index", "--source", str(source))

            self.assertEqual(self.list_code_files(archive), {"feature/page.ets"})

    def test_learn_path_replace_keeps_only_latest_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "a").mkdir()
            (project / "b").mkdir()
            (project / "a" / "one.py").write_text("def one():\n    return 1\n", encoding="utf-8")
            (project / "b" / "two.py").write_text("def two():\n    return 2\n", encoding="utf-8")

            self.run_memory(project, "learn-path", "--path", "a")
            self.run_memory(project, "learn-path", "--path", "b", "--replace")

            self.assertEqual(self.list_code_files(project), {"b/two.py"})

    def test_learn_path_records_persistent_learn_scope_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "src").mkdir()
            (project / "src" / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")

            result = self.run_memory(project, "learn-path", "--path", "src", "--json")

            payload = json.loads(result.stdout)
            scopes = self.list_records(project, "learn-scope")
            self.assertEqual(payload["scope_id"], scopes[0]["id"])
            self.assertEqual(scopes[0]["scope_type"], "path")
            self.assertEqual(scopes[0]["target_path"], "src")
            self.assertEqual(scopes[0]["mode"], "merge")
            self.assertEqual(scopes[0]["file_count"], 1)
            snapshot = json.loads(scopes[0]["file_snapshot"])
            self.assertEqual(list(snapshot.keys()), ["src/app.py"])

    def test_maintain_refresh_scope_updates_structure_and_reports_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text(
                "@Component\nstruct A { build() { console.error('old a'); } }\n",
                encoding="utf-8",
            )
            (pages / "B.ets").write_text(
                "@Component\nstruct B { build() { console.error('old b'); } }\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages", "--json")

            (pages / "A.ets").write_text(
                "@Component\nstruct A { build() { console.error('new a'); } }\n",
                encoding="utf-8",
            )
            (pages / "B.ets").unlink()
            (pages / "C.ets").write_text(
                "@Component\nstruct C { build() { console.error('new c'); } }\n",
                encoding="utf-8",
            )

            result = self.run_memory(project, "maintain-refresh-scope", "--json")

            payload = json.loads(result.stdout)
            self.assertEqual(payload["scope_count"], 1)
            scope = payload["scopes"][0]
            self.assertEqual(scope["status"], "refreshed")
            self.assertEqual(scope["scope_type"], "path")
            self.assertIn("pages/C.ets", scope["added_files"])
            self.assertIn("pages/A.ets", scope["changed_files"])
            self.assertIn("pages/B.ets", scope["removed_files"])
            self.assertTrue(scope["semantic_review_targets"]["drift_detected"])
            self.assertEqual(
                set(scope["semantic_review_targets"]["file_paths"]),
                {"pages/A.ets", "pages/B.ets", "pages/C.ets"},
            )
            self.assertEqual(self.list_code_files(project), {"pages/A.ets", "pages/C.ets"})

    def test_partial_relearn_preserves_unrelated_edge_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text("@Component\nstruct A { build() {} }\n", encoding="utf-8")
            (pages / "B.ets").write_text("@Component\nstruct B { build() {} }\n", encoding="utf-8")

            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            before = self.list_records(project, "memory-edge")
            before_b_ids = {
                row["id"]
                for row in before
                if "pages/B.ets" in str(row.get("evidence") or "")
            }

            (pages / "A.ets").write_text(
                "@Component\nstruct A { build() { console.error('updated'); } }\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", "pages/A.ets", "--json")

            after = self.list_records(project, "memory-edge")
            after_b_ids = {
                row["id"]
                for row in after
                if "pages/B.ets" in str(row.get("evidence") or "")
            }
            self.assertEqual(before_b_ids, after_b_ids)

    def test_search_indexes_exist_and_recall_matching_fact(self) -> None:
        from tools.agent_memory_runtime.query import recall_candidate_ids
        from tools.agent_memory_runtime.storage import connect, ensure_initialized, resolve_project

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            runtime_project = resolve_project(str(project), str(self.memory_home(project)))
            ensure_initialized(runtime_project)
            for index in range(40):
                self.run_memory(
                    project,
                    "update",
                    "--type",
                    "semantic",
                    "--fact",
                    f"generic filler fact {index}",
                    "--source",
                    "test",
                )
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "ArkTS route blank screen investigation playbook",
                "--source",
                "test",
            )
            with connect(runtime_project) as conn:
                fts_count = conn.execute("SELECT COUNT(*) AS count FROM semantic_fact_fts").fetchone()["count"]
                ids = recall_candidate_ids(conn, runtime_project, "semantic_facts", "route blank screen", 20)
                self.assertGreaterEqual(fts_count, 41)
                self.assertTrue(ids)

    def test_duplicate_candidates_only_consider_recent_review_pool(self) -> None:
        from tools.agent_memory_runtime.governance import duplicate_candidates

        rows = [
            {"id": index, "fact": f"generic fact {index}"}
            for index in range(1, 2501)
        ]
        rows[0]["fact"] = "legacy duplicate candidate"
        rows[1]["fact"] = "legacy duplicate candidate"

        candidates = duplicate_candidates(rows, "semantic", limit=10)
        self.assertEqual([], candidates)

    def test_maintain_plan_surfaces_recent_refresh_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text("@Component\nstruct A { build() {} }\n", encoding="utf-8")
            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            (pages / "A.ets").write_text(
                "@Component\nstruct A { build() { console.error('updated'); } }\n",
                encoding="utf-8",
            )
            self.run_memory(project, "maintain-refresh-scope", "--json")

            result = self.run_memory(project, "maintain-plan", "--json")

            payload = json.loads(result.stdout)
            self.assertEqual(payload["summary"]["refresh_drifts"], 1)
            drift_actions = [action for action in payload["actions"] if action["action"] == "review_semantic_drift"]
            self.assertEqual(len(drift_actions), 1)
            self.assertEqual(drift_actions[0]["scope_type"], "path")
            self.assertIn("pages/A.ets", drift_actions[0]["changed_files"])
