# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart12Tests(AgentMemoryTestBase):
    def test_analyze_runtime_log_reflect_template_carries_runtime_evidence_feedback(self) -> None:
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
                                "logs": [
                                    {
                                        "message_template": "load profile start",
                                        "function": "aboutToAppear",
                                        "level": "info",
                                        "logger": "hilog",
                                        "business_summary": "用户资料加载开始日志。",
                                        "business_terms": ["资料加载开始"],
                                        "business_event": "profile_load_started",
                                        "trigger_stage": "profile_page_about_to_appear",
                                        "symptom_terms": ["页面进入后开始加载"],
                                        "likely_causes": [],
                                        "process_hint": "EntryAbility",
                                        "neighbor_terms": ["load profile failed", "session invalid"],
                                    },
                                    {
                                        "message_template": "load profile failed",
                                        "function": "aboutToAppear",
                                        "level": "error",
                                        "logger": "hilog",
                                        "business_summary": "用户资料加载失败日志。",
                                        "business_terms": ["用户资料加载失败", "资料页空白", "session invalid"],
                                        "business_event": "profile_load_failed",
                                        "trigger_stage": "profile_page_about_to_appear",
                                        "symptom_terms": ["资料页空白", "登录后没数据"],
                                        "likely_causes": ["session invalid", "401"],
                                        "process_hint": "EntryAbility",
                                        "neighbor_terms": ["load profile start", "session invalid", "navigate login"],
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )

            runtime_log = project / "profile-feedback.log"
            runtime_log.write_text(
                "2026-06-03T10:21:10.100Z pid=2001 tid=3002 EntryAbility I ProfilePage: load profile start route=pages/Profile request_id=req-1 session_id=sess-9\n"
                "2026-06-03T10:21:13.200Z pid=2001 tid=3002 EntryAbility E ProfilePage: load profile failed code=401 reason=session_invalid request_id=req-1 session_id=sess-9\n"
                "2026-06-03T10:21:13.300Z pid=2001 tid=3002 EntryAbility W SessionManager: session invalid session_id=sess-9\n",
                encoding="utf-8",
            )

            result = self.run_memory(
                project,
                "analyze-runtime-log",
                "--query",
                "个人资料页空白，怀疑登录态异常",
                "--log-file",
                str(runtime_log),
                "--json",
            )
            data = json.loads(result.stdout)
            reflect_payload = data["reflect_payload_template"]

            self.assertEqual(reflect_payload["experience_type"], "procedure_experience")
            self.assertIn("candidate_chain", reflect_payload["evidence"])
            self.assertIn("top_slice", reflect_payload["evidence"])
            self.assertIn("dominant runtime slice", reflect_payload["repair_action"].lower())
            self.assertIn("session invalid", " ".join(reflect_payload["what_worked"]).lower())
            self.assertIsInstance(reflect_payload["misleading_followup_terms"], list)

    def test_log_semantic_fields_enrich_log_search_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Profile.ets").write_text(
                "import hilog from '@ohos.hilog';\n"
                "@Entry\n"
                "@Component\n"
                "struct ProfilePage {\n"
                "  aboutToAppear() {\n"
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
                                "logs": [
                                    {
                                        "message_template": "load profile failed",
                                        "function": "aboutToAppear",
                                        "level": "error",
                                        "logger": "hilog",
                                        "business_summary": "用户资料加载失败日志。",
                                        "business_terms": ["用户资料加载失败", "资料页空白"],
                                        "business_event": "profile_load_failed",
                                        "trigger_stage": "profile_page_about_to_appear",
                                        "symptom_terms": ["资料页空白", "登录后没数据"],
                                        "likely_causes": ["session invalid", "401", "profile api failed"],
                                        "process_hint": "EntryAbility",
                                        "neighbor_terms": ["load profile start", "session invalid"],
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )

            result = self.run_memory(project, "context", "--query", "登录后资料页空白", "--json")
            data = json.loads(result.stdout)
            plan = data["log_search_plan"]
            event = plan["candidate_log_events"][0]

            self.assertEqual(event["business_event"], "profile_load_failed")
            self.assertEqual(event["trigger_stage"], "profile_page_about_to_appear")
            self.assertIn("资料页空白", event["symptom_terms"])
            self.assertIn("session invalid", event["likely_causes"])
            self.assertIn("EntryAbility", plan["process_hints"])
            self.assertIn("session invalid", plan["search_terms"])

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
