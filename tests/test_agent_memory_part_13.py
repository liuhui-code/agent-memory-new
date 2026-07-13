# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart13Tests(AgentMemoryTestBase):
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
