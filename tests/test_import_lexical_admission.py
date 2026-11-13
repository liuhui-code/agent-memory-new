# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from agent_memory_test_base import AgentMemoryTestBase, REPO_ROOT
from tools.agent_memory_runtime.ecma_import_lexical import admitted_import_matches
from tools.agent_memory_runtime.semantic_ecma import IMPORT_RE, DEFAULT_IMPORT_RE


class ImportLexicalAdmissionTests(AgentMemoryTestBase):
    def test_public_call_identity(self):
        protocol = json.loads((REPO_ROOT / 'docs/eval/import-lexical-current/protocol.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, source in protocol['sources'].items():
                (root / name).write_text(source)
            self.run_memory(root, 'init')
            self.run_memory(root, 'learn-path', '--path', '.')
            symbols = json.loads(self.run_memory(root, 'list', '--type', 'code-symbol', '--limit', '100', '--json').stdout)
            edges = json.loads(self.run_memory(root, 'list', '--type', 'memory-edge', '--limit', '100', '--json').stdout)
            names = {row['id']: row['qualified_name'] for row in symbols}
            calls = {(names[e['source_id']], names[e['target_id']]) for e in edges if e['relation'] == 'calls' and e['source_type'] == e['target_type'] == 'code_symbol'}
            self.assertIn(tuple(protocol['expected_named_call']), calls)
            self.assertIn(tuple(protocol['expected_legacy_default_call']), calls)
            self.assertFalse({source for source, _ in calls} & set(protocol['forbidden_call_sources']))

    def test_raw_capture_and_offsets(self):
        source = '''/* multiline\nimport { fake } from './bad'\n*/
const guide = `\nimport ghost from './bad'\n`;
\n  import { real as local, other } from './space-name/path'
import Default from "./default-path";
'''
        groups = admitted_import_matches(source, (IMPORT_RE, DEFAULT_IMPORT_RE))
        self.assertEqual([m.groups() for m in groups[0]], [(' real as local, other ', './space-name/path')])
        self.assertEqual([m.groups() for m in groups[1]], [('Default', './default-path')])
        for group in groups:
            for match in group:
                self.assertEqual(source[match.start():match.end()], match.group())

    def test_multiline_and_crlf_preserve_raw_groups(self):
        for newline in ['\n', '\r\n']:
            source = newline.join(['', '  import {', '    real as local, other', '  } from "./path-with-dash/mod"', 'import Default from "./default"'])
            actual = admitted_import_matches(source, (IMPORT_RE, DEFAULT_IMPORT_RE))
            for pattern, matches in zip((IMPORT_RE, DEFAULT_IMPORT_RE), actual):
                self.assertEqual([(m.span(), m.groups()) for m in matches], [(m.span(), m.groups()) for m in pattern.finditer(source)])

    def test_unknown_is_exact_legacy_matches(self):
        base = "/*\nimport { fake as alias } from './bad'\n*/\nimport TrueName from './real'\n"
        for extra in ['const n = a / b;', 'const x = /ab/;', 'const x = `${value}`;', '/* unfinished', "const x = 'unfinished"]:
            source = base + extra
            with self.subTest(extra=extra):
                actual = admitted_import_matches(source, (IMPORT_RE, DEFAULT_IMPORT_RE))
                for pattern, matches in zip((IMPORT_RE, DEFAULT_IMPORT_RE), actual):
                    self.assertEqual([(m.span(), m.groups()) for m in matches], [(m.span(), m.groups()) for m in pattern.finditer(source)])
