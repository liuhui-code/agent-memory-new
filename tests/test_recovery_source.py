# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_recovery_source import parse_recovery_source

D = Path(__file__).parents[1] / 'docs/evidence/recovery-role-feasibility'
P = json.loads((D / 'protocol.json').read_text())
REGISTRY, STORE = P['sources'].values()
SAME = next(iter(P['families'][1]['sources'].values()))


class RecoverySourceTests(unittest.TestCase):
    def test_fixed_sources_and_fourteen_negatives(self):
        self.assertEqual(parse_recovery_source(REGISTRY)['roles'], ['registry'])
        self.assertEqual(parse_recovery_source(STORE)['roles'], ['store'])
        for case in P['source_negative_controls']:
            with self.subTest(case=case['id']):
                self.assertEqual(case['witness'], 'unknown')
                self.assertIsNone(parse_recovery_source(case['source']))

    def test_same_owner_and_other_owner(self):
        parsed = parse_recovery_source(SAME)
        self.assertEqual(parsed['roles'], ['registry', 'store'])
        self.assertEqual(parsed['owner'], 'SessionRegistryStore')
        changed = SAME.replace('SessionRegistryStore', 'OtherRegistryStore')
        self.assertEqual(parse_recovery_source(changed)['owner'], 'OtherRegistryStore')
        self.assertIsNone(parse_recovery_source(REGISTRY + STORE))

    def test_source_spelling_and_exact_component(self):
        for owner in ('Registry', 'registry', 'RegistryLike'):
            self.assertEqual(parse_recovery_source(REGISTRY.replace('SessionRegistry', owner))['owner'], owner)
        for owner in ('Preregistry', 'Registries', 'Registryish'):
            self.assertIsNone(parse_recovery_source(REGISTRY.replace('SessionRegistry', owner)))
        for method in ('sync', 'Sync', 'syncData'):
            self.assertEqual(parse_recovery_source(STORE.replace('syncSessions', method))['methods'][0]['name'], method)
        self.assertIsNone(parse_recovery_source(STORE.replace('syncSessions', 'synchronize')))

    def test_offsets_lines_original_crlf(self):
        for source in (REGISTRY, REGISTRY.replace('\n', '\r\n'), REGISTRY.replace('\n', '\r')):
            parsed = parse_recovery_source(source)
            self.assertEqual((parsed['class_start'], parsed['class_end']), (1, 11))
            self.assertEqual(source[parsed['class_start_offset']:parsed['class_end_offset']], source.rstrip())
            field = parsed['fields'][0]
            self.assertEqual(source[field['start_offset']:field['end_offset']], 'private repository: SessionRepository = new NetworkSessionRepository()')
            self.assertEqual((field['start_line'], field['end_line']), (2, 2))
            method = parsed['methods'][0]
            self.assertTrue(source[method['start_offset']:method['end_offset']].startswith('chooseRepository('))
            self.assertEqual((method['start_line'], method['end_line']), (4, 10))
        state = parse_recovery_source(STORE)['fields'][0]
        self.assertEqual(STORE[state['start_offset']:state['end_offset']], '@State sessions: SessionRecord[] = []')

    def test_duplicates_shadow_missing(self):
        cases = [
            STORE.replace('  private repository:', '  private repository: SessionRepository\n  private repository:'),
            STORE.replace('const loaded', 'const repository').replace('= loaded', '= repository'),
            SAME.replace('const loaded', 'const online').replace('= loaded', '= online'),
            REGISTRY.replace('NetworkSessionRepository', 'chooseRepository'),
            STORE.replace('  private repository: SessionRepository\n', ''),
            STORE.replace('@State sessions', '@State repository'),
            STORE.replace('private repository', 'private syncSessions'),
        ]
        for source in cases:
            with self.subTest(source=source):
                self.assertIsNone(parse_recovery_source(source))

    def test_imports_unknown_and_whole_file(self):
        self.assertTrue(parse_recovery_source("import { SessionRepository } from './SessionRepository'\n" + STORE))
        for prefix in ("import { X as Y } from './x'\n", "import X from './x'\n", "import { X } from 'package'\n", "'text';\n", "const Other = 1\n"):
            self.assertIsNone(parse_recovery_source(prefix + STORE))
        for suffix in (' class More {}', ' function more(){}', ' unexpected'):
            self.assertIsNone(parse_recovery_source(STORE + suffix))
        for source in (STORE.replace('Promise<void>', 'Promise<any>'), STORE.replace('@State', '@Unknown'), STORE.replace('loadSessions()', 'loadSessions(value)'), STORE.replace('this.sessions = loaded', 'this.sessions = loaded; notify()')):
            self.assertIsNone(parse_recovery_source(source))

    def test_comments_separators_delimiters(self):
        self.assertTrue(parse_recovery_source(STORE.replace('const loaded', '/* comment */ const loaded')))
        self.assertTrue(parse_recovery_source(STORE.replace('loadSessions()\n', 'loadSessions();')))
        self.assertIsNone(parse_recovery_source(STORE.replace('loadSessions()\n', 'loadSessions() ')))
        self.assertIsNone(parse_recovery_source(STORE.replace('loadSessions()', 'loadSessions([)]')))
        self.assertIsNone(parse_recovery_source(STORE.replace('loaded', 'load/*x*/ed')))
        self.assertIsNone(parse_recovery_source(REGISTRY.replace('new NetworkSessionRepository()', '/regex/')))
        self.assertIsNone(parse_recovery_source('/* unterminated' + STORE))

    def test_bounds_and_keywords(self):
        self.assertIsNone(parse_recovery_source(' ' * (2 * 1024 * 1024) + STORE))
        self.assertIsNone(parse_recovery_source(STORE.replace('const loaded', ' ' * 32769 + 'const loaded')))
        four = REGISTRY.replace('  chooseRepository', '  private a: Type\n  private b: Type\n  private c: Type\n  chooseRepository')
        self.assertTrue(parse_recovery_source(four))
        self.assertIsNone(parse_recovery_source(four.replace('  chooseRepository', '  private d: Type\n  chooseRepository')))
        for word in ('this', 'class', 'await', 'from', 'private'):
            self.assertIsNone(parse_recovery_source(REGISTRY.replace('online', word)))
        for value in (None, '\ud800', STORE.replace('const loaded', 'const\u2028loaded')):
            self.assertIsNone(parse_recovery_source(value))


if __name__ == '__main__':
    unittest.main()
