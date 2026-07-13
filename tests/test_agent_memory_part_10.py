# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart10Tests(AgentMemoryTestBase):
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

    def test_context_includes_goal_oriented_log_search_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Profile.ets").write_text(
                "import hilog from '@ohos.hilog';\n"
                "@Entry\n"
                "@Component\n"
                "struct ProfilePage {\n"
                "  aboutToAppear() {\n"
                "    hilog.info(0x0000, 'ProfilePage', 'load profile start');\n"
                "    hilog.error(0x0000, 'ProfilePage', 'load profile failed');\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "pages")
            self.run_memory(
                project,
                "learn-business",
                "--payload",
                json.dumps(
                    {
                        "files": [
                            {
                                "file_path": "pages/Profile.ets",
                                "business_summary": "个人资料页，页面进入时加载用户资料。",
                                "business_terms": ["个人资料", "用户资料", "profile", "资料页"],
                                "logs": [
                                    {
                                        "message_template": "load profile failed",
                                        "function": "aboutToAppear",
                                        "level": "error",
                                        "logger": "hilog",
                                        "business_summary": "用户资料加载失败日志。",
                                        "business_terms": ["用户资料加载失败", "资料页空白", "session invalid", "load profile failed"],
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )

            result = self.run_memory(project, "context", "--query", "个人资料页空白，怀疑登录态异常", "--json")
            data = json.loads(result.stdout)

            self.assertEqual(data["followup_focus"], "log")
            self.assertIn("log_search_plan", data)
            self.assertEqual(data["log_search_plan"]["focus"], "log")
            self.assertIn("load profile failed", data["log_search_plan"]["search_terms"])
            self.assertIn("ProfilePage", data["log_search_plan"]["logger_hints"])
            self.assertTrue(data["log_search_plan"]["candidate_log_events"])
