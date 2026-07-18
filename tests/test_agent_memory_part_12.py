# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import *
from tools.agent_memory_runtime.context_source_excerpt import read_excerpt, safe_source_path


class AgentMemoryRuntimePart12Tests(AgentMemoryTestBase):
    def test_source_excerpt_rejects_paths_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            root.mkdir()
            outside = Path(temp_dir) / "outside.ets"
            outside.write_text("const secret = true\n", encoding="utf-8")
            (root / "external.ets").symlink_to(outside)
            binary = root / "binary.ets"
            binary.write_bytes(b"\x00binary")

            self.assertIsNone(safe_source_path(root.resolve(), "../outside.ets"))
            self.assertIsNone(safe_source_path(root.resolve(), str(outside)))
            self.assertIsNone(safe_source_path(root.resolve(), "external.ets"))
            self.assertEqual(
                {},
                read_excerpt(
                    binary,
                    {"symbol": "Binary", "start_line": 1, "end_line": 1},
                    100,
                ),
            )

    def test_natural_language_noise_does_not_outrank_domain_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            views = project / "features" / "home" / "views"
            views.mkdir(parents=True)
            (views / "ChatItem.ets").write_text(
                "@Component\nstruct ChatItem {\n  build() {}\n}\n",
                encoding="utf-8",
            )
            (views / "MessageBubble.ets").write_text(
                "@Component\n"
                "struct MessageBubble {\n"
                "  StickerOnlyView() { this.StickerView() }\n"
                "  StickerView() { const ephemeralMechanism = 'webm-local-only' }\n"
                "  build() {}\n"
                "}\n",
                encoding="utf-8",
            )
            pages = project / "features" / "home" / "pages"
            pages.mkdir()
            (pages / "ProfilePage.ets").write_text(
                "@Entry\n@Component\nstruct ProfilePage {\n  build() {}\n}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "features")
            result = self.run_memory(
                project,
                "context",
                "--query",
                "A downloaded WebM sticker exists locally but the embedded Web component cannot render it from the generated page.",
                "--compact",
                "--json",
            )
            anchors = json.loads(result.stdout)["query_handoff"]["code_anchors"]

            self.assertEqual(
                "features/home/views/MessageBubble.ets",
                anchors[0]["file_path"],
            )
            self.assertIn(anchors[0]["symbol"], {"StickerOnlyView", "StickerView"})
            self.assertEqual(
                {"StickerOnlyView", "StickerView"},
                {item["symbol"] for item in anchors[0]["source_ranges"]},
            )
            self.assertTrue(
                all(item["start_line"] <= item["end_line"] for item in anchors[0]["source_ranges"])
            )
            self.assertEqual(
                {"start_line": 3, "end_line": 4},
                anchors[0]["read_window"],
            )
            excerpts = anchors[0]["source_excerpts"]
            excerpt_text = "\n".join(item["content"] for item in excerpts)
            self.assertIn("webm-local-only", excerpt_text)
            self.assertTrue(all(item["source"] == "current_worktree" for item in excerpts))
            self.assertNotIn("record_id", anchors[0])
            self.assertNotIn("start_line", anchors[0])
            self.assertNotIn("end_line", anchors[0])
            self.assertLessEqual(json.loads(result.stdout)["output_budget"]["estimated_tokens"], 1500)

            persisted = json.loads(
                (self.project_memory_dir(project) / "runtime" / "last_context.json").read_text(
                    encoding="utf-8"
                )
            )
            persisted_anchor = persisted["query_handoff"]["code_anchors"][0]
            self.assertNotIn("webm-local-only", json.dumps(persisted))
            self.assertNotIn("source_excerpts", persisted_anchor)
            self.assertTrue(persisted_anchor["source_excerpt_metadata"])

    def test_exact_path_segment_prioritizes_distinct_login_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            login = project / "features" / "home" / "pages" / "Login"
            login.mkdir(parents=True)
            for name in ("PhoneNumber", "VerifyCode", "Password"):
                (login / f"{name}.ets").write_text(
                    f"@Component\nstruct {name} {{\n"
                    f"  submit{name}() {{}}\n"
                    f"  build() {{ $r('app.string.login_{name.lower()}_hint') }}\n"
                    "}\n",
                    encoding="utf-8",
                )
            pages = login.parent
            (pages / "Index.ets").write_text(
                "@Component\nstruct Index {\n"
                "  Navigation() {}\n"
                "  build() {}\n"
                "}\n",
                encoding="utf-8",
            )
            chat = project / "features" / "home" / "viewmodel" / "Chat"
            chat.mkdir(parents=True)
            (chat / "ChatDetailViewModel.ets").write_text(
                "class ChatDetailViewModel {\n"
                "  startAppletAbility() {}\n"
                "}\n",
                encoding="utf-8",
            )

            self.run_memory(project, "learn-path", "--path", "features")
            result = self.run_memory(
                project,
                "context",
                "--query",
                "Repeated taps on login actions while authentication is pending can start duplicate requests and conflicting navigation transitions.",
                "--compact",
                "--json",
            )
            anchors = json.loads(result.stdout)["query_handoff"]["code_anchors"]

            self.assertEqual(
                {
                    "features/home/pages/Login/PhoneNumber.ets",
                    "features/home/pages/Login/VerifyCode.ets",
                    "features/home/pages/Login/Password.ets",
                },
                {item["file_path"] for item in anchors[:3]},
            )
            self.assertTrue(all(item["source_ranges"] for item in anchors[:3]))

    def test_log_semantic_fields_enrich_query_handoff(self) -> None:
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
            handoff = data["query_handoff"]
            event = handoff["log_anchors"][0]

            self.assertEqual(event["business_event"], "profile_load_failed")
            self.assertEqual(event["trigger_stage"], "profile_page_about_to_appear")
            self.assertIn("资料页空白", event["symptom_terms"])
            self.assertNotIn("likely_causes", event)
            self.assertIn("entryability", handoff["log_keywords"])
            self.assertIn("session invalid", handoff["log_keywords"])

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
