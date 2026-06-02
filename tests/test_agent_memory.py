# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import os
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = REPO_ROOT / "tools" / "agent_memory.py"
PROJECT_FINGERPRINT = "sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77"


class AgentMemoryRuntimeTests(unittest.TestCase):
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
            if ".pycache" not in path.parts and ".agent-memory" not in path.parts
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

    def memory_home(self, project: Path) -> Path:
        return project.parent / f"memory-home-{project.name}"

    def project_memory_dir(self, project: Path) -> Path:
        project_id = self.project_id(project)
        return self.memory_home(project) / "projects" / project_id

    def project_id(self, project: Path) -> str:
        import hashlib

        return hashlib.sha256(str(project.resolve()).encode("utf-8")).hexdigest()[:16]

    def run_memory(
        self,
        project: Path,
        *args: str,
        memory_home: Optional[Path] = None,
        use_memory_home_arg: bool = True,
        env: Optional[dict[str, str]] = None,
        cwd: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(RUNTIME), *args, "--project", str(project)]
        if use_memory_home_arg:
            command.extend(["--memory-home", str(memory_home or self.memory_home(project))])
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        return subprocess.run(
            command,
            cwd=cwd or REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
            env=process_env,
        )

    def list_code_files(self, project: Path, memory_home: Optional[Path] = None) -> set[str]:
        result = self.run_memory(
            project,
            "list",
            "--type",
            "code-file",
            "--json",
            memory_home=memory_home,
        )
        return {row["file_path"] for row in json.loads(result.stdout)}

    def list_records(self, project: Path, kind: str, memory_home: Optional[Path] = None) -> list[dict]:
        result = self.run_memory(
            project,
            "list",
            "--type",
            kind,
            "--json",
            memory_home=memory_home,
        )
        return json.loads(result.stdout)

    def miss_list(self, project: Path, memory_home: Optional[Path] = None) -> list[dict]:
        result = self.run_memory(project, "miss-list", "--json", memory_home=memory_home)
        return json.loads(result.stdout)

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

    def test_maintain_health_reports_scope_health_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text("@Component\nstruct A { build() {} }\n", encoding="utf-8")
            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            (pages / "A.ets").write_text("@Component\nstruct A { build() { console.error('updated'); } }\n", encoding="utf-8")
            self.run_memory(project, "maintain-refresh-scope", "--json")

            result = self.run_memory(project, "maintain-health", "--json")
            payload = json.loads(result.stdout)
            self.assertEqual(payload["counts"]["learn_scopes"], 1)
            self.assertEqual(payload["counts"]["scope_with_drift"], 1)
            self.assertEqual(payload["scope_health"][0]["health_status"], "drift")

    def test_maintain_plan_flags_reflections_when_removed_file_anchor_disappears(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text("@Component\nstruct A { build() {} }\n", encoding="utf-8")
            (pages / "B.ets").write_text("@Component\nstruct B { build() {} }\n", encoding="utf-8")
            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            payload = {
                "experience_type": "procedure_experience",
                "task_type": "diagnosis",
                "outcome": "success",
                "task": "diagnose removed page issue",
                "lesson": "Removed page anchors should be reviewed.",
                "future_rule": "If a referenced page disappears, review old experience before reuse.",
                "scope": "ArkTS page diagnosis",
                "evidence": "pages/B.ets",
                "trigger_condition": "Linked page file is removed",
                "repair_action": "Review or stale related experience",
                "hidden_assumptions": ["pages/B.ets still exists"],
                "negative_preconditions": ["Do not apply when the file still exists"],
                "verification_method": "Check the current code tree for the referenced file",
                "reuse_feedback": "candidate",
                "source_cases": ["file: pages/B.ets"],
                "inspection_targets": ["pages/B.ets"],
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))
            (pages / "B.ets").unlink()
            self.run_memory(project, "maintain-refresh-scope", "--json")

            result = self.run_memory(project, "maintain-plan", "--json")

            payload = json.loads(result.stdout)
            stale_actions = [
                action
                for action in payload["actions"]
                if action["action"] == "mark_experience_stale_if_anchor_removed"
            ]
            self.assertEqual(len(stale_actions), 1)
            self.assertIn("pages/B.ets", stale_actions[0]["removed_files"])
            self.assertEqual(stale_actions[0]["linked_reflection_ids"], [1])

    def test_maintain_plan_flags_skill_pattern_staleness_when_removed_anchor_hits_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text("@Component\nstruct A { build() {} }\n", encoding="utf-8")
            (pages / "B.ets").write_text("@Component\nstruct B { build() {} }\n", encoding="utf-8")
            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            for task in ("first route issue", "second route issue"):
                payload = {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "task": task,
                    "lesson": "Removed page anchors should be reviewed.",
                    "future_rule": "If a referenced page disappears, review old experience before reuse.",
                    "scope": "ArkTS page diagnosis",
                    "evidence": "pages/B.ets",
                    "trigger_condition": "Linked page file is removed",
                    "repair_action": "Review or stale related experience",
                    "hidden_assumptions": ["pages/B.ets still exists"],
                    "negative_preconditions": ["Do not apply when the file still exists"],
                    "verification_method": "Check the current code tree for the referenced file",
                    "reuse_feedback": "candidate",
                    "source_cases": ["file: pages/B.ets"],
                    "inspection_targets": ["pages/B.ets"],
                    "skill_candidate": "removed-anchor-review",
                }
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))
            (pages / "B.ets").unlink()
            self.run_memory(project, "maintain-refresh-scope", "--json")

            result = self.run_memory(project, "maintain-plan", "--json")
            payload = json.loads(result.stdout)
            actions = [action for action in payload["actions"] if action["action"] == "review_skill_pattern_staleness"]
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0]["pattern_name"], "removed-anchor-review")

    def test_maintain_status_marks_semantic_stale_and_context_excludes_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "SQLite source of truth",
                "--source",
                "test",
                "--confidence",
                "1.0",
            )

            self.run_memory(
                project,
                "maintain-status",
                "--type",
                "semantic",
                "--id",
                "1",
                "--status",
                "stale",
                "--reason",
                "test stale",
            )
            context = self.run_memory(project, "context", "--query", "SQLite", "--json")

            facts = self.list_records(project, "semantic")
            self.assertEqual(facts[0]["status"], "stale")
            self.assertEqual(json.loads(context.stdout)["semantic_facts"], [])

    def test_maintain_promote_episode_to_semantic_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "update",
                "--type",
                "episode",
                "--task",
                "review task",
                "--summary",
                "learned durable fact",
            )

            result = self.run_memory(
                project,
                "maintain-promote",
                "--episode-id",
                "1",
                "--fact",
                "Durable promoted fact",
                "--json",
            )

            payload = json.loads(result.stdout)
            facts = self.list_records(project, "semantic")
            episodes = self.list_records(project, "episode")
            self.assertEqual(payload["semantic_fact_id"], 1)
            self.assertEqual(facts[0]["fact"], "Durable promoted fact")
            self.assertEqual(episodes[0]["derived_facts"], "[1]")

    def test_maintain_merge_marks_old_semantic_records_merged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            for fact in ("Skill calls runtime script", "Skills call runtime script"):
                self.run_memory(
                    project,
                    "update",
                    "--type",
                    "semantic",
                    "--fact",
                    fact,
                    "--source",
                    "test",
                )

            result = self.run_memory(
                project,
                "maintain-merge",
                "--type",
                "semantic",
                "--ids",
                "1,2",
                "--fact",
                "Skills call the runtime script.",
                "--json",
            )

            payload = json.loads(result.stdout)
            facts = sorted(self.list_records(project, "semantic"), key=lambda row: row["id"])
            self.assertEqual(payload["merged_into_id"], 3)
            self.assertEqual([facts[0]["status"], facts[1]["status"], facts[2]["status"]], ["merged", "merged", "active"])
            self.assertEqual([facts[0]["merged_into_id"], facts[1]["merged_into_id"]], [3, 3])

    def test_maintain_plan_outputs_confirmable_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            for fact in ("Runtime uses SQLite", "Runtime uses SQLite"):
                self.run_memory(
                    project,
                    "update",
                    "--type",
                    "semantic",
                    "--fact",
                    fact,
                    "--source",
                    "test",
                )
            self.run_memory(
                project,
                "update",
                "--type",
                "episode",
                "--task",
                "planned review",
                "--summary",
                "may contain durable knowledge",
            )
            self.run_memory(
                project,
                "maintain-status",
                "--type",
                "semantic",
                "--id",
                "2",
                "--status",
                "stale",
                "--reason",
                "test stale",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            payload = json.loads(result.stdout)
            actions = payload["actions"]

            self.assertEqual(payload["summary"]["stale"], 1)
            self.assertTrue(all(action["requires_confirmation"] for action in actions))
            self.assertIn("archive", {action["action"] for action in actions})
            self.assertIn("promote_or_archive", {action["action"] for action in actions})
            self.assertTrue(any(action["type"] == "semantic" and action["id"] == 2 for action in actions))

    def test_reflect_writes_actionable_quality_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(
                project,
                "reflect",
                "--task",
                "change runtime command",
                "--lesson",
                "Command behavior changes need tests and docs.",
                "--future-rule",
                "Update parser, tests, skill docs, usage guide, and gitlog together.",
                "--trigger-condition",
                "When changing runtime CLI behavior",
                "--anti-pattern",
                "Only update parser implementation",
                "--repair-action",
                "Update tests, docs, and skill instructions in the same change",
                "--applies-to",
                "runtime command behavior changes",
                "--does-not-apply-to",
                "docs-only edits",
            )

            reflection = self.list_records(project, "reflection")[0]
            self.assertEqual(reflection["trigger_condition"], "When changing runtime CLI behavior")
            self.assertEqual(reflection["anti_pattern"], "Only update parser implementation")
            self.assertEqual(reflection["repair_action"], "Update tests, docs, and skill instructions in the same change")
            self.assertEqual(reflection["applies_to"], "runtime command behavior changes")
            self.assertEqual(reflection["does_not_apply_to"], "docs-only edits")

    def test_reflect_payload_writes_agent_structured_task_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "experience_type": "procedure_experience",
                "task_type": "diagnosis",
                "outcome": "success",
                "problem": "Profile page shows a blank screen after navigation.",
                "task": "diagnose profile blank page",
                "summary": "Queried memory, inspected route registration, and found the profile route path mismatch.",
                "reasoning_summary": "The useful clue was the route_to edge from Home to ProfileDetail plus the router.pushUrl log.",
                "context_used": [
                    "query: profile blank page route",
                    "file: entry/src/main/ets/pages/Home.ets",
                    "log: router.pushUrl failed",
                    "reflection:#3",
                ],
                "what_worked": [
                    "Search by business term profile before scanning all pages.",
                    "Check route edges before editing UI state.",
                ],
                "what_failed": [
                    "Searching only for blank screen was too broad.",
                ],
                "hidden_assumptions": [
                    "The blank screen started after a successful route push.",
                    "The destination page was expected to exist in page registration.",
                ],
                "negative_preconditions": [
                    "Does not apply when the page never navigates.",
                ],
                "query_rounds": 3,
                "trajectory_summary": "First query was broad, second query locked onto route edges, third inspection confirmed the target page mismatch.",
                "useful_followup_focus": "route",
                "useful_followup_terms": [
                    "profile",
                    "router.pushUrl",
                    "pages/ProfileDetail",
                ],
                "misleading_followup_terms": [
                    "blank screen",
                ],
                "inspection_targets": [
                    "entry/src/main/ets/pages/Home.ets",
                    "entry/src/main/resources/base/profile_pages.json",
                ],
                "final_verification_path": "Reproduce navigation -> inspect route registration -> confirm router target mismatch.",
                "related_cases": ["case_profile_route_001"],
                "verification_method": "Confirm route registration, inspect router log, and reproduce navigation.",
                "reuse_feedback": "candidate until reused on another route issue",
                "source_cases": ["episode:profile-route-mismatch", "reflection:#3"],
                "skill_candidate": "arkts-route-blank-screen-diagnosis",
                "mistake": "The first query omitted the business page name.",
                "lesson": "ArkTS blank-screen diagnosis should combine the business page name with route terms.",
                "future_rule": "When a HarmonyOS page opens blank after navigation, query business page terms plus route/router terms first.",
                "scope": "HarmonyOS ArkTS route diagnosis",
                "evidence": "entry/src/main/ets/pages/Home.ets router.pushUrl",
                "trigger_condition": "Page opens blank after route navigation",
                "anti_pattern": "Only search generic symptom terms",
                "repair_action": "Query memory with business page name, route terms, and related log template",
                "applies_to": "ArkTS routing and page navigation failures",
                "does_not_apply_to": "Pure layout rendering bugs without navigation",
                "confidence": 0.9,
            }

            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            reflection = self.list_records(project, "reflection")[0]
            self.assertEqual(reflection["task_type"], "diagnosis")
            self.assertEqual(reflection["outcome"], "success")
            self.assertEqual(reflection["problem"], "Profile page shows a blank screen after navigation.")
            self.assertIn("route_to edge", reflection["reasoning_summary"])
            self.assertEqual(json.loads(reflection["context_used"])[0], "query: profile blank page route")
            self.assertEqual(json.loads(reflection["what_worked"])[1], "Check route edges before editing UI state.")
            self.assertEqual(json.loads(reflection["what_failed"])[0], "Searching only for blank screen was too broad.")
            self.assertIn("successful route push", json.loads(reflection["hidden_assumptions"])[0])
            self.assertIn("never navigates", json.loads(reflection["negative_preconditions"])[0])
            self.assertEqual(reflection["query_rounds"], 3)
            self.assertIn("second query locked onto route edges", reflection["trajectory_summary"])
            self.assertEqual(reflection["useful_followup_focus"], "route")
            self.assertEqual(json.loads(reflection["useful_followup_terms"])[1], "router.pushUrl")
            self.assertEqual(json.loads(reflection["misleading_followup_terms"])[0], "blank screen")
            self.assertIn("profile_pages.json", json.loads(reflection["inspection_targets"])[1])
            self.assertIn("confirm router target mismatch", reflection["final_verification_path"])
            self.assertEqual(json.loads(reflection["related_cases"])[0], "case_profile_route_001")
            self.assertIn("Confirm route registration", reflection["verification_method"])
            self.assertEqual(reflection["reuse_feedback"], "candidate until reused on another route issue")
            self.assertEqual(json.loads(reflection["source_cases"])[0], "episode:profile-route-mismatch")
            self.assertEqual(reflection["skill_candidate"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(reflection["experience_type"], "procedure_experience")

    def test_search_matches_structured_reflection_payload_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "task_type": "design",
                "outcome": "failure",
                "problem": "Image resource on product card does not appear.",
                "task": "design product card image fix",
                "lesson": "Resource display fixes need business resource names and $r lookup terms.",
                "future_rule": "When product image resources fail, query the product card business terms and app.media references.",
                "reasoning_summary": "The failed plan ignored app.media and searched only UI component names.",
                "context_used": ["query: product card image", "file: pages/ProductCard.ets"],
                "what_worked": ["Adding app.media terms found the right code file."],
                "what_failed": ["Searching only Card component was too broad."],
                "trigger_condition": "Business image or icon resource does not render",
                "repair_action": "Search by business noun plus resource/app.media/$r terms",
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(project, "search", "--query", "商品卡片图片资源不显示", "--json")
            reflections = json.loads(result.stdout)["reflections"]

            self.assertEqual(reflections[0]["task_type"], "design")
            self.assertEqual(reflections[0]["outcome"], "failure")
            self.assertEqual(reflections[0]["problem"], "Image resource on product card does not appear.")

    def test_reflect_updates_used_reflection_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "old lesson",
                "--lesson",
                "Use maintain-plan before memory mutations.",
            )

            self.run_memory(
                project,
                "reflect",
                "--task",
                "new task",
                "--lesson",
                "The old lesson helped this task.",
                "--used-reflection-ids",
                "1",
                "--reflection-outcome",
                "helped",
            )

            old_reflection = sorted(self.list_records(project, "reflection"), key=lambda row: row["id"])[0]
            self.assertEqual(old_reflection["applied_count"], 1)
            self.assertEqual(old_reflection["last_outcome"], "helped")
            self.assertIsNotNone(old_reflection["last_applied_at"])

    def test_reflect_records_reuse_feedback_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "reflect", "--task", "route lesson", "--lesson", "Route bugs need route anchors.")
            self.run_memory(project, "reflect", "--task", "log lesson", "--lesson", "Log bugs need log anchors.")

            self.run_memory(
                project,
                "reflect",
                "--task",
                "combined diagnosis",
                "--lesson",
                "The route lesson partially helped and the log lesson also mattered.",
                "--used-reflection-ids",
                "1,2",
                "--reflection-outcome",
                "partial",
            )

            events = sorted(self.list_records(project, "reflection-reuse"), key=lambda row: row["reused_reflection_id"])
            self.assertEqual([event["reused_reflection_id"] for event in events], [1, 2])
            self.assertEqual([event["applying_reflection_id"] for event in events], [3, 3])
            self.assertEqual([event["outcome"] for event in events], ["partial", "partial"])
            self.assertEqual(events[0]["task"], "combined diagnosis")

    def test_reflect_review_reports_missing_actionability(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "thin reflection",
                "--lesson",
                "Be careful.",
            )

            result = self.run_memory(project, "reflect-review", "--json")
            payload = json.loads(result.stdout)
            item = payload["reflections"][0]

            self.assertEqual(item["id"], 1)
            self.assertIn("missing_trigger_condition", item["issues"])
            self.assertIn("missing_repair_action", item["issues"])
            self.assertEqual(item["suggested_action"], "rewrite")

    def test_maintain_plan_includes_reflection_quality_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "thin reflection",
                "--lesson",
                "Be careful.",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            self.assertTrue(any(action["action"] == "rewrite_reflection" and action["id"] == 1 for action in actions))

    def test_maintain_plan_marks_misleading_reflection_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "bad lesson",
                "--lesson",
                "Use stale data first.",
            )
            self.run_memory(
                project,
                "reflect",
                "--task",
                "later task",
                "--lesson",
                "That lesson misled the task.",
                "--used-reflection-ids",
                "1",
                "--reflection-outcome",
                "misleading",
            )

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            self.assertTrue(any(action["action"] == "mark_stale" and action["id"] == 1 for action in actions))

    def test_maintain_plan_promotes_complete_experience_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "experience_type": "procedure_experience",
                "task_type": "diagnosis",
                "outcome": "success",
                "problem": "Settings page opens blank after route navigation.",
                "task": "diagnose settings route blank screen",
                "summary": "The route target was wrong.",
                "reasoning_summary": "Route and log anchors narrowed the issue.",
                "context_used": ["query: settings blank route", "log: router.pushUrl failed"],
                "what_worked": ["Search page business term with route terms."],
                "what_failed": ["Generic blank-screen search was broad."],
                "hidden_assumptions": ["The blank screen occurred after navigation."],
                "negative_preconditions": ["Does not apply to static layout visibility issues."],
                "query_rounds": 2,
                "trajectory_summary": "Route anchors became useful after the second query round.",
                "useful_followup_focus": "route",
                "useful_followup_terms": ["settings", "router.pushUrl", "pages/Settings"],
                "misleading_followup_terms": ["blank screen"],
                "inspection_targets": ["pages/Home.ets", "pages/Settings.ets"],
                "final_verification_path": "Check route registration and reproduce the navigation path.",
                "related_cases": ["case_settings_route_001"],
                "verification_method": "Check route registration, log output, and reproduce navigation.",
                "reuse_feedback": "helped",
                "source_cases": ["episode:settings-route-fix", "file: pages/Home.ets"],
                "skill_candidate": "arkts-route-blank-screen-diagnosis",
                "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                "scope": "HarmonyOS ArkTS routing",
                "evidence": "pages/Home.ets router.pushUrl",
                "trigger_condition": "Page blanks after route navigation",
                "anti_pattern": "Search generic blank-screen terms only",
                "repair_action": "Query page business terms, router target, and related log template",
                "applies_to": "ArkTS route target failures",
                "does_not_apply_to": "Non-navigation rendering bugs",
                "confidence": 0.9,
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            action = next(
                action for action in actions
                if action["action"] == "promote_experience_candidate" and action["id"] == 1
            )
            self.assertEqual(action["skill_candidate"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(action["experience_type"], "procedure_experience")
            self.assertEqual(action["useful_followup_focus"], "route")
            self.assertEqual(json.loads(action["useful_followup_terms"])[1], "router.pushUrl")
            self.assertEqual(action["query_rounds"], 2)
            self.assertIn("verification_method", action["candidate_fields"])
            self.assertIsNone(action["command"])

    def test_maintain_plan_routes_correction_experience_to_learning_governance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "experience_type": "correction_experience",
                "task_type": "workflow",
                "outcome": "success",
                "problem": "Profile page file semantics were written as a service.",
                "task": "correct profile file business meaning",
                "summary": "Re-read the file and corrected the business responsibility.",
                "reasoning_summary": "The file is a page entry, not a service layer module.",
                "context_used": ["file: pages/Profile.ets"],
                "what_worked": ["Compare route role and page build method."],
                "what_failed": ["Trusting the first broad summary."],
                "hidden_assumptions": ["The file is part of page navigation flow."],
                "negative_preconditions": ["Does not apply to plain utility modules."],
                "query_rounds": 2,
                "trajectory_summary": "The second review step compared route usage with build composition and exposed the wrong page-vs-service summary.",
                "useful_followup_focus": "route",
                "useful_followup_terms": ["Profile", "build()", "route"],
                "misleading_followup_terms": ["service"],
                "inspection_targets": ["pages/Profile.ets"],
                "final_verification_path": "Inspect build() ownership, route usage, and UI composition in the current file.",
                "related_cases": ["case_profile_semantic_fix_001"],
                "verification_method": "Check build method, route usage, and UI composition.",
                "reuse_feedback": "candidate until reused",
                "source_cases": ["file: pages/Profile.ets"],
                "lesson": "Correct learned business semantics when page files were summarized as services.",
                "future_rule": "When a file owns UI composition and route flow, classify it as page-facing business logic first.",
                "scope": "learn-business semantic correction",
                "evidence": "pages/Profile.ets build() and route usage",
                "trigger_condition": "Learned business summary conflicts with current source role.",
                "repair_action": "Rewrite the file business summary and terms from current source.",
                "applies_to": "semantic correction during learn-business review",
                "does_not_apply_to": "procedure diagnosis for runtime bugs",
                "confidence": 0.9,
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            action = next(
                action for action in actions
                if action["action"] == "review_correction_experience" and action["id"] == 1
            )
            self.assertEqual(action["experience_type"], "correction_experience")
            self.assertEqual(action["governance_path"], "learn_semantic_repair")
            self.assertEqual(action["useful_followup_focus"], "route")
            self.assertIn("build()", json.loads(action["useful_followup_terms"])[1])
            self.assertEqual(action["correction_targets"]["file_paths"], ["pages/Profile.ets"])
            self.assertIn("service", action["correction_targets"]["misleading_terms"])
            self.assertEqual(action["learning_rule_draft"]["target_memory_type"], "code_wiki_business_semantics")
            self.assertIn("Learned business summary conflicts with current source role.", action["learning_rule_draft"]["correction_trigger"])
            self.assertIn("Check build method, route usage, and UI composition.", action["learning_rule_draft"]["source_evidence"][1])
            self.assertEqual(action["command_template"], "python tools/agent_memory.py learn-business --project . --payload '<json>' --json")
            self.assertEqual(action["learn_business_payload_template"]["files"][0]["file_path"], "pages/Profile.ets")
            self.assertIn("Profile", action["learn_business_payload_template"]["files"][0]["hint_terms"][0])
            self.assertIn("Rewrite the learn-business payload for the affected records", action["workflow_steps"][2])

    def test_maintain_plan_clusters_procedure_experiences_into_skill_pattern_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Settings page opens blank after route navigation.",
                    "task": "diagnose settings route blank screen",
                    "summary": "The route target was wrong.",
                    "reasoning_summary": "Route and log anchors narrowed the issue.",
                    "context_used": ["query: settings blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Search page business term with route terms."],
                    "what_failed": ["Generic blank-screen search was broad."],
                    "hidden_assumptions": ["The blank screen occurred after navigation."],
                    "negative_preconditions": ["Does not apply to static layout visibility issues."],
                    "query_rounds": 2,
                    "trajectory_summary": "Route anchors became useful after the second query round.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["settings", "router.pushUrl", "pages/Settings"],
                    "misleading_followup_terms": ["blank screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/Settings.ets"],
                    "final_verification_path": "Check route registration and reproduce the navigation path.",
                    "related_cases": ["case_settings_route_001"],
                    "verification_method": "Check route registration, log output, and reproduce navigation.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:settings-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                    "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Search generic blank-screen terms only",
                    "repair_action": "Query page business terms, router target, and related log template",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Profile page opens blank after route navigation.",
                    "task": "diagnose profile route blank screen",
                    "summary": "The profile route registration was mismatched.",
                    "reasoning_summary": "Route anchors and router logs converged quickly.",
                    "context_used": ["query: profile blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Combine business page name and route terms."],
                    "what_failed": ["Starting from pure rendering terms."],
                    "hidden_assumptions": ["Navigation reached the target route."],
                    "negative_preconditions": ["Does not apply to local layout overflow."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the route target registration.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
                    "misleading_followup_terms": ["white screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets"],
                    "final_verification_path": "Inspect route registration and replay the same navigation path.",
                    "related_cases": ["case_profile_route_001"],
                    "verification_method": "Check route registration, logs, and navigation replay.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:profile-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "HarmonyOS route blank-screen diagnosis should start from route anchors.",
                    "future_rule": "When a page blanks after navigation, prefer route anchors before layout debugging.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Treat navigation blank screens as generic rendering bugs",
                    "repair_action": "Query page business terms, route target, and router logs first",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            action = next(action for action in actions if action["action"] == "review_skill_pattern_candidate")
            self.assertEqual(action["pattern_name"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(action["experience_type"], "procedure_experience")
            self.assertEqual(action["supporting_reflection_ids"], [1, 2])
            self.assertEqual(action["supporting_count"], 2)
            self.assertIn("route", action["common_followup_focus"])
            self.assertIn("router.pushUrl", action["common_query_terms"])
            self.assertIn("case_profile_route_001", action["supporting_cases"])
            self.assertIn("query route anchors", action["common_steps"])
            self.assertIn("inspect route target and page registration", action["common_steps"])
            self.assertIn("Check route registration and reproduce the navigation path.", action["common_stop_conditions"])
            self.assertIn("Search generic blank-screen terms only", action["failure_modes"])
            self.assertIn("verification checklist", action["expected_outputs"])
            self.assertEqual(action["draft_path"], "docs/skill-candidates/arkts-route-blank-screen-diagnosis.md")
            self.assertEqual(action["draft_status"], "not_written")
            self.assertEqual(action["draft_review_status"], "")
            self.assertEqual(action["package_path"], "skills/_candidates/arkts-route-blank-screen-diagnosis/SKILL.md")
            self.assertEqual(action["package_status"], "not_written")
            self.assertEqual(action["package_review_status"], "")
            self.assertEqual(action["promotion_checklist_path"], "skills/_candidates/arkts-route-blank-screen-diagnosis/PROMOTION.md")
            self.assertEqual(action["promotion_checklist_status"], "not_written")
            self.assertEqual(action["promotion_stage"], "clustered")
            self.assertEqual(action["promotion_readiness"], "review_candidate")
            self.assertGreaterEqual(action["quality_score"], 5)
            self.assertIn("has_minimum_supporting_reflections", action["quality_reasons"])
            self.assertEqual(action["helped_reuse_count"], 2)
            self.assertEqual(action["partial_reuse_count"], 0)
            self.assertEqual(action["misleading_reuse_count"], 0)
            self.assertEqual(action["anchor_health"], "missing")
            self.assertIn("pages/Home.ets", action["missing_anchor_paths"])
            self.assertIn("Write the draft artifact first", action["review_guidance"][0])
            self.assertIn("maintain-skill-draft", action["write_command_template"])
            self.assertIn("maintain-skill-package", action["package_command_template"])
            self.assertIn("# Skill Candidate: arkts-route-blank-screen-diagnosis", action["draft_markdown"])
            self.assertIn("## Trigger Cluster", action["draft_markdown"])
            self.assertIn("## Common Steps", action["draft_markdown"])
            self.assertIn("## Common Stop Conditions", action["draft_markdown"])
            self.assertIn("## Failure Modes", action["draft_markdown"])

    def test_maintain_skill_draft_writes_markdown_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Settings page opens blank after route navigation.",
                    "task": "diagnose settings route blank screen",
                    "summary": "The route target was wrong.",
                    "reasoning_summary": "Route and log anchors narrowed the issue.",
                    "context_used": ["query: settings blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Search page business term with route terms."],
                    "what_failed": ["Generic blank-screen search was broad."],
                    "hidden_assumptions": ["The blank screen occurred after navigation."],
                    "negative_preconditions": ["Does not apply to static layout visibility issues."],
                    "query_rounds": 2,
                    "trajectory_summary": "Route anchors became useful after the second query round.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["settings", "router.pushUrl", "pages/Settings"],
                    "misleading_followup_terms": ["blank screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/Settings.ets"],
                    "final_verification_path": "Check route registration and reproduce the navigation path.",
                    "related_cases": ["case_settings_route_001"],
                    "verification_method": "Check route registration, log output, and reproduce navigation.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:settings-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                    "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Search generic blank-screen terms only",
                    "repair_action": "Query page business terms, router target, and related log template",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Profile page opens blank after route navigation.",
                    "task": "diagnose profile route blank screen",
                    "summary": "The profile route registration was mismatched.",
                    "reasoning_summary": "Route anchors and router logs converged quickly.",
                    "context_used": ["query: profile blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Combine business page name and route terms."],
                    "what_failed": ["Starting from pure rendering terms."],
                    "hidden_assumptions": ["Navigation reached the target route."],
                    "negative_preconditions": ["Does not apply to local layout overflow."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the route target registration.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
                    "misleading_followup_terms": ["white screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets"],
                    "final_verification_path": "Inspect route registration and replay the same navigation path.",
                    "related_cases": ["case_profile_route_001"],
                    "verification_method": "Check route registration, logs, and navigation replay.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:profile-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "HarmonyOS route blank-screen diagnosis should start from route anchors.",
                    "future_rule": "When a page blanks after navigation, prefer route anchors before layout debugging.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Treat navigation blank screens as generic rendering bugs",
                    "repair_action": "Query page business terms, route target, and router logs first",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(
                project,
                "maintain-skill-draft",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            payload = json.loads(result.stdout)
            draft_path = project / "docs" / "skill-candidates" / "arkts-route-blank-screen-diagnosis.md"
            self.assertTrue(draft_path.exists())
            content = draft_path.read_text(encoding="utf-8")
            self.assertEqual(Path(payload["path"]).resolve(), draft_path.resolve())
            self.assertEqual(payload["pattern_name"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(payload["draft_status"], "written")
            self.assertEqual(payload["draft_review_status"], "pending_review")
            self.assertEqual(payload["package_status"], "not_written")
            self.assertEqual(payload["package_review_status"], "")
            self.assertEqual(payload["promotion_stage"], "draft")
            self.assertEqual(payload["write_action"], "wrote_artifact")
            self.assertEqual(payload["warning"], "")
            self.assertIn("Review the draft and record reviewer metadata", payload["review_guidance"][0])
            self.assertIn("artifact_type: \"skill_candidate_draft\"", content)
            self.assertIn("promotion_status: \"draft\"", content)
            self.assertIn("review_status: \"pending_review\"", content)
            self.assertIn("reviewer: \"\"", content)
            self.assertIn("review_notes: []", content)
            self.assertIn("supporting_reflection_ids: [1, 2]", content)
            self.assertIn("common_followup_focus: [\"route\"]", content)
            self.assertIn("- Review status: pending_review", content)
            self.assertIn("## Common Steps", content)
            self.assertIn("query route anchors", content)
            self.assertIn("## Failure Modes", content)

    def test_maintain_skill_draft_all_writes_all_candidate_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Settings page opens blank after route navigation.",
                    "task": "diagnose settings route blank screen",
                    "summary": "The route target was wrong.",
                    "reasoning_summary": "Route and log anchors narrowed the issue.",
                    "context_used": ["query: settings blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Search page business term with route terms."],
                    "what_failed": ["Generic blank-screen search was broad."],
                    "hidden_assumptions": ["The blank screen occurred after navigation."],
                    "negative_preconditions": ["Does not apply to static layout visibility issues."],
                    "query_rounds": 2,
                    "trajectory_summary": "Route anchors became useful after the second query round.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["settings", "router.pushUrl", "pages/Settings"],
                    "misleading_followup_terms": ["blank screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/Settings.ets"],
                    "final_verification_path": "Check route registration and reproduce the navigation path.",
                    "related_cases": ["case_settings_route_001"],
                    "verification_method": "Check route registration, log output, and reproduce navigation.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:settings-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                    "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Search generic blank-screen terms only",
                    "repair_action": "Query page business terms, router target, and related log template",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "design",
                    "outcome": "success",
                    "problem": "Product image resource does not render.",
                    "task": "diagnose product image resource failure",
                    "summary": "The resource key was mismatched.",
                    "reasoning_summary": "Resource anchors and app.media lookups narrowed the issue.",
                    "context_used": ["query: product image resource", "file: ProductCard.ets"],
                    "what_worked": ["Search business image term with app.media anchors."],
                    "what_failed": ["Searching only card component names."],
                    "hidden_assumptions": ["The resource exists in the current module bundle."],
                    "negative_preconditions": ["Does not apply to network image loading."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the wrong resource key.",
                    "useful_followup_focus": "resource",
                    "useful_followup_terms": ["product image", "app.media", "$r"],
                    "misleading_followup_terms": ["card"],
                    "inspection_targets": ["pages/ProductCard.ets", "resources/base/media"],
                    "final_verification_path": "Inspect resource key usage and compare with declared media entries.",
                    "related_cases": ["case_product_resource_001"],
                    "verification_method": "Check resource declarations and lookup sites.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:product-resource-fix"],
                    "skill_candidate": "arkts-resource-missing-diagnosis",
                    "lesson": "Resource failures should start from business noun plus app.media anchors.",
                    "future_rule": "When a business image fails, query the resource anchors before UI component names.",
                    "scope": "HarmonyOS ArkTS resource lookup",
                    "evidence": "ProductCard.ets app.media reference",
                    "trigger_condition": "Business image or icon resource does not render",
                    "anti_pattern": "Search only component names",
                    "repair_action": "Query business resource terms and compare with resource keys",
                    "applies_to": "ArkTS resource lookup failures",
                    "does_not_apply_to": "Remote image network failures",
                    "confidence": 0.9,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "design",
                    "outcome": "success",
                    "problem": "Product icon resource does not render.",
                    "task": "diagnose product icon resource failure",
                    "summary": "The icon resource key was mismatched.",
                    "reasoning_summary": "Resource anchors and app.media lookups converged on the wrong key.",
                    "context_used": ["query: product icon resource", "file: ProductCard.ets"],
                    "what_worked": ["Search business icon term with app.media anchors."],
                    "what_failed": ["Starting from component names only."],
                    "hidden_assumptions": ["The icon resource is bundled locally."],
                    "negative_preconditions": ["Does not apply to remote CDN icon failures."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the wrong icon resource key.",
                    "useful_followup_focus": "resource",
                    "useful_followup_terms": ["product icon", "app.media", "$r"],
                    "misleading_followup_terms": ["card"],
                    "inspection_targets": ["pages/ProductCard.ets", "resources/base/media"],
                    "final_verification_path": "Inspect icon resource key usage and compare with declared media entries.",
                    "related_cases": ["case_product_resource_002"],
                    "verification_method": "Check resource declarations and icon lookup sites.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:product-icon-resource-fix"],
                    "skill_candidate": "arkts-resource-missing-diagnosis",
                    "lesson": "Resource failures should start from business noun plus app.media anchors.",
                    "future_rule": "When a business icon fails, query the resource anchors before UI component names.",
                    "scope": "HarmonyOS ArkTS resource lookup",
                    "evidence": "ProductCard.ets app.media reference",
                    "trigger_condition": "Business icon resource does not render",
                    "anti_pattern": "Search only component names",
                    "repair_action": "Query business resource terms and compare with resource keys",
                    "applies_to": "ArkTS resource lookup failures",
                    "does_not_apply_to": "Remote image network failures",
                    "confidence": 0.9,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Profile page opens blank after route navigation.",
                    "task": "diagnose profile route blank screen",
                    "summary": "The profile route registration was mismatched.",
                    "reasoning_summary": "Route anchors and router logs converged quickly.",
                    "context_used": ["query: profile blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Combine business page name and route terms."],
                    "what_failed": ["Starting from pure rendering terms."],
                    "hidden_assumptions": ["Navigation reached the target route."],
                    "negative_preconditions": ["Does not apply to local layout overflow."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the route target registration.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
                    "misleading_followup_terms": ["white screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets"],
                    "final_verification_path": "Inspect route registration and replay the same navigation path.",
                    "related_cases": ["case_profile_route_001"],
                    "verification_method": "Check route registration, logs, and navigation replay.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:profile-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "HarmonyOS route blank-screen diagnosis should start from route anchors.",
                    "future_rule": "When a page blanks after navigation, prefer route anchors before layout debugging.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Treat navigation blank screens as generic rendering bugs",
                    "repair_action": "Query page business terms, route target, and router logs first",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(
                project,
                "maintain-skill-draft",
                "--pattern-name",
                "all",
                "--json",
            )

            payload = json.loads(result.stdout)
            route_draft = project / "docs" / "skill-candidates" / "arkts-route-blank-screen-diagnosis.md"
            resource_draft = project / "docs" / "skill-candidates" / "arkts-resource-missing-diagnosis.md"
            self.assertTrue(route_draft.exists())
            self.assertTrue(resource_draft.exists())
            self.assertEqual(payload["written_count"], 2)
            self.assertEqual(payload["pattern_names"], [
                "arkts-resource-missing-diagnosis",
                "arkts-route-blank-screen-diagnosis",
            ])
            self.assertEqual(payload["written"][0]["draft_status"], "written")
            self.assertEqual(payload["written"][0]["draft_review_status"], "pending_review")
            self.assertEqual(payload["written"][0]["promotion_stage"], "draft")
            self.assertEqual(payload["written"][0]["write_action"], "wrote_artifact")

    def test_maintain_skill_package_writes_candidate_skill_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Settings page opens blank after route navigation.",
                    "task": "diagnose settings route blank screen",
                    "summary": "The route target was wrong.",
                    "reasoning_summary": "Route and log anchors narrowed the issue.",
                    "context_used": ["query: settings blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Search page business term with route terms."],
                    "what_failed": ["Generic blank-screen search was broad."],
                    "hidden_assumptions": ["The blank screen occurred after navigation."],
                    "negative_preconditions": ["Does not apply to static layout visibility issues."],
                    "query_rounds": 2,
                    "trajectory_summary": "Route anchors became useful after the second query round.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["settings", "router.pushUrl", "pages/Settings"],
                    "misleading_followup_terms": ["blank screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/Settings.ets"],
                    "final_verification_path": "Check route registration and reproduce the navigation path.",
                    "related_cases": ["case_settings_route_001"],
                    "verification_method": "Check route registration, log output, and reproduce navigation.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:settings-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                    "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Search generic blank-screen terms only",
                    "repair_action": "Query page business terms, router target, and related log template",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Profile page opens blank after route navigation.",
                    "task": "diagnose profile route blank screen",
                    "summary": "The profile route registration was mismatched.",
                    "reasoning_summary": "Route anchors and router logs converged quickly.",
                    "context_used": ["query: profile blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Combine business page name and route terms."],
                    "what_failed": ["Starting from pure rendering terms."],
                    "hidden_assumptions": ["Navigation reached the target route."],
                    "negative_preconditions": ["Does not apply to local layout overflow."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the route target registration.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
                    "misleading_followup_terms": ["white screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets"],
                    "final_verification_path": "Inspect route registration and replay the same navigation path.",
                    "related_cases": ["case_profile_route_001"],
                    "verification_method": "Check route registration, logs, and navigation replay.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:profile-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "HarmonyOS route blank-screen diagnosis should start from route anchors.",
                    "future_rule": "When a page blanks after navigation, prefer route anchors before layout debugging.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Treat navigation blank screens as generic rendering bugs",
                    "repair_action": "Query page business terms, route target, and router logs first",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            result = self.run_memory(
                project,
                "maintain-skill-package",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            payload = json.loads(result.stdout)
            package_path = project / "skills" / "_candidates" / "arkts-route-blank-screen-diagnosis" / "SKILL.md"
            checklist_path = project / "skills" / "_candidates" / "arkts-route-blank-screen-diagnosis" / "PROMOTION.md"
            self.assertTrue(package_path.exists())
            self.assertTrue(checklist_path.exists())
            content = package_path.read_text(encoding="utf-8")
            checklist = checklist_path.read_text(encoding="utf-8")
            self.assertEqual(Path(payload["path"]).resolve(), package_path.resolve())
            self.assertEqual(payload["pattern_name"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(payload["draft_status"], "not_written")
            self.assertEqual(payload["draft_review_status"], "")
            self.assertEqual(payload["package_status"], "written")
            self.assertEqual(payload["package_review_status"], "pending_review")
            self.assertEqual(payload["promotion_checklist_status"], "written")
            self.assertEqual(payload["promotion_stage"], "candidate_package")
            self.assertEqual(payload["promotion_readiness"], "review_candidate")
            self.assertEqual(payload["write_action"], "wrote_artifact")
            self.assertEqual(payload["warning"], "")
            self.assertIn("Review the candidate package metadata", payload["review_guidance"][0])
            self.assertIn("artifact_type: \"skill_candidate_package\"", content)
            self.assertIn("promotion_status: \"candidate\"", content)
            self.assertIn("review_status: \"pending_review\"", content)
            self.assertIn("review_notes: []", content)
            self.assertIn("source_draft: \"docs/skill-candidates/arkts-route-blank-screen-diagnosis.md\"", content)
            self.assertIn("Candidate package generated from repeated procedure_experience reflections.", content)
            self.assertIn("## Common Steps", content)
            self.assertIn("## Quality Signals", content)
            self.assertIn("Readiness: `review_candidate`", content)
            self.assertIn("Anchor health:", content)
            self.assertIn("# Promotion Checklist: arkts-route-blank-screen-diagnosis", checklist)
            self.assertIn("Formal target: `skills/arkts-route-blank-screen-diagnosis/SKILL.md`", checklist)
            self.assertIn("Promotion readiness is acceptable (`review_candidate`)", checklist)

    def test_maintain_skill_draft_preserves_existing_reviewed_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Settings page opens blank after route navigation.",
                    "task": "diagnose settings route blank screen",
                    "summary": "The route target was wrong.",
                    "reasoning_summary": "Route and log anchors narrowed the issue.",
                    "context_used": ["query: settings blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Search page business term with route terms."],
                    "what_failed": ["Generic blank-screen search was broad."],
                    "hidden_assumptions": ["The blank screen occurred after navigation."],
                    "negative_preconditions": ["Does not apply to static layout visibility issues."],
                    "query_rounds": 2,
                    "trajectory_summary": "Route anchors became useful after the second query round.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["settings", "router.pushUrl", "pages/Settings"],
                    "misleading_followup_terms": ["blank screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/Settings.ets"],
                    "final_verification_path": "Check route registration and reproduce the navigation path.",
                    "related_cases": ["case_settings_route_001"],
                    "verification_method": "Check route registration, log output, and reproduce navigation.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:settings-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                    "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Search generic blank-screen terms only",
                    "repair_action": "Query page business terms, router target, and related log template",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Profile page opens blank after route navigation.",
                    "task": "diagnose profile route blank screen",
                    "summary": "The profile route registration was mismatched.",
                    "reasoning_summary": "Route anchors and router logs converged quickly.",
                    "context_used": ["query: profile blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Combine business page name and route terms."],
                    "what_failed": ["Starting from pure rendering terms."],
                    "hidden_assumptions": ["Navigation reached the target route."],
                    "negative_preconditions": ["Does not apply to local layout overflow."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the route target registration.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
                    "misleading_followup_terms": ["white screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets"],
                    "final_verification_path": "Inspect route registration and replay the same navigation path.",
                    "related_cases": ["case_profile_route_001"],
                    "verification_method": "Check route registration, logs, and navigation replay.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:profile-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "HarmonyOS route blank-screen diagnosis should start from route anchors.",
                    "future_rule": "When a page blanks after navigation, prefer route anchors before layout debugging.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Treat navigation blank screens as generic rendering bugs",
                    "repair_action": "Query page business terms, route target, and router logs first",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            self.run_memory(
                project,
                "maintain-skill-draft",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            draft_path = project / "docs" / "skill-candidates" / "arkts-route-blank-screen-diagnosis.md"
            draft_path.write_text(
                draft_path.read_text(encoding="utf-8")
                .replace('review_status: "pending_review"', 'review_status: "approved"')
                .replace('reviewer: ""', 'reviewer: "Alice"'),
                encoding="utf-8",
            )
            preserved_content = draft_path.read_text(encoding="utf-8")

            result = self.run_memory(
                project,
                "maintain-skill-draft",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["write_action"], "preserved_existing_reviewed_artifact")
            self.assertIn("did not overwrite", payload["warning"])
            self.assertEqual(payload["existing_review_status"], "approved")
            self.assertEqual(payload["existing_reviewer"], "Alice")
            self.assertEqual(payload["draft_review_status"], "approved")
            self.assertEqual(payload["draft_reviewer"], "Alice")
            self.assertEqual(draft_path.read_text(encoding="utf-8"), preserved_content)

    def test_maintain_skill_promotion_status_reports_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Settings page opens blank after route navigation.",
                    "task": "diagnose settings route blank screen",
                    "summary": "The route target was wrong.",
                    "reasoning_summary": "Route and log anchors narrowed the issue.",
                    "context_used": ["query: settings blank route"],
                    "what_worked": ["Search page business term with route terms."],
                    "what_failed": ["Generic blank-screen search was broad."],
                    "hidden_assumptions": ["The blank screen occurred after navigation."],
                    "negative_preconditions": ["Does not apply to static layout visibility issues."],
                    "query_rounds": 2,
                    "trajectory_summary": "Route anchors became useful after the second query round.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["settings", "router.pushUrl", "pages/Settings"],
                    "misleading_followup_terms": ["blank screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/Settings.ets"],
                    "final_verification_path": "Check route registration and reproduce the navigation path.",
                    "related_cases": ["case_settings_route_001"],
                    "verification_method": "Check route registration, log output, and reproduce navigation.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:settings-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                    "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Search generic blank-screen terms only",
                    "repair_action": "Query page business terms, router target, and related log template",
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Profile page opens blank after route navigation.",
                    "task": "diagnose profile route blank screen",
                    "summary": "The profile route registration was mismatched.",
                    "reasoning_summary": "Route anchors and router logs converged quickly.",
                    "context_used": ["query: profile blank route"],
                    "what_worked": ["Combine business page name and route terms."],
                    "what_failed": ["Starting from pure rendering terms."],
                    "hidden_assumptions": ["Navigation reached the target route."],
                    "negative_preconditions": ["Does not apply to local layout overflow."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the route target registration.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
                    "misleading_followup_terms": ["white screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets"],
                    "final_verification_path": "Inspect route registration and replay the same navigation path.",
                    "related_cases": ["case_profile_route_001"],
                    "verification_method": "Check route registration, logs, and navigation replay.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:profile-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "HarmonyOS route blank-screen diagnosis should start from route anchors.",
                    "future_rule": "When a page blanks after navigation, prefer route anchors before layout debugging.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Treat navigation blank screens as generic rendering bugs",
                    "repair_action": "Query page business terms, route target, and router logs first",
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))
            self.run_memory(
                project,
                "maintain-skill-package",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            result = self.run_memory(
                project,
                "maintain-skill-promotion-status",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )
            payload = json.loads(result.stdout)

            self.assertEqual(payload["pattern_name"], "arkts-route-blank-screen-diagnosis")
            self.assertEqual(payload["formal_target"], "skills/arkts-route-blank-screen-diagnosis/SKILL.md")
            self.assertIn("package_review_not_completed", payload["promotion_blockers"])
            self.assertIn("promotion_readiness_not_high_enough", payload["promotion_blockers"])
            self.assertFalse(payload["ready_for_manual_promotion"])

    def test_maintain_skill_package_preserves_existing_reviewed_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Settings page opens blank after route navigation.",
                    "task": "diagnose settings route blank screen",
                    "summary": "The route target was wrong.",
                    "reasoning_summary": "Route and log anchors narrowed the issue.",
                    "context_used": ["query: settings blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Search page business term with route terms."],
                    "what_failed": ["Generic blank-screen search was broad."],
                    "hidden_assumptions": ["The blank screen occurred after navigation."],
                    "negative_preconditions": ["Does not apply to static layout visibility issues."],
                    "query_rounds": 2,
                    "trajectory_summary": "Route anchors became useful after the second query round.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["settings", "router.pushUrl", "pages/Settings"],
                    "misleading_followup_terms": ["blank screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/Settings.ets"],
                    "final_verification_path": "Check route registration and reproduce the navigation path.",
                    "related_cases": ["case_settings_route_001"],
                    "verification_method": "Check route registration, log output, and reproduce navigation.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:settings-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                    "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Search generic blank-screen terms only",
                    "repair_action": "Query page business terms, router target, and related log template",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Profile page opens blank after route navigation.",
                    "task": "diagnose profile route blank screen",
                    "summary": "The profile route registration was mismatched.",
                    "reasoning_summary": "Route anchors and router logs converged quickly.",
                    "context_used": ["query: profile blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Combine business page name and route terms."],
                    "what_failed": ["Starting from pure rendering terms."],
                    "hidden_assumptions": ["Navigation reached the target route."],
                    "negative_preconditions": ["Does not apply to local layout overflow."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the route target registration.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
                    "misleading_followup_terms": ["white screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets"],
                    "final_verification_path": "Inspect route registration and replay the same navigation path.",
                    "related_cases": ["case_profile_route_001"],
                    "verification_method": "Check route registration, logs, and navigation replay.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:profile-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "HarmonyOS route blank-screen diagnosis should start from route anchors.",
                    "future_rule": "When a page blanks after navigation, prefer route anchors before layout debugging.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Treat navigation blank screens as generic rendering bugs",
                    "repair_action": "Query page business terms, route target, and router logs first",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            self.run_memory(
                project,
                "maintain-skill-package",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            package_path = project / "skills" / "_candidates" / "arkts-route-blank-screen-diagnosis" / "SKILL.md"
            package_path.write_text(
                package_path.read_text(encoding="utf-8")
                .replace('review_status: "pending_review"', 'review_status: "approved"')
                .replace('reviewer: ""', 'reviewer: "Bob"'),
                encoding="utf-8",
            )
            preserved_content = package_path.read_text(encoding="utf-8")

            result = self.run_memory(
                project,
                "maintain-skill-package",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["write_action"], "preserved_existing_reviewed_artifact")
            self.assertIn("did not overwrite", payload["warning"])
            self.assertEqual(payload["existing_review_status"], "approved")
            self.assertEqual(payload["existing_reviewer"], "Bob")
            self.assertEqual(payload["package_review_status"], "approved")
            self.assertEqual(payload["package_reviewer"], "Bob")
            self.assertEqual(package_path.read_text(encoding="utf-8"), preserved_content)

    def test_maintain_promote_reflection_to_semantic_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "durable workflow",
                "--lesson",
                "Runtime changes need parser tests and skill docs.",
            )

            result = self.run_memory(
                project,
                "maintain-promote",
                "--reflection-id",
                "1",
                "--fact",
                "Runtime changes must update parser tests and skill docs.",
                "--json",
            )

            payload = json.loads(result.stdout)
            facts = self.list_records(project, "semantic")
            reflection = self.list_records(project, "reflection")[0]
            self.assertEqual(payload["semantic_fact_id"], 1)
            self.assertEqual(facts[0]["source"], "reflection:1")
            self.assertIsNotNone(reflection["reviewed_at"])

    def test_vault_export_writes_reflection_quality_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "reflect",
                "--task",
                "thin reflection",
                "--lesson",
                "Be careful.",
            )

            self.run_memory(project, "vault-export")

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Reflection Quality.md"
            self.assertTrue(dashboard.exists())
            self.assertIn("missing_trigger_condition", dashboard.read_text(encoding="utf-8"))

    def test_vault_export_writes_experience_candidates_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "task_type": "diagnosis",
                "outcome": "success",
                "problem": "Settings page opens blank after route navigation.",
                "task": "diagnose settings route blank screen",
                "summary": "The route target was wrong.",
                "reasoning_summary": "Route and log anchors narrowed the issue.",
                "context_used": ["query: settings blank route", "log: router.pushUrl failed"],
                "what_worked": ["Search page business term with route terms."],
                "what_failed": ["Generic blank-screen search was broad."],
                "hidden_assumptions": ["The blank screen occurred after navigation."],
                "negative_preconditions": ["Does not apply to static layout visibility issues."],
                "verification_method": "Check route registration, log output, and reproduce navigation.",
                "reuse_feedback": "helped",
                "source_cases": ["episode:settings-route-fix", "file: pages/Home.ets"],
                "skill_candidate": "arkts-route-blank-screen-diagnosis",
                "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                "scope": "HarmonyOS ArkTS routing",
                "evidence": "pages/Home.ets router.pushUrl",
                "trigger_condition": "Page blanks after route navigation",
                "anti_pattern": "Search generic blank-screen terms only",
                "repair_action": "Query page business terms, router target, and related log template",
                "applies_to": "ArkTS route target failures",
                "does_not_apply_to": "Non-navigation rendering bugs",
                "confidence": 0.9,
            }
            self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            self.run_memory(project, "vault-export")

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Experience Candidates.md"
            index = self.project_memory_dir(project) / "vault" / "index.md"
            self.assertTrue(dashboard.exists())
            content = dashboard.read_text(encoding="utf-8")
            self.assertIn("arkts-route-blank-screen-diagnosis", content)
            self.assertIn("Check route registration", content)
            self.assertIn("episode:settings-route-fix", content)
            self.assertIn("[[Governance/Experience Candidates]]", index.read_text(encoding="utf-8"))

    def test_vault_export_writes_reflection_reuse_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "reflect", "--task", "old diagnosis", "--lesson", "Route bugs need route anchors.")
            self.run_memory(
                project,
                "reflect",
                "--task",
                "new diagnosis",
                "--lesson",
                "The old diagnosis partially helped.",
                "--used-reflection-ids",
                "1",
                "--reflection-outcome",
                "partial",
            )

            self.run_memory(project, "vault-export")

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Reflection Reuse.md"
            index = self.project_memory_dir(project) / "vault" / "index.md"
            self.assertTrue(dashboard.exists())
            content = dashboard.read_text(encoding="utf-8")
            self.assertIn("reused reflection #1", content)
            self.assertIn("applying reflection #2", content)
            self.assertIn("partial", content)
            self.assertIn("[[Governance/Reflection Reuse]]", index.read_text(encoding="utf-8"))

    def test_vault_export_writes_skill_pattern_candidates_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payloads = [
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Settings page opens blank after route navigation.",
                    "task": "diagnose settings route blank screen",
                    "summary": "The route target was wrong.",
                    "reasoning_summary": "Route and log anchors narrowed the issue.",
                    "context_used": ["query: settings blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Search page business term with route terms."],
                    "what_failed": ["Generic blank-screen search was broad."],
                    "hidden_assumptions": ["The blank screen occurred after navigation."],
                    "negative_preconditions": ["Does not apply to static layout visibility issues."],
                    "query_rounds": 2,
                    "trajectory_summary": "Route anchors became useful after the second query round.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["settings", "router.pushUrl", "pages/Settings"],
                    "misleading_followup_terms": ["blank screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/Settings.ets"],
                    "final_verification_path": "Check route registration and reproduce the navigation path.",
                    "related_cases": ["case_settings_route_001"],
                    "verification_method": "Check route registration, log output, and reproduce navigation.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:settings-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "ArkTS route blank-screen diagnosis should query business page terms with route terms.",
                    "future_rule": "When a page blanks after navigation, query page business name plus router terms.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Search generic blank-screen terms only",
                    "repair_action": "Query page business terms, router target, and related log template",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
                {
                    "experience_type": "procedure_experience",
                    "task_type": "diagnosis",
                    "outcome": "success",
                    "problem": "Profile page opens blank after route navigation.",
                    "task": "diagnose profile route blank screen",
                    "summary": "The profile route registration was mismatched.",
                    "reasoning_summary": "Route anchors and router logs converged quickly.",
                    "context_used": ["query: profile blank route", "log: router.pushUrl failed"],
                    "what_worked": ["Combine business page name and route terms."],
                    "what_failed": ["Starting from pure rendering terms."],
                    "hidden_assumptions": ["Navigation reached the target route."],
                    "negative_preconditions": ["Does not apply to local layout overflow."],
                    "query_rounds": 2,
                    "trajectory_summary": "The second query round narrowed the issue to the route target registration.",
                    "useful_followup_focus": "route",
                    "useful_followup_terms": ["profile", "router.pushUrl", "pages/ProfileDetail"],
                    "misleading_followup_terms": ["white screen"],
                    "inspection_targets": ["pages/Home.ets", "pages/ProfileDetail.ets"],
                    "final_verification_path": "Inspect route registration and replay the same navigation path.",
                    "related_cases": ["case_profile_route_001"],
                    "verification_method": "Check route registration, logs, and navigation replay.",
                    "reuse_feedback": "helped",
                    "source_cases": ["episode:profile-route-fix"],
                    "skill_candidate": "arkts-route-blank-screen-diagnosis",
                    "lesson": "HarmonyOS route blank-screen diagnosis should start from route anchors.",
                    "future_rule": "When a page blanks after navigation, prefer route anchors before layout debugging.",
                    "scope": "HarmonyOS ArkTS routing",
                    "evidence": "pages/Home.ets router.pushUrl",
                    "trigger_condition": "Page blanks after route navigation",
                    "anti_pattern": "Treat navigation blank screens as generic rendering bugs",
                    "repair_action": "Query page business terms, route target, and router logs first",
                    "applies_to": "ArkTS route target failures",
                    "does_not_apply_to": "Non-navigation rendering bugs",
                    "confidence": 0.9,
                },
            ]
            for payload in payloads:
                self.run_memory(project, "reflect", "--payload", json.dumps(payload, ensure_ascii=False))

            self.run_memory(
                project,
                "maintain-skill-package",
                "--pattern-name",
                "arkts-route-blank-screen-diagnosis",
                "--json",
            )
            package_path = project / "skills" / "_candidates" / "arkts-route-blank-screen-diagnosis" / "SKILL.md"
            package_path.write_text(
                package_path.read_text(encoding="utf-8")
                .replace('review_status: "pending_review"', 'review_status: "approved"')
                .replace('reviewer: ""', 'reviewer: "Bob"'),
                encoding="utf-8",
            )

            self.run_memory(project, "vault-export")

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Skill Pattern Candidates.md"
            index = self.project_memory_dir(project) / "vault" / "index.md"
            self.assertTrue(dashboard.exists())
            content = dashboard.read_text(encoding="utf-8")
            self.assertIn("Reviewed draft or candidate-package artifacts are preserved by the runtime", content)
            self.assertIn("arkts-route-blank-screen-diagnosis", content)
            self.assertIn("Promotion stage: `candidate_package`", content)
            self.assertIn("Draft status: `not_written`", content)
            self.assertIn("Package status: `written`", content)
            self.assertIn("Package review status: `approved`", content)
            self.assertIn("Package reviewer: `Bob`", content)
            self.assertIn("Promotion checklist status: `written`", content)
            self.assertIn("Promotion checklist path: `skills/_candidates/arkts-route-blank-screen-diagnosis/PROMOTION.md`", content)
            self.assertIn("Promotion readiness: `review_candidate`", content)
            self.assertIn("Quality score: `", content)
            self.assertIn("Anchor health: `", content)
            self.assertIn("Review guidance:", content)
            self.assertIn("Review the candidate package metadata", content)
            self.assertIn("docs/skill-candidates/arkts-route-blank-screen-diagnosis.md", content)
            self.assertIn("router.pushUrl", content)
            self.assertIn("supporting reflections", content.lower())
            self.assertIn("[[Governance/Skill Pattern Candidates]]", index.read_text(encoding="utf-8"))

    def test_vault_export_writes_learned_scopes_and_refresh_drift_dashboards(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            pages = project / "pages"
            pages.mkdir()
            (pages / "A.ets").write_text("@Component\nstruct A { build() {} }\n", encoding="utf-8")
            self.run_memory(project, "learn-path", "--path", "pages", "--json")
            (pages / "A.ets").write_text("@Component\nstruct A { build() { console.error('updated'); } }\n", encoding="utf-8")
            self.run_memory(project, "maintain-refresh-scope", "--json")
            self.run_memory(project, "vault-export")

            vault_dir = self.project_memory_dir(project) / "vault"
            scopes = (vault_dir / "Governance" / "Learned Scopes.md").read_text(encoding="utf-8")
            drift = (vault_dir / "Governance" / "Refresh Drift.md").read_text(encoding="utf-8")
            index = (vault_dir / "index.md").read_text(encoding="utf-8")
            self.assertIn("Scope #1 (path)", scopes)
            self.assertIn("Health: `drift`", scopes)
            self.assertIn("Changed files: 1", drift)
            self.assertIn("[[Governance/Learned Scopes]]", index)
            self.assertIn("[[Governance/Refresh Drift]]", index)

    def test_vault_export_truncates_large_record_sets_for_scale(self) -> None:
        from tools.agent_memory_runtime.storage import connect, ensure_initialized, now_iso, resolve_project

        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            runtime_project = resolve_project(str(project), str(self.memory_home(project)))
            ensure_initialized(runtime_project)
            with connect(runtime_project) as conn:
                for index in range(520):
                    ts = now_iso()
                    conn.execute(
                        """
                        INSERT INTO episodes(
                          project_id, task, summary, outcome, files_touched, commands_run,
                          importance, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            runtime_project.project_id,
                            f"episode {index}",
                            f"summary {index}",
                            None,
                            None,
                            None,
                            0.5,
                            ts,
                        ),
                    )
                for index in range(1050):
                    ts = now_iso()
                    conn.execute(
                        """
                        INSERT INTO semantic_facts(
                          project_id, fact, source, confidence, category, scope, evidence,
                          created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            runtime_project.project_id,
                            f"fact {index}",
                            "test",
                            0.8,
                            None,
                            None,
                            None,
                            ts,
                            ts,
                        ),
                    )
                conn.commit()

            self.run_memory(project, "vault-export")

            vault_dir = self.project_memory_dir(project) / "vault"
            episodes_dir = vault_dir / "Episodes"
            facts_page = (vault_dir / "Semantic Facts" / "project-facts.md").read_text(encoding="utf-8")

            self.assertEqual(500, len(list(episodes_dir.glob("*.md"))))
            self.assertIn("Truncated vault export: showing 1000 of 1050 records", facts_page)

    def test_context_records_query_miss_when_all_result_sets_are_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(project, "context", "--query", "no-such-memory-token", "--json")

            misses = self.miss_list(project)
            self.assertEqual(len(misses), 1)
            self.assertEqual(misses[0]["query"], "no-such-memory-token")
            self.assertEqual(misses[0]["source"], "context")
            self.assertEqual(misses[0]["status"], "open")
            self.assertEqual(json.loads(misses[0]["result_counts"])["semantic_facts"], 0)

    def test_repeated_query_miss_updates_existing_open_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(project, "context", "--query", "No Such Memory Token", "--json")
            self.run_memory(project, "context", "--query", "  no   such memory token  ", "--json")

            misses = self.miss_list(project)
            self.assertEqual(len(misses), 1)
            self.assertEqual(misses[0]["query"], "No Such Memory Token")
            self.assertEqual(misses[0]["normalized_query"], "no such memory token")
            self.assertEqual(misses[0]["miss_count"], 2)
            self.assertIsNotNone(misses[0]["last_seen_at"])

    def test_context_does_not_record_query_miss_when_memory_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "SQLite remains the source of truth.",
                "--source",
                "test",
            )

            self.run_memory(project, "context", "--query", "SQLite", "--json")

            self.assertEqual(self.miss_list(project), [])

    def test_wiki_search_records_query_miss_when_no_wiki_match_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            self.run_memory(project, "wiki-search", "--query", "missing-wiki-token", "--json")

            misses = self.miss_list(project)
            self.assertEqual(len(misses), 1)
            self.assertEqual(misses[0]["source"], "wiki-search")

    def test_miss_status_updates_query_miss_review_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "context", "--query", "unanswered-question", "--json")

            self.run_memory(
                project,
                "miss-status",
                "--id",
                "1",
                "--status",
                "resolved",
                "--resolution",
                "added semantic fact",
            )

            miss = self.miss_list(project)[0]
            self.assertEqual(miss["status"], "resolved")
            self.assertEqual(miss["resolution"], "added semantic fact")
            self.assertIsNotNone(miss["reviewed_at"])

    def test_maintain_plan_includes_open_query_miss_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "symbols": [{"symbol": "profileCache", "symbol_type": "field"}],
                        "logs": [{"message_template": "load profile start", "level": "info"}],
                    }
                ]
            }
            self.run_memory(project, "learn-business", "--payload", json.dumps(payload, ensure_ascii=False), "--json")
            self.run_memory(project, "context", "--query", "unanswered-question", "--json")

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            action = next(action for action in actions if action["action"] == "review_query_miss" and action["id"] == 1)
            self.assertEqual(action["miss_count"], 1)
            self.assertEqual(
                action["suggested_fixes"],
                ["learn_missing_scope", "add_business_terms", "rewrite_reflection", "ignore_noise"],
            )
            self.assertIn("unanswered", action["suggested_query_terms"])
            self.assertIn("pages/profiledetail.ets", action["suggested_query_terms"])
            self.assertIn("profilecache", action["suggested_query_terms"])
            self.assertEqual(
                action["query_command_template"],
                "python tools/agent_memory.py search --project . --query '<query>' --json",
            )
            self.assertEqual(
                action["query_workflow_steps"],
                [
                    "Start from suggested_query_terms and keep the original user problem wording.",
                    "Prefer exact route, resource, log, file, and symbol anchors before generic keywords.",
                    "Run query or search again with the strongest 2-6 followup terms.",
                    "If retrieval is still weak, enrich the listed code records with learn-business before querying again.",
                ],
            )
            self.assertIn("pages/ProfileDetail.ets", action["semantic_gap_targets"]["files_missing_business_terms"])
            self.assertIn(
                "pages/ProfileDetail.ets::profileCache",
                action["semantic_gap_targets"]["symbols_missing_business_terms"],
            )
            self.assertIn(
                "pages/ProfileDetail.ets::load profile start",
                action["semantic_gap_targets"]["logs_missing_business_summary"],
            )

    def test_maintain_plan_adds_business_term_enrichment_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "symbols": [{"symbol": "profileCache", "symbol_type": "field"}],
                        "logs": [
                            {
                                "message_template": "load profile start",
                                "function": "loadUserProfile",
                                "level": "info",
                                "logger": "hilog",
                            }
                        ],
                    }
                ]
            }

            self.run_memory(project, "learn-business", "--payload", json.dumps(payload, ensure_ascii=False), "--json")

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]

            action = next(action for action in actions if action["action"] == "add_business_terms")
            self.assertEqual(action["type"], "code_memory")
            self.assertFalse(action["requires_confirmation"])
            self.assertIn("pages/ProfileDetail.ets", action["semantic_gap_targets"]["files_missing_business_summary"])
            self.assertIn(
                "pages/ProfileDetail.ets::profileCache",
                action["semantic_gap_targets"]["symbols_missing_business_terms"],
            )
            self.assertEqual(
                action["command_template"],
                "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
            )
            payload_template = action["learn_business_payload_template"]
            self.assertEqual(payload_template["files"][0]["file_path"], "pages/ProfileDetail.ets")
            self.assertEqual(payload_template["files"][0]["business_summary"], "")
            self.assertEqual(payload_template["files"][0]["business_terms"], [])
            self.assertIn("pages/ProfileDetail.ets", payload_template["files"][0]["hint_context"])
            self.assertIn("profiledetail", payload_template["files"][0]["hint_terms"])
            self.assertEqual(payload_template["files"][0]["symbols"][0]["symbol"], "profileCache")
            self.assertEqual(payload_template["files"][0]["symbols"][0]["symbol_type"], "field")
            self.assertIn("profilecache", payload_template["files"][0]["symbols"][0]["hint_terms"])
            self.assertEqual(payload_template["files"][0]["logs"][0]["message_template"], "load profile start")
            self.assertEqual(payload_template["files"][0]["logs"][0]["function"], "loadUserProfile")
            self.assertIn("hilog", payload_template["files"][0]["logs"][0]["hint_terms"])
            self.assertEqual(
                action["workflow_steps"],
                [
                    "Read the listed files, symbols, and logs in current source.",
                    "Fill missing business_summary and business_terms in learn_business_payload_template.",
                    "Write the completed payload with learn-business.",
                    "Re-run query or maintain-plan to confirm the semantic gap is reduced.",
                ],
            )

    def test_maintain_plan_query_miss_prefers_route_scene_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "context", "--query", "页面跳转后白屏但没有命中", "--json")
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "import hilog from '@ohos.hilog';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "  aboutToAppear() {\n"
                "    hilog.error(0x0000, 'Index', 'account sync failed');\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            result = self.run_memory(project, "maintain-plan", "--json")
            actions = json.loads(result.stdout)["actions"]
            action = next(action for action in actions if action["action"] == "review_query_miss" and action["query"] == "页面跳转后白屏但没有命中")

            self.assertEqual(action["followup_focus"], "route")
            self.assertIn("pages/detail", action["suggested_query_terms"])
            self.assertLess(
                action["suggested_query_terms"].index("pages/detail"),
                action["suggested_query_terms"].index("pages/index.ets"),
            )

    def test_maintain_plan_surfaces_recent_semantic_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps(
                    {
                        "files": [
                            {
                                "file_path": "pages/ProfileDetail.ets",
                                "business_summary": "用户资料详情页",
                                "symbols": [
                                    {
                                        "symbol": "profileCache",
                                        "symbol_type": "field",
                                        "business_summary": "资料缓存字段。",
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps(
                    {
                        "files": [
                            {
                                "file_path": "pages/ProfileDetail.ets",
                                "business_summary": "订单详情页",
                                "symbols": [
                                    {
                                        "symbol": "profileCache",
                                        "symbol_type": "field",
                                        "business_summary": "订单缓存字段。",
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )

            runtime_file = self.project_memory_dir(project) / "runtime" / "last_learn_business.json"
            runtime_file.unlink()
            payload = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)
            actions = payload["actions"]
            conflict_actions = [action for action in actions if action["action"] == "review_semantic_conflict"]

            self.assertEqual(payload["summary"]["semantic_conflicts"], 2)
            self.assertEqual(len(conflict_actions), 2)
            self.assertEqual(conflict_actions[0]["type"], "semantic_conflict")
            self.assertEqual(conflict_actions[0]["source_command"], "learn-business")
            self.assertIsNotNone(conflict_actions[0]["observed_at"])
            self.assertIn(conflict_actions[0]["target"], {"pages/ProfileDetail.ets", "pages/ProfileDetail.ets::profileCache"})
            self.assertIn("conflict-apply --project . --id", conflict_actions[0]["apply_command_template"])

    def test_vault_export_writes_semantic_conflicts_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps(
                    {
                        "files": [
                            {
                                "file_path": "pages/ProfileDetail.ets",
                                "business_summary": "用户资料详情页",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps(
                    {
                        "files": [
                            {
                                "file_path": "pages/ProfileDetail.ets",
                                "business_summary": "订单详情页",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )

            self.run_memory(project, "vault-export")
            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Semantic Conflicts.md"
            index = self.project_memory_dir(project) / "vault" / "index.md"
            content = dashboard.read_text(encoding="utf-8")
            index_text = index.read_text(encoding="utf-8")

            self.assertIn("pages/ProfileDetail.ets", content)
            self.assertIn("用户资料详情页", content)
            self.assertIn("订单详情页", content)
            self.assertIn("[[Governance/Semantic Conflicts]]", index_text)

    def test_vault_review_queue_lists_open_semantic_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps({"files": [{"file_path": "pages/ProfileDetail.ets", "business_summary": "用户资料详情页"}]}, ensure_ascii=False),
                "--json",
            )
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps({"files": [{"file_path": "pages/ProfileDetail.ets", "business_summary": "订单详情页"}]}, ensure_ascii=False),
                "--json",
            )

            self.run_memory(project, "vault-export")
            review_queue = self.project_memory_dir(project) / "vault" / "Governance" / "Review Queue.md"
            content = review_queue.read_text(encoding="utf-8")

            self.assertIn("Open Semantic Conflicts", content)
            self.assertIn("pages/ProfileDetail.ets", content)

    def test_vault_health_breaks_open_semantic_conflicts_down_by_entity_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps(
                    {
                        "files": [
                            {
                                "file_path": "pages/ProfileDetail.ets",
                                "business_summary": "用户资料详情页",
                                "symbols": [
                                    {
                                        "symbol": "profileCache",
                                        "symbol_type": "field",
                                        "business_summary": "资料缓存字段。",
                                    }
                                ],
                                "logs": [
                                    {
                                        "message_template": "load profile failed",
                                        "function": "loadUserProfile",
                                        "level": "error",
                                        "business_summary": "资料加载失败日志。",
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps(
                    {
                        "files": [
                            {
                                "file_path": "pages/ProfileDetail.ets",
                                "business_summary": "订单详情页",
                                "symbols": [
                                    {
                                        "symbol": "profileCache",
                                        "symbol_type": "field",
                                        "business_summary": "订单缓存字段。",
                                    }
                                ],
                                "logs": [
                                    {
                                        "message_template": "load profile failed",
                                        "function": "loadUserProfile",
                                        "level": "error",
                                        "business_summary": "订单失败日志。",
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )

            self.run_memory(project, "vault-export")
            health = self.project_memory_dir(project) / "vault" / "Governance" / "Health.md"
            content = health.read_text(encoding="utf-8")

            self.assertIn("- Open semantic conflicts: 3", content)
            self.assertIn("- Open file semantic conflicts: 1", content)
            self.assertIn("- Open symbol semantic conflicts: 1", content)
            self.assertIn("- Open log semantic conflicts: 1", content)

    def test_conflict_status_updates_semantic_conflict_review_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps({"files": [{"file_path": "pages/ProfileDetail.ets", "business_summary": "用户资料详情页"}]}, ensure_ascii=False),
                "--json",
            )
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps({"files": [{"file_path": "pages/ProfileDetail.ets", "business_summary": "订单详情页"}]}, ensure_ascii=False),
                "--json",
            )

            conflicts_before = self.list_records(project, "semantic-conflict")
            self.assertEqual(len(conflicts_before), 1)

            self.run_memory(
                project,
                "conflict-status",
                "--id",
                str(conflicts_before[0]["id"]),
                "--status",
                "resolved",
                "--resolution",
                "confirmed existing summary against current source",
                "--decision-note",
                "Current ProfileDetail page still loads profile data, not order data.",
                "--replacement-source",
                "source:pages/ProfileDetail.ets",
            )

            conflicts_after = self.list_records(project, "semantic-conflict")
            self.assertEqual(conflicts_after[0]["status"], "resolved")
            self.assertEqual(conflicts_after[0]["resolution"], "confirmed existing summary against current source")
            self.assertEqual(conflicts_after[0]["decision_note"], "Current ProfileDetail page still loads profile data, not order data.")
            self.assertEqual(conflicts_after[0]["replacement_source"], "source:pages/ProfileDetail.ets")
            self.assertTrue(conflicts_after[0]["reviewed_at"])

            payload = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)
            self.assertEqual(payload["summary"]["semantic_conflicts"], 0)

    def test_conflict_apply_updates_summary_and_closes_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps({"files": [{"file_path": "pages/ProfileDetail.ets", "business_summary": "用户资料详情页"}]}, ensure_ascii=False),
                "--json",
            )
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps({"files": [{"file_path": "pages/ProfileDetail.ets", "business_summary": "订单详情页"}]}, ensure_ascii=False),
                "--json",
            )

            conflict = self.list_records(project, "semantic-conflict")[0]

            self.run_memory(
                project,
                "conflict-apply",
                "--id",
                str(conflict["id"]),
                "--resolution",
                "confirmed incoming summary against current source",
                "--decision-note",
                "Page responsibility changed from profile detail to order detail in current source.",
                "--replacement-source",
                "source:pages/ProfileDetail.ets",
            )

            file_row = self.list_records(project, "code-file")[0]
            conflict_row = self.list_records(project, "semantic-conflict")[0]

            self.assertEqual(file_row["business_summary"], "订单详情页")
            self.assertEqual(conflict_row["status"], "applied")
            self.assertEqual(conflict_row["resolution"], "confirmed incoming summary against current source")
            self.assertEqual(conflict_row["decision_note"], "Page responsibility changed from profile detail to order detail in current source.")
            self.assertEqual(conflict_row["replacement_source"], "source:pages/ProfileDetail.ets")
            self.assertTrue(conflict_row["reviewed_at"])

            payload = json.loads(self.run_memory(project, "maintain-plan", "--json").stdout)
            self.assertEqual(payload["summary"]["semantic_conflicts"], 0)

    def test_conflict_apply_rejects_non_unique_log_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            first_payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "logs": [
                            {
                                "message_template": "load profile failed",
                                "function": "loadA",
                                "level": "error",
                                "business_summary": "资料加载失败日志 A",
                            },
                            {
                                "message_template": "load profile failed",
                                "function": "loadB",
                                "level": "error",
                                "business_summary": "资料加载失败日志 B",
                            },
                        ],
                    }
                ]
            }
            conflicting_payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "logs": [
                            {
                                "message_template": "load profile failed",
                                "function": "loadA",
                                "level": "error",
                                "business_summary": "订单失败日志",
                            }
                        ],
                    }
                ]
            }

            self.run_memory(project, "learn-business", "--payload", json.dumps(first_payload, ensure_ascii=False), "--json")
            self.run_memory(project, "learn-business", "--payload", json.dumps(conflicting_payload, ensure_ascii=False), "--json")

            conflict = self.list_records(project, "semantic-conflict")[0]
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNTIME),
                    "conflict-apply",
                    "--id",
                    str(conflict["id"]),
                    "--project",
                    str(project),
                    "--memory-home",
                    str(self.memory_home(project)),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("matched 2 rows", result.stderr)

    def test_vault_export_writes_query_misses_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "context", "--query", "unanswered-question", "--json")

            self.run_memory(project, "vault-export")

            dashboard = self.project_memory_dir(project) / "vault" / "Governance" / "Query Misses.md"
            self.assertTrue(dashboard.exists())
            self.assertIn("unanswered-question", dashboard.read_text(encoding="utf-8"))

    def test_vault_export_writes_query_misses_codebase_wiki_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(project, "context", "--query", "arkts route miss", "--json")
            self.run_memory(project, "context", "--query", "arkts   route miss", "--json")

            self.run_memory(project, "vault-export")

            wiki_page = self.project_memory_dir(project) / "vault" / "Codebase Wiki" / "query-misses.md"
            index = self.project_memory_dir(project) / "vault" / "index.md"
            self.assertTrue(wiki_page.exists())
            content = wiki_page.read_text(encoding="utf-8")
            self.assertIn("arkts route miss", content)
            self.assertIn("misses 2", content)
            self.assertIn("[[Codebase Wiki/query-misses]]", index.read_text(encoding="utf-8"))

    def test_learn_path_extracts_python_print_and_logger_statements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "service.py").write_text(
                "import logging\n"
                "logger = logging.getLogger(__name__)\n\n"
                "def sync_user(user_id):\n"
                "    print('starting sync', user_id)\n"
                "    logger.error('sync failed for user %s', user_id)\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", ".")

            logs = sorted(self.list_records(project, "code-log"), key=lambda row: row["line"])
            self.assertEqual([log["level"] for log in logs], ["print", "error"])
            self.assertEqual([log["function"] for log in logs], ["sync_user", "sync_user"])
            self.assertIn("sync failed for user %s", logs[1]["message_template"])

    def test_learn_path_extracts_javascript_console_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "app.js").write_text(
                "function loadUser(id) {\n"
                "  console.error('load failed', id);\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", ".")

            logs = self.list_records(project, "code-log")
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["level"], "error")
            self.assertEqual(logs[0]["function"], "loadUser")
            self.assertIn("load failed", logs[0]["message_template"])

    def test_learn_path_extracts_arkts_symbols_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import hilog from '@ohos.hilog';\n\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  aboutToAppear(): void {\n"
                "    console.error('load account failed');\n"
                "    hilog.info(0x0000, 'Index', 'page ready %{public}s', 'ok');\n"
                "  }\n"
                "  build() {\n"
                "    Column() {}\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            files = self.list_code_files(project)
            symbols = self.list_records(project, "code-symbol")
            logs = sorted(self.list_records(project, "code-log"), key=lambda row: row["line"])

            self.assertEqual(files, {"pages/Index.ets"})
            self.assertTrue(any(row["symbol"] == "Index" and row["symbol_type"] == "component" for row in symbols))
            self.assertTrue(any(row["symbol"] == "aboutToAppear" and row["symbol_type"] == "function" for row in symbols))
            self.assertEqual([log["level"] for log in logs], ["error", "info"])
            self.assertEqual([log["function"] for log in logs], ["aboutToAppear", "aboutToAppear"])
            self.assertEqual(logs[1]["logger"], "hilog")
            self.assertIn("page ready %{public}s", logs[1]["message_template"])

    def test_learn_entry_follows_arkts_relative_imports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "model").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import { UserModel } from '../model/UserModel';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  build() {}\n"
                "}\n",
                encoding="utf-8",
            )
            (project / "model" / "UserModel.ets").write_text(
                "export class UserModel {\n"
                "  name: string = '';\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-entry", "--entry", "pages/Index.ets", "--depth", "1", "--json")

            self.assertEqual(self.list_code_files(project), {"pages/Index.ets", "model/UserModel.ets"})

    def test_learn_path_extracts_harmonyos_json5_config_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "entry" / "src" / "main").mkdir(parents=True)
            (project / "entry" / "oh-package.json5").write_text(
                "{\n"
                "  \"dependencies\": {\n"
                "    \"@ohos/axios\": \"^2.2.0\"\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            (project / "entry" / "src" / "main" / "module.json5").write_text(
                "{\n"
                "  \"module\": {\n"
                "    \"name\": \"entry\",\n"
                "    \"abilities\": [{ \"name\": \"EntryAbility\" }],\n"
                "    \"requestPermissions\": [{ \"name\": \"ohos.permission.INTERNET\" }],\n"
                "    \"pages\": \"$profile:main_pages\"\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "entry")

            symbols = self.list_records(project, "code-symbol")
            symbol_pairs = {(row["symbol"], row["symbol_type"]) for row in symbols}
            self.assertIn(("EntryAbility", "ability"), symbol_pairs)
            self.assertIn(("ohos.permission.INTERNET", "permission"), symbol_pairs)
            self.assertIn(("@ohos/axios", "dependency"), symbol_pairs)

    def test_learn_path_extracts_arkts_router_and_resource_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  build() {\n"
                "    Text($r('app.string.home_title'))\n"
                "    Image($r(\"app.media.logo\"))\n"
                "  }\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            symbols = self.list_records(project, "code-symbol")
            symbol_pairs = {(row["symbol"], row["symbol_type"]) for row in symbols}
            self.assertIn(("pages/Detail", "route"), symbol_pairs)
            self.assertIn(("app.string.home_title", "resource"), symbol_pairs)
            self.assertIn(("app.media.logo", "resource"), symbol_pairs)

    def test_arkts_learning_writes_knowledge_summaries_for_files_and_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  build() {\n"
                "    Text($r('app.string.home_title'))\n"
                "  }\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            files = self.list_records(project, "code-file")
            symbols = self.list_records(project, "code-symbol")
            file_summary = files[0]["summary"]
            symbol_summaries = {
                (row["symbol"], row["symbol_type"]): row["summary"]
                for row in symbols
            }

            self.assertIn("components: Index", file_summary)
            self.assertIn("routes: pages/Detail", file_summary)
            self.assertIn("resources: app.string.home_title", file_summary)
            self.assertIn("ArkTS component", symbol_summaries[("Index", "component")])
            self.assertIn("route target", symbol_summaries[("pages/Detail", "route")])
            self.assertIn("resource", symbol_summaries[("app.string.home_title", "resource")])

    def test_chinese_problem_query_expands_to_arkts_route_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            result = self.run_memory(project, "context", "--query", "页面跳转后白屏", "--json")
            data = json.loads(result.stdout)
            matched = [
                item
                for item in data["wiki_matches"]
                if item.get("symbol") == "pages/Detail" or item.get("file_path") == "pages/Index.ets"
            ]
            self.assertTrue(matched)
            self.assertTrue(any(item.get("match_reasons") for item in matched))
            self.assertTrue(any("expanded_query" in reason for item in matched for reason in item["match_reasons"]))
            self.assertEqual(data["followup_focus"], "route")
            self.assertIn("pages/detail", data["suggested_followup_terms"][:3])
            self.assertLess(
                data["suggested_followup_terms"].index("pages/detail"),
                data["suggested_followup_terms"].index("pages/index.ets"),
            )

    def test_chinese_problem_query_expands_to_arkts_resource_and_log_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import hilog from '@ohos.hilog';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  build() {\n"
                "    Image($r('app.media.logo'))\n"
                "  }\n"
                "  aboutToAppear() {\n"
                "    hilog.error(0x0000, 'Index', 'load profile failed');\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            resource_result = self.run_memory(project, "context", "--query", "图片资源显示不出来", "--json")
            resource_data = json.loads(resource_result.stdout)
            self.assertEqual(resource_data["followup_focus"], "resource")
            self.assertTrue(
                any(item.get("symbol") == "app.media.logo" for item in resource_data["wiki_matches"])
            )
            resource_match = next(item for item in resource_data["wiki_matches"] if item.get("symbol") == "app.media.logo")
            self.assertIn("resource", resource_match["search_terms"])
            self.assertIn("app.media.logo", resource_data["suggested_followup_terms"])
            self.assertIn("app.media.logo", resource_data["suggested_followup_terms"][:3])
            self.assertLess(
                resource_data["suggested_followup_terms"].index("app.media.logo"),
                resource_data["suggested_followup_terms"].index("resource"),
            )

            log_result = self.run_memory(project, "context", "--query", "加载用户资料失败日志", "--json")
            log_data = json.loads(log_result.stdout)
            self.assertEqual(log_data["followup_focus"], "log")
            self.assertTrue(
                any(item.get("message_template") == "load profile failed" for item in log_data["code_log_matches"])
            )
            log_match = next(item for item in log_data["code_log_matches"] if item.get("message_template") == "load profile failed")
            self.assertTrue(any("log" in reason for reason in log_match["match_reasons"]))
            self.assertIn("load profile failed", log_data["suggested_followup_terms"])
            self.assertIn("load profile failed", log_data["suggested_followup_terms"][:3])
            self.assertLess(
                log_data["suggested_followup_terms"].index("load profile failed"),
                log_data["suggested_followup_terms"].index("app.media.logo"),
            )

    def test_chinese_problem_query_expands_to_harmonyos_config_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "entry" / "src" / "main").mkdir(parents=True)
            (project / "entry" / "src" / "main" / "module.json5").write_text(
                "{\n"
                "  \"module\": {\n"
                "    \"name\": \"entry\",\n"
                "    \"abilities\": [{ \"name\": \"EntryAbility\" }],\n"
                "    \"requestPermissions\": [{ \"name\": \"ohos.permission.INTERNET\" }]\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "entry")

            result = self.run_memory(project, "context", "--query", "网络权限配置异常", "--json")
            data = json.loads(result.stdout)
            self.assertEqual(data["followup_focus"], "config")
            self.assertTrue(
                any(item.get("symbol") == "ohos.permission.INTERNET" for item in data["wiki_matches"])
            )
            self.assertIn("ohos.permission.internet", data["suggested_followup_terms"][:5])
            self.assertLess(
                data["suggested_followup_terms"].index("ohos.permission.internet"),
                data["suggested_followup_terms"].index("entryability"),
            )

    def test_route_problem_prefers_route_anchor_over_unrelated_log_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "import hilog from '@ohos.hilog';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "  aboutToAppear() {\n"
                "    hilog.error(0x0000, 'Index', 'account sync failed');\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            result = self.run_memory(project, "context", "--query", "页面跳转后白屏", "--json")
            data = json.loads(result.stdout)
            self.assertIn("pages/detail", data["suggested_followup_terms"])
            self.assertLess(
                data["suggested_followup_terms"].index("pages/detail"),
                data["suggested_followup_terms"].index("pages/index.ets"),
            )

    def test_query_reranks_exact_file_path_above_expanded_summary_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            (project / "pages" / "Detail.ets").write_text(
                "@Entry\n"
                "@Component\n"
                "struct Detail {\n"
                "  build() {}\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")

            result = self.run_memory(project, "context", "--query", "pages/Detail.ets", "--json")
            data = json.loads(result.stdout)

            self.assertEqual(data["wiki_matches"][0]["file_path"], "pages/Detail.ets")
            self.assertIn("exact_file_path", data["wiki_matches"][0]["match_reasons"])

    def test_learn_business_writes_business_semantics_to_existing_code_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "summary": "ArkTS profile detail page",
                        "business_summary": "个人信息详情页，负责加载用户资料并展示头像。",
                        "business_terms": ["个人信息", "用户资料", "profile", "头像", "avatar"],
                        "symbols": [
                            {
                                "symbol": "loadUserProfile",
                                "symbol_type": "function",
                                "business_summary": "加载用户资料的方法。",
                                "business_terms": ["加载用户资料", "profile", "load profile"],
                            }
                        ],
                        "logs": [
                            {
                                "message_template": "load profile failed",
                                "function": "loadUserProfile",
                                "level": "error",
                                "logger": "hilog",
                                "business_summary": "用户资料加载失败时输出的错误日志。",
                                "business_terms": ["用户资料加载失败", "profile failed", "load profile failed"],
                            }
                        ],
                    }
                ]
            }

            self.run_memory(project, "learn-business", "--payload", json.dumps(payload, ensure_ascii=False), "--json")

            files = self.list_records(project, "code-file")
            symbols = self.list_records(project, "code-symbol")
            logs = self.list_records(project, "code-log")
            self.assertEqual(files[0]["business_summary"], "个人信息详情页，负责加载用户资料并展示头像。")
            self.assertIn("头像", json.loads(files[0]["business_terms"]))
            self.assertEqual(symbols[0]["business_summary"], "加载用户资料的方法。")
            self.assertEqual(logs[0]["business_summary"], "用户资料加载失败时输出的错误日志。")

    def test_business_terms_are_high_signal_query_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "business_summary": "个人信息详情页，负责加载用户资料并展示头像。",
                        "business_terms": ["个人信息", "用户资料", "profile", "头像", "avatar"],
                        "symbols": [
                            {
                                "symbol": "loadUserProfile",
                                "symbol_type": "function",
                                "business_summary": "加载用户资料的方法。",
                                "business_terms": ["加载用户资料", "profile", "load profile"],
                            }
                        ],
                        "logs": [
                            {
                                "message_template": "load profile failed",
                                "function": "loadUserProfile",
                                "level": "error",
                                "business_summary": "用户资料加载失败时输出的错误日志。",
                                "business_terms": ["用户资料加载失败", "profile failed"],
                            }
                        ],
                    }
                ]
            }
            self.run_memory(project, "learn-business", "--payload", json.dumps(payload, ensure_ascii=False), "--json")

            result = self.run_memory(project, "context", "--query", "个人信息头像加载失败", "--json")
            data = json.loads(result.stdout)

            self.assertEqual(data["wiki_matches"][0]["file_path"], "pages/ProfileDetail.ets")
            self.assertIn("头像", data["wiki_matches"][0]["business_terms"])
            self.assertTrue(any("business_terms" in reason for reason in data["wiki_matches"][0]["match_reasons"]))
            self.assertTrue(any(log["message_template"] == "load profile failed" for log in data["code_log_matches"]))

    def test_vault_and_health_include_code_business_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "business_summary": "个人信息详情页，负责加载用户资料并展示头像。",
                        "business_terms": ["个人信息", "profile", "头像"],
                    }
                ]
            }
            self.run_memory(project, "learn-business", "--payload", json.dumps(payload, ensure_ascii=False), "--json")
            self.run_memory(project, "learn-business", "--payload", json.dumps({"files": [{"file_path": "pages/Empty.ets"}]}), "--json")

            health = json.loads(self.run_memory(project, "maintain-health", "--json").stdout)
            self.assertEqual(health["counts"]["code_files_missing_business_terms"], 1)

            self.run_memory(project, "vault-export")
            files_page = self.project_memory_dir(project) / "vault" / "Codebase Wiki" / "files.md"
            content = files_page.read_text(encoding="utf-8")
            self.assertIn("Business: 个人信息详情页", content)
            self.assertIn("Terms: 个人信息, profile, 头像", content)

    def test_learn_business_reports_semantic_stats_and_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            payload = {
                "files": [
                    {
                        "file_path": "pages/Empty.ets",
                    },
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "business_summary": "个人信息详情页，负责加载用户资料并展示头像。",
                        "business_terms": ["个人信息", "profile", "头像"],
                        "symbols": [
                            {
                                "symbol": "loadUserProfile",
                                "symbol_type": "function",
                                "business_summary": "加载用户资料的方法。",
                                "business_terms": ["加载用户资料", "profile", "load profile"],
                            },
                            {
                                "symbol": "profileCache",
                                "symbol_type": "field",
                            },
                        ],
                        "logs": [
                            {
                                "message_template": "load profile failed",
                                "function": "loadUserProfile",
                                "level": "error",
                                "business_summary": "用户资料加载失败时输出的错误日志。",
                                "business_terms": ["用户资料加载失败", "profile failed"],
                            },
                            {
                                "message_template": "load profile start",
                                "function": "loadUserProfile",
                                "level": "info",
                            },
                        ],
                    },
                ]
            }

            result = self.run_memory(project, "learn-business", "--payload", json.dumps(payload, ensure_ascii=False), "--json")
            data = json.loads(result.stdout)

            self.assertEqual(data["semantic_stats"]["files_total"], 2)
            self.assertEqual(data["semantic_stats"]["files_with_business_summary"], 1)
            self.assertEqual(data["semantic_stats"]["symbols_total"], 2)
            self.assertEqual(data["semantic_stats"]["symbols_with_business_terms"], 1)
            self.assertEqual(data["semantic_stats"]["logs_total"], 2)
            self.assertEqual(data["semantic_stats"]["logs_with_business_summary"], 1)
            self.assertIn("pages/Empty.ets", data["semantic_gaps"]["files_missing_business_summary"])
            self.assertIn("pages/ProfileDetail.ets::profileCache", data["semantic_gaps"]["symbols_missing_business_terms"])
            self.assertIn("pages/ProfileDetail.ets::load profile start", data["semantic_gaps"]["logs_missing_business_summary"])
            self.assertEqual(
                data["semantic_followup"]["command_template"],
                "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
            )
            self.assertEqual(
                data["semantic_followup"]["workflow_steps"],
                [
                    "Read the listed files, symbols, and logs in current source.",
                    "Fill missing business_summary and business_terms in followup_payload_template.",
                    "Write the completed payload with learn-business.",
                    "Re-run learn-business, query, or maintain-plan to confirm the semantic gap is reduced.",
                ],
            )
            self.assertEqual(data["semantic_followup"]["recommended_next_action"], "run_learn_business_now")
            self.assertFalse(data["semantic_followup"]["truncated"])
            followup = data["semantic_followup"]["followup_payload_template"]
            self.assertEqual(followup["files"][0]["file_path"], "pages/ProfileDetail.ets")
            self.assertGreater(followup["files"][0]["priority_score"], followup["files"][1]["priority_score"])
            self.assertIn("missing_log_semantics", followup["files"][0]["priority_reasons"])
            self.assertIn("pages/ProfileDetail.ets", followup["files"][0]["hint_context"])
            self.assertIn("profiledetail", followup["files"][0]["hint_terms"])
            self.assertEqual(followup["files"][0]["symbols"][0]["symbol"], "profileCache")
            self.assertIn("profilecache", followup["files"][0]["symbols"][0]["hint_terms"])
            self.assertIn("field", followup["files"][0]["symbols"][0]["hint_context"])
            self.assertEqual(followup["files"][0]["logs"][0]["message_template"], "load profile start")
            self.assertIn("load", followup["files"][0]["logs"][0]["hint_terms"])
            self.assertIn("loadUserProfile", followup["files"][0]["logs"][0]["hint_context"])
            self.assertEqual(followup["files"][1]["file_path"], "pages/Empty.ets")
            self.assertIn("missing_file_business_summary", followup["files"][1]["priority_reasons"])
            self.assertIn("missing_file_business_terms", followup["files"][1]["priority_reasons"])

    def test_learn_business_followup_truncates_to_priority_batch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            files = []
            for index in range(6):
                files.append(
                    {
                        "file_path": f"pages/Page{index}.ets",
                        "symbols": [
                            {
                                "symbol": f"loadPage{index}",
                                "symbol_type": "function",
                            }
                        ],
                    }
                )
            payload = {"files": files}

            result = self.run_memory(project, "learn-business", "--payload", json.dumps(payload, ensure_ascii=False), "--json")
            data = json.loads(result.stdout)

            self.assertTrue(data["semantic_followup"]["truncated"])
            self.assertEqual(data["semantic_followup"]["remaining_counts"]["files"], 1)
            self.assertEqual(data["semantic_followup"]["returned_counts"]["files"], 5)
            self.assertEqual(len(data["semantic_followup"]["followup_payload_template"]["files"]), 5)
            self.assertEqual(
                data["semantic_followup"]["recommended_next_action"],
                "run_learn_business_now",
            )

    def test_learn_business_partial_update_keeps_unmentioned_symbols_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            first_payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "business_summary": "个人信息详情页",
                        "business_terms": ["个人信息", "profile"],
                        "symbols": [
                            {
                                "symbol": "loadUserProfile",
                                "symbol_type": "function",
                                "business_summary": "加载用户资料的方法。",
                                "business_terms": ["加载用户资料", "load profile"],
                            },
                            {
                                "symbol": "profileCache",
                                "symbol_type": "field",
                                "business_summary": "资料缓存字段。",
                                "business_terms": ["资料缓存", "profile cache"],
                            },
                        ],
                        "logs": [
                            {
                                "message_template": "load profile failed",
                                "function": "loadUserProfile",
                                "level": "error",
                                "business_summary": "资料加载失败日志。",
                                "business_terms": ["资料加载失败", "profile failed"],
                            },
                            {
                                "message_template": "load profile start",
                                "function": "loadUserProfile",
                                "level": "info",
                                "business_summary": "资料加载开始日志。",
                                "business_terms": ["资料加载开始", "profile start"],
                            },
                        ],
                    }
                ]
            }
            second_payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "symbols": [
                            {
                                "symbol": "profileCache",
                                "symbol_type": "field",
                                "business_terms": ["头像缓存", "avatar cache"],
                            }
                        ],
                        "logs": [
                            {
                                "message_template": "load profile start",
                                "function": "loadUserProfile",
                                "level": "info",
                                "business_terms": ["进入加载", "load entry"],
                            }
                        ],
                    }
                ]
            }

            self.run_memory(project, "learn-business", "--payload", json.dumps(first_payload, ensure_ascii=False), "--json")
            self.run_memory(project, "learn-business", "--payload", json.dumps(second_payload, ensure_ascii=False), "--json")

            symbols = sorted(self.list_records(project, "code-symbol"), key=lambda row: row["symbol"])
            logs = sorted(self.list_records(project, "code-log"), key=lambda row: row["message_template"])

            self.assertEqual([row["symbol"] for row in symbols], ["loadUserProfile", "profileCache"])
            self.assertEqual([row["message_template"] for row in logs], ["load profile failed", "load profile start"])
            profile_cache_terms = json.loads(next(row for row in symbols if row["symbol"] == "profileCache")["business_terms"])
            self.assertIn("profile cache", profile_cache_terms)
            self.assertIn("avatar cache", profile_cache_terms)
            load_start_terms = json.loads(next(row for row in logs if row["message_template"] == "load profile start")["business_terms"])
            self.assertIn("profile start", load_start_terms)
            self.assertIn("load entry", load_start_terms)

    def test_learn_business_preserves_existing_non_empty_summary_and_reports_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            first_payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "business_summary": "用户资料详情页",
                        "business_terms": ["用户资料", "profile"],
                        "symbols": [
                            {
                                "symbol": "profileCache",
                                "symbol_type": "field",
                                "business_summary": "资料缓存字段。",
                                "business_terms": ["资料缓存", "profile cache"],
                            }
                        ],
                    }
                ]
            }
            conflicting_payload = {
                "files": [
                    {
                        "file_path": "pages/ProfileDetail.ets",
                        "business_summary": "订单详情页",
                        "symbols": [
                            {
                                "symbol": "profileCache",
                                "symbol_type": "field",
                                "business_summary": "订单缓存字段。",
                            }
                        ],
                    }
                ]
            }

            self.run_memory(project, "learn-business", "--payload", json.dumps(first_payload, ensure_ascii=False), "--json")
            result = self.run_memory(project, "learn-business", "--payload", json.dumps(conflicting_payload, ensure_ascii=False), "--json")
            data = json.loads(result.stdout)

            files = self.list_records(project, "code-file")
            symbols = self.list_records(project, "code-symbol")
            self.assertEqual(files[0]["business_summary"], "用户资料详情页")
            self.assertEqual(symbols[0]["business_summary"], "资料缓存字段。")
            self.assertEqual(
                data["semantic_conflicts"][0]["target"],
                "pages/ProfileDetail.ets",
            )
            self.assertEqual(
                data["semantic_conflicts"][1]["target"],
                "pages/ProfileDetail.ets::profileCache",
            )

    def test_arkts_memory_edges_connect_imports_routes_and_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "model").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import { UserModel } from '../model/UserModel';\n"
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  build() {\n"
                "    Text($r('app.string.home_title'))\n"
                "  }\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            (project / "pages" / "Detail.ets").write_text(
                "@Component\n"
                "struct Detail { build() {} }\n",
                encoding="utf-8",
            )
            (project / "model" / "UserModel.ets").write_text(
                "export class UserModel {}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-entry", "--entry", "pages/Index.ets", "--depth", "1", "--json")

            edges = self.list_records(project, "memory-edge")
            relations = {(edge["source_type"], edge["relation"], edge["target_type"]) for edge in edges}
            evidence_by_relation = {edge["relation"]: edge["evidence"] for edge in edges}

            self.assertIn(("code_file", "imports", "code_file"), relations)
            self.assertIn(("code_file", "routes_to", "code_file"), relations)
            self.assertIn(("code_file", "uses_resource", "code_symbol"), relations)
            self.assertIn("pages/Index.ets -> model/UserModel.ets", evidence_by_relation["imports"])
            self.assertIn("pages/Index.ets -> pages/Detail.ets", evidence_by_relation["routes_to"])
            self.assertIn("app.string.home_title", evidence_by_relation["uses_resource"])

    def test_learn_entry_follows_arkts_router_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "  build() {}\n"
                "}\n",
                encoding="utf-8",
            )
            (project / "pages" / "Detail.ets").write_text(
                "@Component\n"
                "struct Detail {\n"
                "  build() {}\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-entry", "--entry", "pages/Index.ets", "--depth", "1", "--json")

            self.assertEqual(self.list_code_files(project), {"pages/Index.ets", "pages/Detail.ets"})

    def test_learn_entry_returns_parse_stats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Index.ets").write_text(
                "import router from '@ohos.router';\n"
                "@Entry\n"
                "@Component\n"
                "struct Index {\n"
                "  aboutToAppear(): void {\n"
                "    console.error('load failed');\n"
                "  }\n"
                "  openDetail() {\n"
                "    router.pushUrl({ url: 'pages/Detail' });\n"
                "  }\n"
                "  build() {\n"
                "    Text($r('app.string.home_title'))\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            result = self.run_memory(project, "learn-entry", "--entry", "pages/Index.ets", "--depth", "0", "--json")
            stats = json.loads(result.stdout)["parse_stats"]

            self.assertEqual(stats["files_indexed"], 1)
            self.assertEqual(stats["languages"]["ArkTS"], 1)
            self.assertEqual(stats["symbols_by_type"]["component"], 1)
            self.assertEqual(stats["symbols_by_type"]["route"], 1)
            self.assertEqual(stats["symbols_by_type"]["resource"], 1)
            self.assertEqual(stats["code_logs_total"], 1)
            self.assertEqual(stats["code_logs_by_level"]["error"], 1)
            self.assertGreaterEqual(stats["memory_edges_total"], 1)
            followup = json.loads(result.stdout)["semantic_followup"]
            self.assertEqual(
                followup["command_template"],
                "python tools/agent_memory.py learn-business --project . --payload '<json>' --json",
            )
            self.assertEqual(followup["followup_payload_template"]["files"][0]["file_path"], "pages/Index.ets")
            self.assertEqual(
                followup["followup_payload_template"]["files"][0]["logs"][0]["message_template"],
                "load failed",
            )
            self.assertIn("console", followup["followup_payload_template"]["files"][0]["logs"][0]["hint_terms"])
            self.assertTrue(
                any(
                    "app.string.home_title" in symbol["hint_context"]
                    for symbol in followup["followup_payload_template"]["files"][0]["symbols"]
                )
            )

    def test_learn_path_json_returns_parse_stats_for_harmonyos_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "entry").mkdir()
            (project / "entry" / "oh-package.json5").write_text(
                "{\n"
                "  \"dependencies\": {\n"
                "    \"@ohos/axios\": \"^2.2.0\"\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            result = self.run_memory(project, "learn-path", "--path", "entry", "--json")
            payload = json.loads(result.stdout)

            self.assertEqual(payload["parse_stats"]["files_indexed"], 1)
            self.assertEqual(payload["parse_stats"]["languages"]["HarmonyOS Config"], 1)
            self.assertEqual(payload["parse_stats"]["symbols_by_type"]["dependency"], 1)
            self.assertEqual(
                payload["semantic_followup"]["followup_payload_template"]["files"][0]["file_path"],
                "entry/oh-package.json5",
            )
            self.assertEqual(
                payload["semantic_followup"]["followup_payload_template"]["files"][0]["symbols"][0]["symbol"],
                "@ohos/axios",
            )

    def test_context_returns_code_log_and_related_edge_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            result = self.run_memory(project, "context", "--query", "retrying job", "--json")
            payload = json.loads(result.stdout)

            self.assertEqual(payload["code_log_matches"][0]["file_path"], "worker.py")
            self.assertEqual(payload["code_log_matches"][0]["function"], "process_job")
            self.assertTrue(
                any(edge["relation"] == "emits_log" for edge in payload["edge_matches"])
            )

    def test_search_returns_batched_aggregate_metadata_and_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            for index in range(6):
                self.run_memory(
                    project,
                    "update",
                    "--type",
                    "semantic",
                    "--fact",
                    f"profile timeout investigation note {index}",
                    "--source",
                    "test",
                    "--confidence",
                    "1.0",
                )

            first = json.loads(
                self.run_memory(
                    project,
                    "search",
                    "--query",
                    "profile timeout",
                    "--per-type-limit",
                    "5",
                    "--aggregate-limit",
                    "3",
                    "--json",
                ).stdout
            )
            second = json.loads(
                self.run_memory(
                    project,
                    "search",
                    "--query",
                    "profile timeout",
                    "--per-type-limit",
                    "5",
                    "--aggregate-limit",
                    "3",
                    "--cursor",
                    "3",
                    "--json",
                ).stdout
            )

            self.assertTrue(first["truncated"])
            self.assertEqual(first["next_cursor"], 3)
            self.assertEqual(first["total_candidates_by_type"]["semantic_facts"], 6)
            self.assertEqual(first["returned_counts_by_type"]["semantic_facts"], 3)
            self.assertEqual(len(first["semantic_facts"]), 3)
            self.assertIsNone(first["followup_focus"])
            self.assertIn("profile", first["suggested_followup_terms"])
            self.assertEqual(second["returned_counts_by_type"]["semantic_facts"], 3)
            self.assertIsNone(second["next_cursor"])
            self.assertEqual(len(second["semantic_facts"]), 3)

    def test_context_limits_network_edges_and_reports_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            db_path = self.project_memory_dir(project) / "memory.db"
            with sqlite3.connect(db_path) as conn:
                project_id = conn.execute("SELECT project_id FROM projects").fetchone()[0]
                for index in range(25):
                    conn.execute(
                        """
                        INSERT INTO memory_edges(
                          project_id, source_type, source_id, relation, target_type,
                          target_id, evidence, confidence, created_at
                        )
                        VALUES (?, 'code_log_statement', 1, 'calls', 'code_symbol', ?, 'synthetic', 0.9, '2026-01-01T00:00:00+00:00')
                        """,
                        (project_id, 1000 + index),
                    )

            result = self.run_memory(project, "context", "--query", "retrying job", "--json")
            payload = json.loads(result.stdout)

            self.assertEqual(payload["network_limits"]["max_depth"], 1)
            self.assertEqual(payload["network_limits"]["edge_limit"], 10)
            self.assertNotIn("calls", payload["network_limits"]["allowed_relations"])
            self.assertLessEqual(len(payload["edge_matches"]), 10)
            self.assertTrue(all(edge["relation"] != "calls" for edge in payload["edge_matches"]))

    def test_collect_related_edges_handles_more_than_thousand_targets(self) -> None:
        from tools.agent_memory_runtime.query import collect_related_edges
        from tools.agent_memory_runtime.storage import connect, ensure_initialized, resolve_project

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            project = resolve_project(str(project_path), str(self.memory_home(project_path)))
            ensure_initialized(project)

            with connect(project) as conn:
                for index in range(1200):
                    conn.execute(
                        """
                        INSERT INTO memory_edges(
                          project_id, source_type, source_id, relation, target_type,
                          target_id, evidence, confidence, created_at
                        )
                        VALUES (?, 'code_symbol', ?, 'emits_log', 'code_log_statement', ?, 'synthetic', 0.9, '2026-01-01T00:00:00+00:00')
                        """,
                        (project.project_id, index + 1, index + 1),
                    )
                conn.commit()

            targets = {
                "code_file": set(),
                "code_symbol": set(range(1, 1201)),
                "code_log_statement": set(),
            }
            edges = collect_related_edges(project, targets)

            self.assertLessEqual(len(edges), 10)

    def test_context_returns_one_hop_evidence_chains(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            result = self.run_memory(project, "context", "--query", "retrying job", "--json")
            payload = json.loads(result.stdout)
            chain = next(
                item for item in payload["evidence_chains"]
                if item["relation"] == "emits_log"
            )

            self.assertEqual(chain["depth"], 1)
            self.assertEqual(chain["reason"], "matched log statement emitted by symbol")
            self.assertEqual(chain["target_type"], "code_log_statement")
            self.assertIn("worker.py", chain["evidence"])

    def test_search_limits_large_result_sets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            for index in range(30):
                self.run_memory(
                    project,
                    "update",
                    "--type",
                    "semantic",
                    "--fact",
                    f"Route failure fact {index}",
                    "--source",
                    "test",
                )

            result = self.run_memory(project, "search", "--query", "route failure", "--json")
            payload = json.loads(result.stdout)

            self.assertLessEqual(len(payload["semantic_facts"]), 20)
            self.assertIn("result_limits", payload)
            self.assertEqual(payload["result_limits"]["semantic_facts"], 20)

    def test_context_json_stdout_preserves_chinese_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            self.run_memory(
                project,
                "update",
                "--type",
                "semantic",
                "--fact",
                "页面跳转后白屏需要先查路由",
                "--source",
                "test",
            )

            result = self.run_memory(project, "context", "--query", "页面跳转后白屏", "--json")

            self.assertIn("页面跳转后白屏", result.stdout)
            self.assertNotIn("\\u9875", result.stdout)

    def test_wiki_search_returns_code_log_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            result = self.run_memory(project, "wiki-search", "--query", "retrying job", "--json")
            payload = json.loads(result.stdout)

            self.assertEqual(payload[0]["kind"], "log_statement")
            self.assertEqual(payload[0]["function"], "process_job")

    def test_memory_edges_connect_files_symbols_and_log_statements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            edges = self.list_records(project, "memory-edge")
            relations = {(edge["source_type"], edge["relation"], edge["target_type"]) for edge in edges}

            self.assertIn(("code_file", "contains", "code_symbol"), relations)
            self.assertIn(("code_file", "contains", "code_log_statement"), relations)
            self.assertIn(("code_symbol", "emits_log", "code_log_statement"), relations)

    def test_learn_path_replace_clears_old_code_log_statements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "a").mkdir()
            (project / "b").mkdir()
            (project / "a" / "one.py").write_text(
                "def one():\n    print('old log')\n",
                encoding="utf-8",
            )
            (project / "b" / "two.py").write_text(
                "def two():\n    print('new log')\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "a")
            self.run_memory(project, "learn-path", "--path", "b", "--replace")

            logs = self.list_records(project, "code-log")
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["file_path"], "b/two.py")
            self.assertIn("new log", logs[0]["message_template"])

    def test_vault_export_writes_code_log_network_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "worker.py").write_text(
                "def process_job(job_id):\n"
                "    logger.warning('retrying job %s', job_id)\n",
                encoding="utf-8",
            )
            self.run_memory(project, "learn-path", "--path", ".")

            self.run_memory(project, "vault-export")

            logs = self.project_memory_dir(project) / "vault" / "Codebase Wiki" / "log-statements.md"
            edges = self.project_memory_dir(project) / "vault" / "Codebase Wiki" / "memory-edges.md"
            self.assertTrue(logs.exists())
            self.assertTrue(edges.exists())
            self.assertIn("retrying job %s", logs.read_text(encoding="utf-8"))
            self.assertIn("emits_log", edges.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
