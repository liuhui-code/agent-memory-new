# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.semantic_adapters import adapter_for
from tools.agent_memory_runtime.storage import resolve_project


SOURCE = '''pub struct Ledger;
impl Ledger {
    pub async fn read_balance(
        &self,
        account: u64,
    ) -> u64 {
        account
    }
}
pub fn current_version() -> u64 { 1 }
'''


class RustSourceContextTests(AgentMemoryTestBase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name) / "rust-fixture"
        self.project.mkdir()
        (self.project / "src").mkdir()
        self.source = self.project / "src/ledger.rs"
        self.source.write_text(SOURCE)
        self.run_memory(self.project, "init")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def learn(self) -> dict:
        return json.loads(self.run_memory(
            self.project, "learn-path", "--path", "src", "--json",
        ).stdout)

    def design(self) -> dict:
        return json.loads(self.run_memory(
            self.project, "design-context", "--query", "Ledger read_balance current_version",
            "--anchor", "src/ledger.rs", "--json",
        ).stdout)

    def rows(self, table: str) -> list[sqlite3.Row]:
        with sqlite3.connect(self.project_memory_dir(self.project) / "memory.db") as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()

    def batch(self, text: str):
        self.source.write_text(text)
        adapter = adapter_for("Rust")
        self.assertIsNotNone(adapter)
        project = resolve_project(str(self.project), str(self.memory_home(self.project)))
        return adapter.index(project, [self.source])

    def test_public_learning_and_design_return_rust_source_anchors(self) -> None:
        learned = self.learn()
        result = self.design()
        anchors = result["current_repository"]["source_anchors"]
        self.assertEqual(1, learned["parse_stats"]["files_indexed"], f"actual design anchors: {anchors}")
        self.assertTrue(any(item["file_path"] == "src/ledger.rs" for item in anchors))
        symbols = self.rows("code_symbols")
        method = next(item for item in symbols if item["qualified_name"] == "Ledger::read_balance")
        self.assertEqual((3, 8), (method["start_line"], method["end_line"]))
        self.assertEqual(hashlib.sha256(SOURCE.encode()).hexdigest(), method["source_digest"])
        self.assertEqual("static", method["evidence_class"])
        self.assertEqual("Ledger", method["owner_name"])
        self.assertEqual("rust-static@1.0", method["semantic_adapter"])
        self.assertIn("source-only", self.rows("code_files")[0]["summary"])
        self.assertFalse(any(item["relation"] == "calls" for item in self.rows("memory_edges")))

    def test_compact_projection_retains_explicit_rust_file_amid_distractors(self) -> None:
        for name in ("a", "b", "c"):
            (self.project / "src" / f"{name}.rs").write_text("pub fn read_balance() {}\n")
        self.learn()
        payload = json.loads(self.run_memory(
            self.project, "design-context", "--query", "read_balance",
            "--anchor", "src/ledger.rs", "--compact", "--json",
        ).stdout)
        self.assertIn("src/ledger.rs", {
            item["file_path"] for item in payload["current_repository"]["source_anchors"]
        })

    def test_comments_strings_and_macro_token_trees_are_not_declarations(self) -> None:
        batch = self.batch('''// fn line_comment() {}
/* fn block_comment() {} /* fn nested_comment() {} */ */
const TEMPLATE: &str = r###"fn raw_string() {}"###;
const BYTE: &[u8] = br#"fn byte_string() {}"#;
const NORMAL: &str = "fn quoted_string() {}";
macro_rules! generate { () => { fn generated() {} }; }
some_macro! { fn invocation_body() {} }
pub fn real<'a>(value: &'a str) -> &'a str {
    let _brace = '}';
    value
}
''')
        self.assertEqual(["real"], [item.name for item in batch.entities])
        self.assertEqual((8, 11), (batch.entities[0].start_line, batch.entities[0].end_line))
        self.assertEqual(["definitions"], batch.capabilities)
        self.assertFalse(batch.relations)
        self.assertTrue(batch.gaps)

    def test_distinct_owners_and_cfg_duplicates_have_distinct_public_ids(self) -> None:
        self.source.write_text('''struct A;
struct B;
impl A { fn read(&self) {} }
impl B { fn read(&self) {} }
#[cfg(unix)]
fn platform() {}
#[cfg(windows)]
fn platform() {}
''')
        self.learn()
        methods = [row for row in self.rows("code_symbols") if row["symbol_type"] == "method"]
        self.assertEqual({"A::read", "B::read"}, {row["qualified_name"] for row in methods})
        symbols = [row for row in self.rows("code_symbols") if "platform" in row["symbol"]]
        self.assertEqual(2, len(symbols))
        self.assertEqual(2, len({row["symbol_key"] for row in symbols}))
        anchors = self.design()["current_repository"]["source_anchors"]
        self.assertEqual(len(anchors), len({row["id"] for row in anchors}))

    def test_inline_module_trait_and_generic_impl_keep_source_scopes(self) -> None:
        batch = self.batch('''mod inner {
    pub trait Readable { fn read(&self) -> u64; }
    pub struct Store<T> { value: T }
    impl<T> Store<T> {
        pub fn get(&self) -> &T { &self.value }
    }
}
''')
        names = {item.qualified_name for item in batch.entities}
        self.assertIn("inner::Readable::read", names)
        self.assertIn("inner::Store<T>::get", names)
        self.assertFalse(batch.relations)

    def test_unbalanced_source_keeps_file_without_inventing_spans(self) -> None:
        self.source.write_text("pub fn incomplete() {\n")
        self.learn()
        self.assertEqual(1, len(self.rows("code_files")))
        self.assertEqual([], self.rows("code_symbols"))

    def test_function_bounds_do_not_truncate_the_generic_impl_owner(self) -> None:
        batch = self.batch('''struct Store<F> { operation: F }
impl<F: Fn() -> u64> Store<F> {
    fn invoke(&self) -> u64 { (self.operation)() }
}
''')
        method = next(item for item in batch.entities if item.kind == "method")
        self.assertEqual("Store<F>::invoke", method.qualified_name)

    def test_crlf_digest_matches_original_bytes_and_remains_queryable(self) -> None:
        data = SOURCE.replace("\n", "\r\n").encode()
        self.source.write_bytes(data)
        self.learn()
        method = next(item for item in self.rows("code_symbols") if item["symbol_type"] == "method")
        self.assertEqual(hashlib.sha256(data).hexdigest(), method["source_digest"])
        result = json.loads(self.run_memory(
            self.project, "context", "--query", "Ledger read_balance", "--compact", "--json",
        ).stdout)
        self.assertEqual("current", result["source_freshness"]["status"])
        self.assertTrue(any(
            row.get("file_path") == "src/ledger.rs"
            for row in result["query_handoff"]["code_anchors"]
        ))

    def test_invalid_utf8_does_not_become_a_different_valid_declaration(self) -> None:
        self.source.write_bytes(b"pub fn misleading_\xff() {}\n")
        self.learn()
        self.assertEqual(1, len(self.rows("code_files")))
        self.assertEqual([], self.rows("code_symbols"))

    def test_function_pointer_and_header_without_parameters_are_not_functions(self) -> None:
        batch = self.batch("type Callback = fn(u64) -> u64;\nfn missing_parameters {}\nfn real() {}\n")
        self.assertEqual(["real"], [item.name for item in batch.entities])

    def test_deeply_nested_modules_respect_the_static_scope_budget(self) -> None:
        batch = self.batch("mod nested { " * 40 + "fn deep() {}" + " }" * 40)
        self.assertFalse(any(item.name.endswith("deep") for item in batch.entities))
        self.assertTrue(batch.gaps)

    def test_same_line_conditional_definitions_keep_distinct_physical_identities(self) -> None:
        batch = self.batch("#[cfg(unix)] fn platform() {} #[cfg(windows)] fn platform() {}\n")
        self.assertEqual(2, len(batch.entities))
        self.assertEqual(2, len({item.key for item in batch.entities}))
        self.assertEqual(2, len({item.name for item in batch.entities}))
        self.assertEqual({"platform"}, {item.qualified_name for item in batch.entities})

    def test_changed_source_is_blocked_in_context_and_relearned_without_duplicates(self) -> None:
        self.learn()
        original = self.rows("code_symbols")
        self.source.write_text(SOURCE.replace("current_version", "new_version"))
        result = json.loads(self.run_memory(
            self.project, "context", "--query", "Ledger read_balance current_version",
            "--compact", "--json",
        ).stdout)
        self.assertIn("src/ledger.rs", result["source_freshness"]["stale_paths"])
        self.assertFalse(any(
            row.get("file_path") == "src/ledger.rs"
            for row in result["query_handoff"]["code_anchors"]
        ))
        self.learn()
        self.learn()
        current = self.rows("code_symbols")
        self.assertEqual(len(original), len(current))
        self.assertFalse(any("current_version" in row["symbol"] for row in current))
        self.assertTrue(any("new_version" in row["symbol"] for row in current))
