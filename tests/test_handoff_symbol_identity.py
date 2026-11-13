# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy
import json
import tempfile
import unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_handoff import append_code_anchor, code_anchors


def row(identifier=1, start=3, end=6, **extra):
    return dict(file_path='Pair.ts', symbol='forward', kind='symbol', id=identifier,
                start_line=start, end_line=end, symbol_type='function', **extra)


class HandoffSymbolIdentityTests(AgentMemoryTestBase):
    def test_public_required_direct_method_survives_raw_projection(self):
        p=json.loads(Path('docs/evidence/typed-parameter-invocation/samefile-protocol.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in p['cohorts']['samefile']:
                (root/name).write_text(p['sources'][name])
            self.run_memory(root,'init')
            self.run_memory(root,'learn-path','--path','.', '--json')
            out=json.loads(self.run_memory(root,'context','--query',p['query'],'--json').stdout)
            wiki=[x for x in out['wiki_matches'] if x.get('file_path')=='Pair.ts' and x.get('start_line')==10]
            self.assertEqual(len(wiki),1)
            self.assertEqual(wiki[0]['owner_name'],'Direct')
            self.assertTrue(any(x.get('record_type')=='code_symbol' and x.get('record_id')==wiki[0]['id']
                                and x.get('start_line')==10 and x.get('end_line')==12
                                for x in out['query_handoff']['code_anchors']))

    def test_distinct_symbol_records_and_real_duplicate(self):
        values=[row(),row(),row(2,10,12),row(3,15,17)]
        saved=copy.deepcopy(values)
        self.assertEqual([x['record_id'] for x in code_anchors(values,[])],[1,2])
        self.assertEqual(values,saved)
        self.assertEqual(len(code_anchors([row(),row(1,10,12)],[])),1)
        self.assertEqual(len(code_anchors([row(),row(2)],[])),2)

    def test_unknown_legacy_and_cross_source_do_not_gain_identity(self):
        for identifier in [None,0,-1,True,'2']:
            self.assertEqual(len(code_anchors([row(),row(identifier,10,12)],[])),1)
        for start,end in [(None,None),(True,6),(0,6),(10,9)]:
            self.assertEqual(len(code_anchors([row(),row(2,start,end)],[])),1)
        for source in ['unknown','log_emitter','wrapped_log_caller']:
            anchors=[];seen=set()
            self.assertTrue(append_code_anchor(anchors,seen,row(),'wiki'))
            self.assertFalse(append_code_anchor(anchors,seen,row(2,10,12),source))
        legacy=row(2,10,12);legacy['kind']='file'
        self.assertEqual(len(code_anchors([legacy,row()],[])),1)

    def test_same_record_conflicting_description_keeps_first(self):
        first=row();second=row(1,10,12);second["symbol"]="other"
        self.assertEqual(len(code_anchors([first,second],[])),1)
        second["file_path"]="Other.ts"
        self.assertEqual(len(code_anchors([first,second],[])),1)
        first["symbol"]="";second=row(2,10,12);second["symbol"]=""
        self.assertEqual(len(code_anchors([first,second],[])),1)

    def test_budget_and_order_unchanged(self):
        values=[]
        for i in range(20):
            r=row(i+1);r['file_path']=f'{i}.ts';values.append(r)
        result=code_anchors(values,[])
        self.assertEqual(len(result),12)
        self.assertEqual([r['record_id'] for r in result],list(range(1,13)))

if __name__=='__main__':unittest.main()
