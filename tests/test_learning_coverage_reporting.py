# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Independent development regressions for public learning coverage reporting."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "agent_memory.py"


class LearningCoverageReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.project = self.home / "project"
        self.project.mkdir()
        self.memory = self.home / "memory"

    def write(self, name: str, content: str) -> None:
        target = self.project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def run_cli(self, command: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), command, "--project", str(self.project),
             "--memory-home", str(self.memory), *args],
            capture_output=True, text=True, timeout=40,
        )

    def successful_json(self, command: str, *args: str) -> dict:
        result = self.run_cli(command, *args, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_mjs_entry_indexes_relative_cjs_and_public_context(self) -> None:
        self.write("launch.mjs", "import { assist } from './helper.cjs';\n"
                   "export function coverageBeacon() {\n"
                   "  console.warn('coverage beacon reached');\n  return assist();\n}\n")
        self.write("helper.cjs", "function assist() { return 42; }\nmodule.exports = { assist };\n")
        data = self.successful_json("learn-entry", "--entry", "launch.mjs", "--depth", "1")
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["files"], ["helper.cjs", "launch.mjs"])
        self.assertEqual(data["parse_stats"]["files_indexed"], 2)
        self.assertEqual(data["parse_stats"]["languages"], {"JavaScript": 2})
        self.assertGreater(data["parse_stats"]["symbols_total"], 0)
        self.assertGreater(data["parse_stats"]["code_logs_total"], 0)
        context = self.successful_json("context", "--query", "coverageBeacon")
        anchors = context["query_handoff"]["code_anchors"]
        self.assertTrue(any(item["file_path"] == "launch.mjs" and
                            item.get("symbol") == "coverageBeacon" for item in anchors))
        self.assertTrue(any(item["file_path"] == "launch.mjs" for item in
                            context["query_handoff"]["log_anchors"]))

    def test_cjs_path_uses_existing_javascript_profile(self) -> None:
        self.write("worker.cjs", "function worker() { console.log('working'); }\n")
        data = self.successful_json("learn-path", "--path", "worker.cjs")
        self.assertEqual(data["parse_stats"]["languages"], {"JavaScript": 1})
        self.assertEqual(data["parse_stats"]["files_indexed"], 1)

    def test_directory_reports_unsupported_files_and_pruned_directories(self) -> None:
        self.write("src/ok.py", "def accepted():\n    return 1\n")
        self.write("src/native.rs", "fn unsupported() {}\n")
        self.write("src/notes.txt", "Not a supported source format.\n")
        self.write("src/node_modules/ignored.js", "function ignored() {}\n")
        self.write("src/generated/ignored.py", "def ignored(): pass\n")
        data = self.successful_json("learn-path", "--path", "src")
        self.assertEqual(data["files"], ["src/ok.py"])
        self.assertEqual(data["parse_stats"]["skipped_by_reason"], {
            "unsupported_extension": 2, "ignored_directory": 2,
        })

    def test_explicit_unsupported_path_fails_before_replace(self) -> None:
        self.write("kept.py", "def coveragePreserved():\n    return 1\n")
        self.write("native.rs", "fn unsupported() {}\n")
        self.successful_json("learn-path", "--path", "kept.py")
        result = self.run_cli("learn-path", "--path", "native.rs", "--replace", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported_extension", result.stderr)
        self.assertIn("native.rs", result.stderr)
        hits = self.successful_json("wiki-search", "--query", "coveragePreserved")
        self.assertIn("kept.py", json.dumps(hits))

    def test_unsupported_only_directory_cannot_replace_existing_index(self) -> None:
        self.write("kept.py", "def kept(): pass\n")
        self.write("unsupported/native.rs", "fn unsupported() {}\n")
        self.successful_json("learn-path", "--path", "kept.py")
        result = self.run_cli("learn-path", "--path", "unsupported", "--replace", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported_extension", result.stderr)
        rows = self.successful_json("list", "--type", "code-file")
        self.assertEqual([row["file_path"] for row in rows], ["kept.py"])

    def test_wiki_index_rejects_unsupported_only_source_before_replace(self) -> None:
        self.write("kept.py", "def kept(): pass\n")
        self.write("unsupported/native.rs", "fn unsupported() {}\n")
        self.successful_json("learn-path", "--path", "kept.py")
        result = self.run_cli("wiki-index", "--source", str(self.project / "unsupported"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported_extension", result.stderr)
        rows = self.successful_json("list", "--type", "code-file")
        self.assertEqual([row["file_path"] for row in rows], ["kept.py"])

    def test_unreadable_directory_blocks_partial_project_replacement(self) -> None:
        import os
        self.write("private/kept.py", "def preservedPrivate(): pass\n")
        self.write("visible.py", "def visible(): pass\n")
        initial = self.run_cli("wiki-index")
        self.assertEqual(initial.returncode, 0, initial.stderr)
        directory = self.project / "private"
        directory.chmod(0)
        try:
            if os.access(directory, os.R_OK):
                self.skipTest("This environment can read directories despite mode 000")
            result = self.run_cli("wiki-index")
        finally:
            directory.chmod(0o700)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unreadable_directory", result.stderr)
        rows = self.successful_json("list", "--type", "code-file")
        self.assertEqual(sorted(row["file_path"] for row in rows),
                         ["private/kept.py", "visible.py"])

    def test_explicit_truly_empty_directory_replacement_still_works(self) -> None:
        self.write("kept.py", "def kept(): pass\n")
        (self.project / "empty").mkdir()
        self.successful_json("learn-path", "--path", "kept.py")
        data = self.successful_json("learn-path", "--path", "empty", "--replace")
        self.assertEqual(data["parse_stats"]["files_indexed"], 0)
        self.assertEqual(data["parse_stats"]["skipped_by_reason"], {})
        self.assertEqual(self.successful_json("list", "--type", "code-file"), [])

    def test_explicit_unsupported_entry_fails_with_reason(self) -> None:
        self.write("native.rs", "fn unsupported() {}\n")
        result = self.run_cli("learn-entry", "--entry", "native.rs", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported_extension", result.stderr)
        self.assertIn("native.rs", result.stderr)

    def test_explicit_ignored_path_fails_with_reason(self) -> None:
        self.write("generated/ignored.py", "def ignored(): pass\n")
        result = self.run_cli("learn-path", "--path", "generated/ignored.py", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ignored_directory", result.stderr)

    def test_existing_javascript_payload_is_preserved(self) -> None:
        self.write("legacy.js", "function legacy() { return 1; }\n")
        data = self.successful_json("learn-path", "--path", "legacy.js")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["files"], ["legacy.js"])
        self.assertEqual(data["mode"], "merge")
        self.assertIn("scope_id", data)
        self.assertIn("summary", data)
        self.assertEqual(data["parse_stats"]["skipped_by_reason"], {})

    def test_extensionless_require_discovers_cjs(self) -> None:
        self.write("main.cjs", "const helper = require('./helper');\nfunction main() {}\n")
        self.write("helper.cjs", "function helper() {}\n")
        data = self.successful_json("learn-entry", "--entry", "main.cjs", "--depth", "1")
        self.assertEqual(data["files"], ["helper.cjs", "main.cjs"])

    def test_ignored_import_is_reported_without_inflating_selected_count(self) -> None:
        self.write("main.js", "import { hidden } from './generated/hidden.js';\nfunction main() {}\n")
        self.write("generated/hidden.js", "function hidden() {}\n")
        data = self.successful_json("learn-entry", "--entry", "main.js", "--depth", "1")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["files"], ["main.js"])
        self.assertEqual(data["parse_stats"]["files_indexed"], 1)
        self.assertEqual(data["parse_stats"]["skipped_by_reason"], {"ignored_directory": 1})

    def test_directory_symlinks_and_outside_files_are_reported(self) -> None:
        self.write("src/main.py", "def main(): pass\n")
        outside = self.home / "external.py"
        outside.write_text("def outside(): pass\n", encoding="utf-8")
        (self.project / "src/outside.py").symlink_to(outside)
        (self.project / "src/linked_dir").symlink_to(self.home, target_is_directory=True)
        data = self.successful_json("learn-path", "--path", "src")
        self.assertEqual(data["files"], ["src/main.py"])
        self.assertEqual(data["parse_stats"]["skipped_by_reason"], {
            "outside_source_root": 1, "symlink_directory": 1,
        })

    def test_javascript_suffix_policy_and_rust_boundary(self) -> None:
        from tools.agent_memory_runtime.source_adapters import source_profile_for
        from tools.agent_memory_runtime.source_path_policy import (
            candidate_language, filter_explicit_language_candidates,
        )
        from tools.agent_memory_runtime.semantic_adapters import adapter_for
        for suffix in ("mjs", "cjs", "MJS", "CJS"):
            with self.subTest(suffix=suffix):
                path = "main." + suffix
                self.assertEqual(source_profile_for(Path(path)).language, "JavaScript")
                self.assertEqual(candidate_language({"file_path": path}), "JavaScript")
                selected = {"file_path": path}
                self.assertEqual(filter_explicit_language_candidates(
                    [selected, {"file_path": "main.py"}], "Find main." + suffix), [selected])
        self.assertIsNone(source_profile_for(Path("native.rs")))
        self.assertIsNone(adapter_for("JavaScript"))
        self.assertIsNone(adapter_for("Rust"))

    def test_index_writer_reports_its_own_rejections(self) -> None:
        from tools.agent_memory_runtime.code_wiki_indexing import write_wiki_index
        from tools.agent_memory_runtime.storage import ensure_initialized, resolve_project
        self.write("main.py", "def main(): pass\n")
        self.write("native.rs", "fn unsupported() {}\n")
        self.write("generated/hidden.py", "def hidden(): pass\n")
        outside = self.home / "outside.py"
        outside.write_text("def outside(): pass\n", encoding="utf-8")
        project = resolve_project(str(self.project), str(self.memory))
        ensure_initialized(project)
        counts = {"unsupported_extension": 2}
        stats = write_wiki_index(project, [self.project / name for name in
            ["main.py", "native.rs", "generated/hidden.py", "missing.py", "generated"]]
            + [outside, self.project], skipped_by_reason=counts)
        self.assertEqual(stats["files_indexed"], 1)
        self.assertEqual(stats["skipped_by_reason"], {
            "unsupported_extension": 3, "ignored_directory": 2,
            "missing_path": 1, "outside_source_root": 1, "not_regular_file": 1,
        })
        self.assertEqual(counts, {"unsupported_extension": 2})

    def test_directory_with_only_unsupported_files_reports_zero_coverage(self) -> None:
        self.write("src/native.rs", "fn unsupported() {}\n")
        data = self.successful_json("learn-path", "--path", "src")
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["parse_stats"]["files_indexed"], 0)
        self.assertEqual(data["parse_stats"]["skipped_by_reason"], {"unsupported_extension": 1})
        self.assertNotIn("Rust", data["parse_stats"]["languages"])

    def test_wiki_index_text_includes_skip_reason(self) -> None:
        self.write("main.py", "def main(): pass\n")
        self.write("native.rs", "fn unsupported() {}\n")
        result = self.run_cli("wiki-index")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unsupported_extension=1", result.stdout)


if __name__ == "__main__":
    unittest.main()
