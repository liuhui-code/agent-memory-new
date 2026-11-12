# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Independent development fixtures for suffix candidate equivalence and cost."""
from __future__ import annotations

import itertools
import json
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from tools.agent_memory_runtime.code_wiki_edge_candidates import add_suffix_rows, path_has_suffix

ROOT = Path(__file__).resolve().parents[1]


def original_path_has_suffix(file_path: str, suffixes: set[str]) -> bool:
    normalized = file_path.lower()
    return normalized in suffixes or any(normalized.endswith(f"/{suffix}") for suffix in suffixes)


class CountingSet(set):
    def __init__(self, values):
        super().__init__(values)
        self.yielded = 0
        self.lookups = 0

    def __iter__(self):
        for item in super().__iter__():
            self.yielded += 1
            yield item

    def __contains__(self, item):
        self.lookups += 1
        return super().__contains__(item)


class PathSuffixCandidatesTests(unittest.TestCase):
    def test_boundary_case_unicode_and_empty_contract(self):
        cases = [
            ("src/FeatureTest.TS", {"featuretest.ts"}, True),
            ("src/FeatureTest.TS", {"FeatureTest.TS"}, False),
            ("src/prefixfeaturetest.ts", {"featuretest.ts"}, False),
            ("src/tests/feature.ts", {"tests/feature.ts"}, True),
            ("src/othertests/feature.ts", {"tests/feature.ts"}, False),
            ("src/tests/feature.ts", {"src/tests/feature.ts"}, True),
            ("src\\tests\\feature.ts", {"feature.ts"}, False),
            ("src//feature.ts", {"/feature.ts"}, True),
            ("/feature.ts", {"feature.ts"}, True),
            ("src/../feature.ts", {"../feature.ts"}, True),
            ("src/./feature.ts", {"./feature.ts"}, True),
            ("src/FEATURE.TS/", {"feature.ts"}, False),
            ("src/", {""}, True), ("", {""}, True), ("src", {""}, False),
            ("/", {"/"}, True), ("//", {"/"}, True), ("", set(), False),
            ("src/İ.TS", {"i\u0307.ts"}, True), ("src/İ.TS", {"i.ts"}, False),
            ("src/Σ.TS", {"σ.ts"}, True), ("src/ß.ts", {"ss.ts"}, False),
            ("src/É.ts", {"e\u0301.ts"}, False),
            ("目录/重复/测试.ts", {"重复/测试.ts"}, True),
            ("src/🌟.ts", {"🌟.ts"}, True), ("a/\x00.ts", {"\x00.ts"}, True),
        ]
        for path, suffixes, expected in cases:
            with self.subTest(path=path, suffixes=suffixes):
                self.assertEqual(expected, original_path_has_suffix(path, suffixes))
                self.assertEqual(expected, path_has_suffix(path, suffixes))

    def test_exhaustive_short_paths_and_seeded_nested_paths_match_original(self):
        alphabet = ["a", "A", "/", "İ", "\\"]
        words = [""] + ["".join(x) for n in range(1, 4) for x in itertools.product(alphabet, repeat=n)]
        for path in words:
            for suffix in words:
                self.assertEqual(original_path_has_suffix(path, {suffix}), path_has_suffix(path, {suffix}), (path, suffix))
        rng = random.Random(720914)
        pieces = ["", "src", "..", ".", "Ünit", "测试", "İ", "Σ", "ß", "🌟", "é", "e\u0301", "\\", "null\x00"]
        for _ in range(3000):
            path = "/".join(rng.choices(pieces, k=rng.randint(1, 9))) + rng.choice(["", ".ts", ".TEST.py"])
            suffixes = {"/".join(rng.choices(pieces, k=rng.randint(1, 4))).lower() for _ in range(rng.randint(0, 20))}
            if rng.random() < 0.5:
                suffixes.add(path[rng.randrange(len(path) + 1):].lower())
            self.assertEqual(original_path_has_suffix(path, suffixes), path_has_suffix(path, suffixes), (path, suffixes))

    def test_invalid_outer_arguments_keep_exception_types(self):
        for path, suffixes in [(None, {"a"}), (1, set()), (Path("a"), set()), ("a", None)]:
            with self.subTest(path=path, suffixes=suffixes):
                try:
                    original_path_has_suffix(path, suffixes)
                except Exception as exc:
                    with self.assertRaises(type(exc)):
                        path_has_suffix(path, suffixes)
                else:
                    self.fail("Fixture must exercise an exception")

    def test_suffix_work_does_not_grow_with_number_of_suffixes(self):
        for count in [32, 4096, 32768]:
            suffixes = CountingSet(f"unrelated{i}.ts" for i in range(count))
            self.assertFalse(path_has_suffix("src/nested/unit/absent.ts", suffixes))
            self.assertEqual(0, suffixes.yielded)
            self.assertLessEqual(suffixes.lookups, 4)

    def test_fts_case_and_path_filters_preserve_project_and_existing_rows(self):
        with sqlite3.connect(":memory:") as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("CREATE TABLE code_files (id INTEGER PRIMARY KEY, project_id TEXT, file_path TEXT, language TEXT)")
            conn.execute("CREATE VIRTUAL TABLE code_file_fts USING fts5(file_path, project_id UNINDEXED)")
            paths = ["src/Signal.test.TS", "src/prefixSignal.test.ts", "src/nested/Signal.test.ts", "src/othernested/Signal.test.ts", "unrelated.ts"]
            for i, path in enumerate(paths, 1):
                conn.execute("INSERT INTO code_files VALUES (?, 'p', ?, 'TypeScript')", (i, path))
                conn.execute("INSERT INTO code_file_fts(rowid, file_path, project_id) VALUES (?, ?, 'p')", (i, path))
            conn.execute("INSERT INTO code_files VALUES (99, 'other', 'Signal.test.ts', 'TypeScript')")
            conn.execute("INSERT INTO code_file_fts(rowid, file_path, project_id) VALUES (99, 'Signal.test.ts', 'other')")
            selected = {5: conn.execute("SELECT * FROM code_files WHERE id = 5").fetchone()}
            add_suffix_rows(conn, "p", {"SIGNAL.TEST.TS"}, selected)
            self.assertEqual({1, 3, 4, 5}, set(selected))
            nested = {}
            add_suffix_rows(conn, "p", {"nested/signal.test.ts"}, nested)
            self.assertEqual({3}, set(nested))
            before = dict(selected)
            conn.execute("DROP TABLE code_file_fts")
            with self.assertRaises(sqlite3.OperationalError):
                add_suffix_rows(conn, "p", {"signal.test.ts"}, selected)
            self.assertEqual(before, selected)

    def test_public_scoped_relearn_keeps_test_relation_and_query_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            memory = Path(tmp) / "memory"
            files = {
                "package.json": "{}\n",
                "feature-a/package.json": "{}\n", "feature-b/package.json": "{}\n",
                "feature-a/src/Signal.ts": "export function emitSignal() { return 1; }\n",
                "feature-a/test/Signal.test.ts": "export function verifySignal() { return 1; }\n",
                "feature-a/test/prefixSignal.test.ts": "export function prefixSignal() { return 1; }\n",
                "feature-b/src/Signal.ts": "export function emitOtherSignal() { return 2; }\n",
                "feature-b/test/Signal.test.ts": "export function verifyOtherSignal() { return 2; }\n",
                "目录/Ünit.ts": "export function unicodeSignal() { return 3; }\n",
            }
            for name, content in files.items():
                path = project / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            def run(*args):
                result = subprocess.run([sys.executable, str(ROOT / "tools/agent_memory.py"), *args, "--project", str(project), "--memory-home", str(memory), "--json"], capture_output=True, text=True, timeout=40)
                self.assertEqual(0, result.returncode, result.stderr)
                return json.loads(result.stdout)
            run("learn-path", "--path", ".")
            run("learn-path", "--path", "feature-a/src/Signal.ts")
            code_files = {int(row["id"]): row["file_path"] for row in run("list", "--type", "code-file")}
            pairs = {(code_files[int(row["source_id"])], code_files[int(row["target_id"])]) for row in run("list", "--type", "memory-edge") if row["relation"] == "tested_by"}
            self.assertEqual({("feature-a/src/Signal.ts", "feature-a/test/Signal.test.ts"), ("feature-b/src/Signal.ts", "feature-b/test/Signal.test.ts")}, pairs)
            handoff = run("context", "--query", "emitSignal")["query_handoff"]
            self.assertTrue(any(row["file_path"] == "feature-a/src/Signal.ts" and row.get("symbol") == "emitSignal" for row in handoff["code_anchors"]))


if __name__ == "__main__":
    unittest.main()
