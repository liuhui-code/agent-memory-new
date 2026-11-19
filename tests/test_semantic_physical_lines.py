# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Physical file coordinates, not ECMAScript lexical line-terminator counts."""
import hashlib
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.semantic_ecma import parse_source
from tools.agent_memory_runtime.semantic_models import physical_source_lines
from tools.agent_memory_runtime.semantic_symbol_evidence import load_semantic_source_lines, method_source_text
from tools.agent_memory_runtime.storage import resolve_project, connect

BASE = "export class DocumentStore {\n  label: string = 'Document%slabel'\n  save(value: string): string {\n    return value.trim()\n  }\n}\n"

class SemanticPhysicalLineTests(AgentMemoryTestBase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project'
        self.root.mkdir()
        self.file = self.root / 'DocumentStore.ts'
        self.project = resolve_project(str(self.root), str(self.memory_home(self.root)))

    def test_file_reader_boundaries_and_empty_trailing_lines(self):
        for text, expected in [('', []), ('\n', ['']), ('a\n', ['a']),
                               ('a\n\n', ['a', '']), ('a\rb\r\nc', ['a','b','c']),
                               ('a\u2028b\u2029c', ['a\u2028b\u2029c'])]:
            self.assertEqual(physical_source_lines(text), expected)

    def test_typed_and_evidence_ranges_share_physical_source(self):
        for separator in [' ', '\u2028', '\u2029']:
            for newline in ['\n', '\r\n', '\r']:
                for ending in [True, False]:
                    text = (BASE % separator).replace('\n', newline)
                    if not ending: text = text[:-len(newline)]
                    raw = text.encode()
                    self.file.write_bytes(raw)
                    parsed = parse_source(self.project, self.file, raw, 'TypeScript', False)
                    method = next(e for e in parsed.entities if e.name == 'save')
                    self.assertEqual((method.start_line, method.end_line), (3,5))
                    self.assertEqual(parsed.digest, hashlib.sha256(raw).hexdigest())
                    loaded = load_semantic_source_lines(self.project, ['DocumentStore.ts'])
                    self.assertEqual(method_source_text(method, loaded['DocumentStore.ts']),
                                     '  save(value: string): string {\n    return value.trim()\n  }')

    def test_public_cli_ranges_and_original_excerpt_bytes(self):
        for sep in ['\u2028', '\u2029']:
            source = BASE % sep
            self.file.write_text(source)
            self.run_memory(self.root, 'learn-path', '--path', '.')
            result = json.loads(self.run_memory(self.root, 'context', '--query',
                'Locate DocumentStore.save source.', '--compact', '--json').stdout)
            anchors = result['query_handoff']['code_anchors']
            ranges = [r for a in anchors for r in a.get('source_ranges', []) if r['symbol']=='save']
            self.assertTrue(ranges)
            self.assertTrue(all((r['start_line'],r['end_line']) == (3,5) for r in ranges))
            for anchor in anchors:
                for excerpt in anchor.get('source_excerpts', []):
                    self.assertEqual(excerpt['content'], '\n'.join(physical_source_lines(source)[
                        excerpt['start_line']-1:excerpt['end_line']]))
            with connect(self.project) as conn:
                row = conn.execute("SELECT method_evidence FROM code_symbols WHERE qualified_name='DocumentStore.save'").fetchone()
                self.assertIn('trim', row[0])

    def test_tsx_existing_adapter_uses_the_same_evidence_coordinates(self):
        self.file = self.root / 'DocumentStore.tsx'
        self.file.write_text(BASE % '\u2028')
        self.run_memory(self.root, 'learn-path', '--path', '.')
        with connect(self.project) as conn:
            row = conn.execute("SELECT start_line,end_line,method_evidence FROM code_symbols WHERE qualified_name='DocumentStore.save'").fetchone()
        self.assertEqual(tuple(row[:2]), (3,5))
        self.assertIn('trim', row[2])
        parsed = parse_source(self.project,self.file,self.file.read_bytes(),'TypeScript',False)
        method = next(e for e in parsed.entities if e.name == 'save')
        loaded = load_semantic_source_lines(self.project, ['DocumentStore.tsx'])
        self.assertEqual(method_source_text(method, loaded['DocumentStore.tsx']),
                         '  save(value: string): string {\n    return value.trim()\n  }')
