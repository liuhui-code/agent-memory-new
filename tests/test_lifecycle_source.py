# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_lifecycle_source import parse_lifecycle_source as parse
ROOT = Path(__file__).parents[1]
P = json.loads((ROOT / 'docs/evidence/lifecycle-source-prerequisites/protocol.json').read_text())
BASE = P['old_cases'][0]['sources']['BufferSession.ets']
ORIGINAL = (ROOT / 'docs/eval/fixtures/system-capability/src/coordinators/DraftSessionCoordinator.ets').read_text()

class LifecycleSourceTests(unittest.TestCase):
    def test_frozen_twelve_and_positive_sources(self):
        for case in P['source_negatives']:
            with self.subTest(case=case['id']):
                self.assertEqual(case['expected'], 'unknown')
                self.assertIsNone(parse(case['source']))
        self.assertEqual(parse(BASE)['receiver'], 'cache')
        self.assertEqual(parse(ORIGINAL)['receiver'], 'this.draftPreferences')
        owners = {parse(s)['owner'] for s in P['additional_cases'][0]['sources'].values()}
        self.assertEqual(owners, {'BufferSession', 'EditorSession'})
        for name, source in P['old_cases'][0]['sources'].items():
            if name != 'BufferSession.ets': self.assertIsNone(parse(source))
        self.assertIsNone(parse(BASE + BASE.replace('BufferSession', 'EditorSession')))

    def test_original_offsets_crlf(self):
        for source in (ORIGINAL, ORIGINAL.replace('\n', '\r\n'), ORIGINAL.replace('\n', '\r')):
            p = parse(source)
            self.assertEqual((p['class_start'], p['class_end']), (1, 16))
            self.assertEqual(source[p['class_start_offset']:p['class_end_offset']], source.rstrip())
            self.assertEqual([(m['start_line'], m['end_line']) for m in p['methods']], [(5,7),(9,11),(13,15)])
            h = p['methods'][0]
            self.assertEqual(h['call_line'], 6)
            self.assertEqual(source[h['call_start_offset']:h['call_end_offset']], 'this.restoreDraft()')
            self.assertEqual([f['kind'] for f in p['fields']], ['state','receiver'])
            for f in p['fields']:
                self.assertEqual(f['start_line'], f['end_line'])
                self.assertTrue(source[f['start_offset']:f['end_offset']].startswith(('@State','private')))

    def test_order_names_separators(self):
        p = parse(BASE); f = p['fields'][0]; m = p['methods']
        s = 'class BufferSession {\n' + '\n'.join(BASE[x['start_offset']:x['end_offset']] for x in [m[2],f,m[1],m[0]]) + '\n}'
        self.assertTrue(parse(s))
        self.assertTrue(parse(BASE.replace('this.reload()', 'this.reload();')))
        s = BASE.replace('text','body').replace('reload','refresh').replace('commit','persist').replace('cache','archive')
        self.assertEqual(parse(s)['receiver'], 'archive')

    def test_binding_scope(self):
        cases = [ORIGINAL.replace('this.draftPreferences.load()', 'draftPreferences.load()'),
                 ORIGINAL.replace('this.draftPreferences.save', 'other.save'),
                 ORIGINAL.replace('private draftPreferences: DraftPreferences = new DraftPreferences()', 'private other: DraftPreferences'),
                 BASE.replace('cache.load', 'cache.other.load'), BASE.replace('cache.save', 'cache?.save'),
                 BASE.replace("private text: string = ''", "private text: string = ''\nprivate text: string = ''"),
                 BASE.replace("private text: string = ''", "private reload: string = ''"),
                 BASE.replace('onMount()', 'constructor()'), BASE.replace('onMount()', 'onStart()'),
                 BASE.replace('async reload()', 'async reload(value: string)'),
                 BASE.replace('this.reload()', 'this.commit()'), BASE.replace('this.reload()', 'this.reload();notify()'),
                 BASE.replace("= ''", "= 'seed'"), BASE.replace('private text', 'text')]
        for s in cases:
            with self.subTest(source=s): self.assertIsNone(parse(s))

    def test_lexical_full_body_and_async(self):
        self.assertTrue(parse(BASE.replace('this.reload()', 'this /*comment*/ . reload()')))
        self.assertTrue(parse(BASE.replace('async reload', 'async /*same line*/ reload')))
        for s in [BASE.replace('async reload','async\nreload'), BASE.replace('async reload','async/*\n*/reload'),
                  BASE.replace('reload','re/*split*/load'), BASE.replace('this.reload()',"'this.reload()'"),
                  BASE.replace('this.reload()','/this.reload()/'), BASE.replace("''",'`label`'),
                  BASE+'/*unclosed', BASE.replace('this.reload()','this.reload([)]')]:
            self.assertIsNone(parse(s))

    def test_imports_tail_limits(self):
        self.assertTrue(parse("import { cache } from './storage'\n"+BASE))
        for prefix in ["import Storage from './x'\n", "import { Storage as Other } from './x'\n", "'header';\n"]:
            self.assertIsNone(parse(prefix+BASE))
        for s in [BASE+'class Extra{}', BASE.replace('class BufferSession','class BufferSession extends Parent'),
                  BASE.replace('this.reload()', ' '*32769+'this.reload()'), ' '*(2*1024*1024)+BASE,
                  None,'\ud800',BASE.replace('this.reload()','this.\u2028reload()')]:
            self.assertIsNone(parse(s))

if __name__ == '__main__': unittest.main()
