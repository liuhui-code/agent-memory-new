# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""File recall hints require code, not examples embedded in text."""
import json
from pathlib import Path
import tempfile
import unittest
from agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.arkts_behavior_markers import extract_arkts_behavior_markers

SCAN = 'if (this.entries.size > 1) { for (const [key, value] of this.entries) { if (value.updatedAt < oldest) { this.entries.delete(key) } } }'

class CacheMarkerLexicalTests(unittest.TestCase):
    def marker(self, source):
        return 'cacheeviction' in extract_arkts_behavior_markers(source)

    def test_real_scan_and_comments(self):
        self.assertTrue(self.marker(SCAN))
        self.assertTrue(self.marker('// explanatory text\n' + SCAN))
        self.assertFalse(self.marker('/* ' + SCAN + ' */'))

    def test_strings_and_plain_templates_are_not_code(self):
        for quote in ('"', "'", '`'):
            with self.subTest(quote=quote):
                self.assertFalse(self.marker('return ' + quote + SCAN + quote))

    def test_literal_cannot_supply_one_missing_operation(self):
        self.assertFalse(self.marker(SCAN.replace('this.entries.delete(key)', 'note("this.entries.delete(key)")')))
        self.assertFalse(self.marker(SCAN.replace('value.updatedAt < oldest', 'value.rank < minimum') + '; note("updatedAt")'))

    def test_unknown_lexical_forms_retain_legacy_hint(self):
        for prefix in ('const r = /"/;\n', 'const t = `${compute()}`;\n', 'const bad = "'):
            with self.subTest(prefix=prefix):
                self.assertTrue(self.marker(prefix + SCAN))

class CacheMarkerPublicTests(AgentMemoryTestBase):
    def test_real_context_excludes_literal_scan_but_explicit_identity_survives(self):
        protocol = json.loads((Path(__file__).parents[1] / 'docs/releases/cache-marker-lexical-20261118/protocol.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for name, source in protocol['sources'].items():
                path = project / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source)
            self.run_memory(project, 'learn-path', '--path', 'src')
            edges = self.list_records(project, 'memory-edge')
            for name, query in protocol['queries']:
                output = json.loads(self.run_memory(project, 'context', '--query', query, '--json').stdout)
                paths = [item['file_path'] for item in output['query_handoff']['code_anchors']]
                if name == 'scan':
                    self.assertEqual(paths, ['src/PruneEngine.ets'])
                else:
                    self.assertIn('src/ReferenceText.ets', paths)
            self.assertEqual(edges, self.list_records(project, 'memory-edge'))
