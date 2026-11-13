# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import re
import tempfile
from pathlib import Path
from agent_memory_test_base import AgentMemoryTestBase, REPO_ROOT
from tools.agent_memory_runtime.ecma_import_lexical import admitted_module_specs


class ImportTraversalLexicalTests(AgentMemoryTestBase):
    def test_public_entry_scope_and_graph(self):
        for protocol_name in ['protocol.json', 'arkts-protocol.json']:
            p = json.loads((REPO_ROOT / 'docs/eval/import-traversal-current' / protocol_name).read_text())
            with self.subTest(protocol=protocol_name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for name, text in p['sources'].items():
                    (root / name).write_text(text)
                self.run_memory(root, 'init')
                out = json.loads(self.run_memory(root, 'learn-entry', '--entry', p['entry'], '--depth', '1', '--json').stdout)
                self.assertEqual(out['files'], p['expected_files'])
                files = json.loads(self.run_memory(root, 'list', '--type', 'code-file', '--limit', '100', '--json').stdout)
                self.assertEqual(sorted(row['file_path'] for row in files), p['expected_files'])
                edges = json.loads(self.run_memory(root, 'list', '--type', 'memory-edge', '--limit', '100', '--json').stdout)
                imports = [row['evidence'] for row in edges if row['relation'] == 'imports']
                self.assertFalse(any(name in edge for name in p['forbidden_files'] for edge in imports))
                if protocol_name == 'arkts-protocol.json':
                    self.assertEqual(set(imports), {f"Entry.ets -> {name}" for name in ['Actual.ets', 'Dynamic.ets', 'Required.ets']})

    def test_unknown_exact_legacy_specs(self):
        pattern = r"(?:from\s+|import\s*\(|require\s*\()\s*['\"]([^'\"]+)['\"]"
        base = "/* from './comment' */\nconst s = `require('./template')`;\nimport x from './real';\n"
        for tail in ['const n=a/b;', 'const re=/x/;', 'const t=`${run()}`;', '/* open', "const s='open"]:
            self.assertEqual(admitted_module_specs(base + tail), re.findall(pattern, base + tail))

    def test_raw_paths_order_duplicates_and_multiline(self):
        text = "\r\nimport { real as alias } from\r\n './dir-name/a';\r\nimport('./dir-name/a'); require(\n './other');\n"
        self.assertEqual(admitted_module_specs(text), ['./dir-name/a', './dir-name/a', './other'])

    def test_public_cycle_and_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Entry.ts').write_text("import { a as b } from './A';\n")
            (root / 'A.ts').write_text("import { b as a } from './Entry';\nconst next = import('./B');\n")
            (root / 'B.ts').write_text("export const b = 2;\n")
            for depth, expected in [(0, ['Entry.ts']), (1, ['A.ts', 'Entry.ts']), (2, ['A.ts', 'B.ts', 'Entry.ts']), (8, ['A.ts', 'B.ts', 'Entry.ts'])]:
                mem = root / ('memory-' + str(depth))
                self.run_memory(root, 'init', memory_home=mem)
                result = json.loads(self.run_memory(root, 'learn-entry', '--entry', 'Entry.ts', '--depth', str(depth), '--json', memory_home=mem).stdout)
                self.assertEqual(result['files'], expected)
