# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from tools.agent_memory_runtime.query_callable_evidence import callable_evidence

class SameOwnerAlternativeTests(unittest.TestCase):
    def row(self,i,**kw):
        return dict(dict(symbol_id=i,file_path='Pair.ts',symbol='f'+str(i),owner_name='Pair',owner_kind='class',start_line=i,end_line=i,score=10,evidence_score=10,reasons=[]),**kw)
    def view(self,*rows):return callable_evidence({'callable_candidates':list(rows),'source_ranges':[dict(r,selection_reason='callable_symbol_range') for r in rows]})
    def test_uncertain_competing_methods_are_visible(self):
        v=self.view(self.row(1),self.row(2));self.assertEqual(v['certainty'],'uncertain');self.assertEqual(v['primary']['symbol'],'f1');self.assertEqual([x['symbol'] for x in v['alternatives']],['f2'])
    def test_bounded_and_existing_cross_file_display_unchanged(self):
        self.assertEqual(self.view(self.row(1,score=20,evidence_score=20),self.row(2))['alternatives'],[])
        v=self.view(self.row(1),self.row(2),self.row(3,file_path='Other.ts',owner_name='Other'))
        self.assertEqual([x['symbol'] for x in v['alternatives']],['f3'])
    def test_unknown_conflicting_owner_and_duplicate_not_added(self):
        for row in [self.row(2,symbol_id=None,owner_name=''),self.row(2,start_line=0),self.row(2,owner_name='Other'),self.row(1)]:
            self.assertEqual(self.view(self.row(1),row)['alternatives'],[])
    def test_maximum_two_and_original_order(self):
        v=self.view(*[self.row(i) for i in range(1,6)]);self.assertEqual([x['symbol'] for x in v['alternatives']],['f2','f3'])
    def test_same_symbol_distinct_identity_ranges_remain_distinct(self):
        v=self.view(self.row(1,symbol='run'),self.row(2,symbol='run'));self.assertEqual(v['alternatives'][0]['source_range']['start_line'],2)
