"""Frozen physical-display controls; no selector or owner-policy oracle changes."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from agent_memory_runtime.context_display_union import union_primary_display
from agent_memory_runtime.context_source_excerpt import redact_source_excerpt_bodies

D = Path(__file__).resolve().parents[1] / 'docs/evidence/lifecycle-display-qualification'

class DisplayUnionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.protocol = json.loads((D / 'protocol.json').read_text())
        for name, source in self.protocol['sources'].items():
            (self.root / name).write_text(source)
        before = json.loads((D / 'before.json').read_text())
        self.p, self.rows = before['compact'], before['raw']['wiki_matches']

    def run_union(self, **kwargs):
        return union_primary_display(self.p, str(self.root), 1500, source_rows=self.rows, **kwargs)

    def test_lossless_priority_and_idempotence(self):
        baseline = copy.deepcopy(self.p)
        out = self.run_union()
        self.assertIsNot(out, self.p)
        self.assertEqual(self.p, baseline)
        old = baseline['query_handoff']['code_anchors'][0]['source_excerpts']
        es = out['query_handoff']['code_anchors'][0]['source_excerpts']
        self.assertEqual([m['symbol'] for m in es[0]['constituent_ranges']], ['reload', 'onMount'])
        self.assertIsNone(es[0]['symbol'])
        self.assertEqual((es[0]['start_line'], es[0]['end_line']), (3, 8))
        for e, m in zip(old, es[0]['constituent_ranges']):
            self.assertEqual(m, {k:v for k,v in e.items() if k != 'content'})
            self.assertIn(e['content'], es[0]['content'])
        self.assertIn('await cache.save(this.text)', es[1]['content'])
        reset = copy.deepcopy(out)
        reset['query_handoff']['code_anchors'][0]['source_excerpts'] = old
        reset['query_handoff']['source_excerpt_policy'] = baseline['query_handoff']['source_excerpt_policy']
        reset['output_budget'] = baseline['output_budget']
        self.assertEqual(reset, baseline)
        self.assertIs(union_primary_display(out, str(self.root), 1500, source_rows=self.rows), out)
        self.assertEqual(json.loads(json.dumps(out)), out)

    def test_forward_order_and_neutral_independent_members(self):
        self.p['query_handoff']['code_anchors'][0]['source_excerpts'].reverse()
        out = self.run_union()
        self.assertEqual([m['symbol'] for m in out['query_handoff']['code_anchors'][0]['source_excerpts'][0]['constituent_ranges']], ['onMount', 'reload'])
        # No owner lookup/certification is attached to these independent ranges.
        self.assertNotIn('owner_name', out['query_handoff']['code_anchors'][0]['source_excerpts'][0])

    def test_fallback_members_and_caps(self):
        original = copy.deepcopy(self.p)
        mutations = [lambda e:e.update(start_line=7), lambda e:e.update(start_line=5),
                     lambda e:e.update(start_line=3,end_line=5), lambda e:e.update(truncated=True),
                     lambda e:e.pop('focus_line'), lambda e:e.update(extra='x'),
                     lambda e:e.update(constituent_ranges=[]), lambda e:e.update(source='other'),
                     lambda e:e.update(selection_reason='selected_log_event_owner'),
                     lambda e:e.update(content='changed')]
        for mutate in mutations:
            self.p = copy.deepcopy(original)
            mutate(self.p['query_handoff']['code_anchors'][0]['source_excerpts'][0])
            self.assertIs(self.run_union(), self.p)
        self.p = original
        for kwargs in ({'source_char_cap':100}, {'total_char_cap':100}, {'source_line_cap':5}):
            self.assertIs(self.run_union(**kwargs), self.p)
        self.assertIs(union_primary_display(self.p, str(self.root), 1155, source_rows=self.rows), self.p)

    def test_identity_and_source_conflicts(self):
        original = copy.deepcopy(self.rows)
        for key, value in [('id',999),('kind','file'),('project_id','other'),('file_path','x'),
                           ('symbol','other'),('qualified_name','other.commit'),('owner_kind','other'),
                           ('owner_name','other'),('start_line',8),('end_line',12),
                           ('index_generation',2),('source_digest','0'*64)]:
            self.rows = copy.deepcopy(original)
            next(r for r in self.rows if r['id']==4)[key] = value
            self.assertIs(self.run_union(),self.p,key)
        self.rows = original + [copy.deepcopy(next(r for r in original if r['id']==4))]
        self.assertIs(self.run_union(),self.p)
        self.rows = original
        path = self.root/'BufferSession.ets'
        path.write_text(path.read_text()+'// changed tail\n')
        self.assertIs(self.run_union(),self.p)

    def test_redaction_and_untrusted_nested_content(self):
        out = self.run_union()
        clean = redact_source_excerpt_bodies(out)
        metadata = clean['query_handoff']['code_anchors'][0]['source_excerpt_metadata'][0]
        self.assertEqual(metadata['constituent_ranges'],out['query_handoff']['code_anchors'][0]['source_excerpts'][0]['constituent_ranges'])
        self.assertNotIn('await cache',json.dumps(clean))
        out['query_handoff']['code_anchors'][0]['source_excerpts'][0]['constituent_ranges'][0]['content']='SECRET'
        clean = redact_source_excerpt_bodies(out)
        self.assertNotIn('SECRET',json.dumps(clean))
        self.assertNotIn('constituent_ranges',clean['query_handoff']['code_anchors'][0]['source_excerpt_metadata'][0])

if __name__ == '__main__':
    unittest.main()
