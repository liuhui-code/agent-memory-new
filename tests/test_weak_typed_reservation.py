# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors


class WeakTypedReservationTests(AgentMemoryTestBase):
    def evidence(self,weak=True):
        return {'certainty':'uncertain','primary':{'file_path':'Pair.ts','symbol':'forward',
                'typed_contract_match':True,'typed_contract_weak':weak,
                'source_range':{'start_line':3,'end_line':6}}}

    def anchors(self):
        return [{'file_path':'Pair.ts','symbol':'forward','start_line':3,'end_line':6,'record_id':3},
                {'file_path':'Pair.ts','symbol':'forward','start_line':10,'end_line':12,'record_id':5},
                {'file_path':'Other.ts','symbol':'other','start_line':2,'end_line':4}]

    def test_no_path_weak_does_not_replace_other_ranges(self):
        a=self.anchors();e=self.evidence();before=copy.deepcopy((a,e))
        self.assertIs(focus_callable_anchors(a,e,False),a)
        self.assertEqual((a,e),before)

    def test_path_reservation_and_strong_legacy_stay_unchanged(self):
        path={'activated':True,'path_candidates':[{'complete':False,'truncated':False}]}
        result=focus_callable_anchors(self.anchors(),self.evidence(),path)
        self.assertFalse(any(x.get('start_line')==10 for x in result))
        for weak in [False,None,1,"true",[]]:
            e=self.evidence(weak)
            if weak is None:e['primary'].pop('typed_contract_weak')
            result=focus_callable_anchors(self.anchors(),e,False)
            self.assertFalse(any(x.get('start_line')==10 for x in result))
        for certainty in [None,'unknown','']:
            e=self.evidence();e['certainty']=certainty
            result=focus_callable_anchors(self.anchors(),e,False)
            self.assertFalse(any(x.get('start_line')==10 for x in result))
        exclusive={'activated':True,'path_candidates':[{'complete':True,'truncated':False}]}
        a=self.anchors();self.assertIs(focus_callable_anchors(a,self.evidence(),exclusive),a)

    def test_missing_partial_and_invalid_primary_coverage_keeps_reservation(self):
        for anchors in [[{'file_path':'Other.ts','start_line':1,'end_line':8}],
                        [{'file_path':'Pair.ts','start_line':4,'end_line':5}],
                        [{'file_path':'Pair.ts','start_line':True,'end_line':8}],
                        [{'file_path':'Pair.ts'}]]:
            result=focus_callable_anchors(anchors,self.evidence(),False)
            self.assertTrue(any(x.get('file_path')=='Pair.ts' and x.get('start_line')==3
                                and x.get('end_line')==6 for x in result))
        a=[{'file_path':'Pair.ts','start_line':1,'end_line':9}]
        self.assertIs(focus_callable_anchors(a,self.evidence(),False),a)
        for source_range in [{'start_line':True,'end_line':6},{'start_line':3},{'start_line':7,'end_line':3}]:
            e=self.evidence();e['primary']['source_range']=source_range
            self.assertIsNot(focus_callable_anchors(a,e,False),a)

    def test_public_unchanged_required_receiver_range_survives_compact(self):
        p=json.loads(Path('docs/evidence/weak-typed-reservation/protocol.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in p['cohorts']['samefile']:(root/name).write_text(p['sources'][name])
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.', '--json')
            out=json.loads(self.run_memory(root,'context','--query',p['query'],'--compact','--json').stdout)
            h=out['query_handoff'];e=h['callable_evidence']
            self.assertTrue(e['primary']['typed_contract_weak'])
            self.assertEqual(e['certainty'],'uncertain')
            content='\n'.join(ex['content'] for a in h['code_anchors'] if a['file_path']=='Pair.ts'
                               for ex in a.get('source_excerpts',[]))
            self.assertIn("target.rejected('bad payload')",content)
            self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
            self.assertTrue(any(r.get('start_line')==10 and r.get('end_line')==12
                                for a in h['code_anchors'] if a['file_path']=='Pair.ts'
                                for r in a.get('source_ranges',[])))
