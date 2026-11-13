# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_callable_focus import multiple_requested_anchors_present
ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/'docs/eval/named-interface-retention/protocol.json').read_text())
class NamedInterfaceRetentionTests(AgentMemoryTestBase):
    def anchors(self):
        return [{'file_path':n+'.ts','symbol':n,'symbol_type':t,'start_line':1,'end_line':3} for n,t in [('PacketScaler','class'),('UnitSpec','interface')]]
    def test_existing_explicit_pair_contract_includes_interface(self):
        self.assertTrue(multiple_requested_anchors_present(self.anchors(),{},P['queries'][0]['query']))
    def test_no_scope_authority_from_ambiguous_or_indirect_identity(self):
        a=self.anchors();a.append({**a[1],'file_path':'other/UnitSpec.ts'})
        self.assertFalse(multiple_requested_anchors_present(a,{},P['queries'][0]['query']))
        for q in ('Find multiple native import boundaries.','Find packet scaling and schema implementation.','Find PacketScaler, not UnitSpec.','Find the strings "PacketScaler" and "UnitSpec".','PacketScaler uses UnitSpec. Find PacketScaler.'):
            self.assertFalse(multiple_requested_anchors_present(self.anchors(),{},q),q)
        for k,v in [('end_line',None),('symbol_type','field'),('file_path','PacketScaler.ts')]:
            a=self.anchors();a[1][k]=v
            self.assertFalse(multiple_requested_anchors_present(a,{},P['queries'][0]['query']))
    def test_public_pair_keeps_identity_typed_refs_and_current_source_under_budget(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,source in P['sources'].items():(root/name).write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            for case in P['queries'][:3]:
                raw=json.loads(self.run_memory(root,'context','--query',case['query'],'--json').stdout)
                out=json.loads(self.run_memory(root,'context','--query',case['query'],'--compact','--json').stdout)
                anchors=out['query_handoff']['code_anchors']
                self.assertTrue(set(case['required'])<={a['file_path'] for a in anchors},case['id'])
                self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
                for a in anchors:
                    refs=[r for r in raw['query_handoff']['code_anchors'] if r['file_path']==a['file_path']]
                    for ident in a.get('record_ids',[]):self.assertTrue(any(r.get('record_id')==ident and r.get('record_type')==a.get('record_type') for r in refs))
                    for e in a.get('source_excerpts',[]):self.assertEqual('\n'.join(P['sources'][a['file_path']].splitlines()[e['start_line']-1:e['end_line']]),e['content'])
                if case['id']=='named-class-interface':
                    unit=next(a for a in anchors if a['file_path']=='UnitSpec.ts')
                    self.assertIn('interface UnitSpec',' '.join(e['content'] for e in unit.get('source_excerpts',[])))
