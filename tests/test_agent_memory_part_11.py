# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *


class AgentMemoryRuntimePart11Tests(AgentMemoryTestBase):
    def test_analyze_runtime_log_builds_bounded_slices_and_episode_candidate(self) -> None:
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
                                        "message_template": "load profile failed",
                                        "function": "aboutToAppear",
                                        "level": "error",
                                        "logger": "hilog",
                                        "business_summary": "用户资料加载失败日志。",
                                        "business_terms": ["用户资料加载失败", "session invalid", "load profile failed"],
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )

            runtime_log = project / "profile-runtime.log"
            runtime_log.write_text(
                "06-03 10:21:10.100 EntryAbility I ProfilePage: load profile start\n"
                "06-03 10:21:11.000 EntryAbility I ApiClient: request /profile\n"
                "06-03 10:21:13.200 EntryAbility E ProfilePage: load profile failed code=401\n"
                "06-03 10:21:13.300 EntryAbility W SessionManager: session invalid\n"
                "06-03 10:21:15.100 EntryAbility I Router: navigate login\n",
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

            self.assertEqual(data["log_search_plan"]["focus"], "log")
            self.assertGreaterEqual(data["normalized_event_count"], 5)
            self.assertTrue(data["matched_events"])
            self.assertTrue(data["slices"])
            self.assertIn("load profile failed", " ".join(data["slices"][0]["excerpt"]))
            self.assertIn("session invalid", " ".join(data["slices"][0]["excerpt"]))
            self.assertIn("load profile failed", " ".join(data["runtime_episode_candidate"]["dominant_signals"]))
            self.assertTrue(data["session_candidates"])
            self.assertIn("reflect_payload_template", data)
            self.assertEqual(data["reflect_payload_template"]["task_type"], "diagnosis")
            self.assertEqual(data["reflect_payload_template"]["experience_type"], "procedure_experience")
            self.assertIn("session invalid", " ".join(data["reflect_payload_template"]["useful_followup_terms"]))

    def test_analyze_runtime_log_extracts_structured_fields_and_chain(self) -> None:
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
                                        "business_terms": ["资料加载开始", "profile start"],
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
                                        "business_terms": ["用户资料加载失败", "资料页空白", "session invalid", "load profile failed"],
                                        "business_event": "profile_load_failed",
                                        "trigger_stage": "profile_page_about_to_appear",
                                        "symptom_terms": ["资料页空白", "登录后没数据"],
                                        "likely_causes": ["session invalid", "401", "profile api failed"],
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

            runtime_log = project / "profile-structured.log"
            runtime_log.write_text(
                "2026-06-03T10:21:10.100Z pid=2001 tid=3002 EntryAbility I ProfilePage: load profile start route=pages/Profile request_id=req-1 session_id=sess-9\n"
                "2026-06-03T10:21:11.000Z pid=2001 tid=3002 EntryAbility I ApiClient: request /profile request_id=req-1\n"
                "2026-06-03T10:21:13.200Z pid=2001 tid=3002 EntryAbility E ProfilePage: load profile failed code=401 reason=session_invalid request_id=req-1 session_id=sess-9\n"
                "2026-06-03T10:21:13.300Z pid=2001 tid=3002 EntryAbility W SessionManager: session invalid session_id=sess-9\n"
                "2026-06-03T10:21:15.100Z pid=2001 tid=3002 EntryAbility I Router: navigate login route=pages/Login request_id=req-1\n",
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

            first_event = data["matched_events"][0]
            self.assertEqual(first_event["process"], "EntryAbility")
            self.assertEqual(first_event["error_code"], "401")
            self.assertEqual(first_event["request_id"], "req-1")
            self.assertEqual(first_event["session_id"], "sess-9")
            self.assertTrue(any(item["route"] == "pages/Profile" for item in data["matched_events"]))

            self.assertIn("candidate_chain", data["runtime_episode_candidate"])
            self.assertTrue(data["runtime_episode_candidate"]["candidate_chain"])
            self.assertIn("session_invalid", " ".join(data["runtime_episode_candidate"]["candidate_chain"]).lower())
            self.assertIn("chain_confidence", data["runtime_episode_candidate"])
            self.assertGreater(data["runtime_episode_candidate"]["chain_confidence"], 0.0)

            self.assertIn("log_improvement_suggestions", data)
            self.assertTrue(data["log_improvement_suggestions"])
            self.assertIn("decision checkpoints", data["log_improvement_suggestions"][0]["why"])

    def test_usage_sample_auto_records_query_runtime_and_governance_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Profile.ets").write_text(
                "import hilog from '@ohos.hilog';\n"
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
                                        "message_template": "load profile failed",
                                        "function": "aboutToAppear",
                                        "level": "error",
                                        "logger": "hilog",
                                        "business_summary": "用户资料加载失败日志。",
                                        "business_terms": ["资料页空白", "load profile failed", "session invalid"],
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )

            self.run_memory(project, "context", "--query", "个人资料页空白，怀疑登录态异常", "--json")
            runtime_log = project / "runtime.log"
            runtime_log.write_text(
                "06-03 10:21:10.100 EntryAbility I ProfilePage: load profile start\n"
                "06-03 10:21:13.200 EntryAbility E ProfilePage: load profile failed code=401\n"
                "06-03 10:21:13.300 EntryAbility W SessionManager: session invalid\n",
                encoding="utf-8",
            )
            self.run_memory(
                project,
                "analyze-runtime-log",
                "--query",
                "个人资料页空白，怀疑登录态异常",
                "--log-file",
                str(runtime_log),
                "--json",
            )
            self.run_memory(project, "maintain-plan", "--json")

            sample = json.loads(self.usage_sample_path(project).read_text(encoding="utf-8"))
            self.assertIn("context", sample["commands"])
            self.assertIn("analyze-runtime-log", sample["commands"])
            self.assertIn("maintain-plan", sample["commands"])
            self.assertGreaterEqual(sample["query_rounds"], 1)
            self.assertIn("log", sample["followup_focuses"])
            self.assertTrue(sample["runtime_log"]["used"])
            self.assertGreaterEqual(sample["runtime_log"]["matched_event_count"], 1)
            self.assertTrue(sample["governance"]["used"])
            self.assertIn("commands:", sample["auto_summary"])
            self.assertIn("dominant runtime signals", sample["auto_summary"])

    def test_reflect_auto_merges_recent_usage_sample(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "pages").mkdir()
            (project / "pages" / "Profile.ets").write_text(
                "import hilog from '@ohos.hilog';\n"
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
                                        "message_template": "load profile failed",
                                        "function": "aboutToAppear",
                                        "level": "error",
                                        "logger": "hilog",
                                        "business_summary": "用户资料加载失败日志。",
                                        "business_terms": ["资料页空白", "load profile failed", "session invalid"],
                                        "business_event": "profile_load_failed",
                                        "trigger_stage": "profile_page_about_to_appear",
                                        "symptom_terms": ["资料页空白"],
                                        "likely_causes": ["session invalid", "401"],
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
            runtime_log = project / "runtime.log"
            runtime_log.write_text(
                "06-03 10:21:10.100 EntryAbility I ProfilePage: load profile start\n"
                "06-03 10:21:13.200 EntryAbility E ProfilePage: load profile failed code=401 reason=session_invalid\n"
                "06-03 10:21:13.300 EntryAbility W SessionManager: session invalid\n",
                encoding="utf-8",
            )
            self.run_memory(
                project,
                "analyze-runtime-log",
                "--query",
                "个人资料页空白，怀疑登录态异常",
                "--log-file",
                str(runtime_log),
                "--json",
            )

            self.run_memory(
                project,
                "reflect",
                "--task",
                "诊断个人资料页空白",
                "--lesson",
                "先看 runtime log 的 dominant slice，再回到代码日志锚点确认。",
            )

            reflections = self.list_records(project, "reflection")
            latest = reflections[0]
            self.assertEqual(latest["task_type"], "diagnosis")
            self.assertEqual(latest["experience_type"], "procedure_experience")
            self.assertGreaterEqual(latest["query_rounds"], 1)
            self.assertEqual(latest["useful_followup_focus"], "log")
            self.assertIn("session invalid", json.loads(latest["useful_followup_terms"]))
            self.assertIn("candidate_chain", latest["evidence"])
            self.assertTrue(latest["repair_action"])

            sample = json.loads(self.usage_sample_path(project).read_text(encoding="utf-8"))
            self.assertTrue(sample["reflection_written"])
            self.assertTrue(sample["closed_at"])

    def test_analyze_runtime_log_can_recommend_correction_experience(self) -> None:
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
                                        "symptom_terms": ["资料页空白"],
                                        "likely_causes": ["session invalid", "401"],
                                        "process_hint": "EntryAbility",
                                        "neighbor_terms": ["session invalid"],
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "--json",
            )

            runtime_log = project / "profile-correction.log"
            runtime_log.write_text(
                "06-03 10:21:13.200 EntryAbility E ProfilePage: load profile failed code=401\n"
                "06-03 10:21:13.300 EntryAbility W SessionManager: session invalid\n",
                encoding="utf-8",
            )

            result = self.run_memory(
                project,
                "analyze-runtime-log",
                "--query",
                "之前怀疑是 route 问题，现在想纠正判断",
                "--log-file",
                str(runtime_log),
                "--json",
            )
            data = json.loads(result.stdout)

            reflect_payload = data["reflect_payload_template"]
            self.assertEqual(reflect_payload["experience_type"], "correction_experience")
            self.assertTrue(reflect_payload["what_failed"])
            self.assertIn("old_hypothesis", reflect_payload)
            self.assertIn("runtime evidence", reflect_payload["reasoning_summary"].lower())
            self.assertIn("route", " ".join(reflect_payload["misleading_followup_terms"]).lower())
            self.assertIn("candidate_chain", reflect_payload["evidence"])
            self.assertIn("dominant runtime slice", reflect_payload["repair_action"].lower())
