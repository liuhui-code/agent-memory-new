# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart09Tests(AgentMemoryTestBase):
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
