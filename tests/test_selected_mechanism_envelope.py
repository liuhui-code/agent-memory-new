"""Current-source identity is needed to complete an already selected method."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
from agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_callable_envelope import expand_callable_envelopes
from tools.agent_memory_runtime.storage import resolve_project, connect
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens

PROTOCOL=Path(__file__).resolve().parents[1]/'docs/releases/semantic-method-envelope-20261119/protocol.json'

class SelectedMechanismEnvelopeTests(AgentMemoryTestBase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'project';self.root.mkdir()
        self.case=json.loads(PROTOCOL.read_text())['cases'][0]
        for name,source in self.case['sources'].items():(self.root/name).write_text(source)
        self.run_memory(self.root,'learn-path','--path','.')
        self.project=resolve_project(str(self.root),str(self.memory_home(self.root)))
        # Freeze the actually observed pre-change projection, with real DB identities.
        self.payload=json.loads(self.run_memory(self.root,'context','--query',self.case['queries'][0]['query'],'--compact','--json').stdout)
        a=self.payload['query_handoff']['code_anchors'][0];e=a['source_excerpts'][0]
        if 'expanded_from'in e:
            old=dict(e['expanded_from']);old['content']='\n'.join(e['content'].split('\n')[old['start_line']-e['start_line']:old['end_line']-e['start_line']+1]);a['source_excerpts']=[old]
            self.payload['query_handoff']['source_excerpt_policy']['excerpt_chars']=len(old['content'])
            from tools.agent_memory_runtime.context_budget import synchronize_estimate
            synchronize_estimate(self.payload)

    def apply(self,p=None):return expand_callable_envelopes(self.project,self.payload if p is None else p,enabled=True)

    def test_full_source_reversible_without_touching_evidence(self):
        before=deepcopy(self.payload);out=self.apply();self.assertIsNot(out,self.payload)
        new=out['query_handoff']['code_anchors'][0]['source_excerpts'][0]
        self.assertEqual((new['start_line'],new['end_line']),(9,13))
        self.assertIn('record: VoucherRecord',new['content'])
        old=dict(new['expanded_from']);old['content']='\n'.join(new['content'].split('\n')[old['start_line']-9:old['end_line']-9+1])
        restored=deepcopy(out);restored['query_handoff']['code_anchors'][0]['source_excerpts']=[old]
        restored['output_budget']=before['output_budget'];restored['query_handoff']['source_excerpt_policy']=before['query_handoff']['source_excerpt_policy']
        self.assertEqual(restored,before);self.assertEqual(self.payload,before);self.assertIs(self.apply(out),out)

    def test_wrong_file_identity_and_unknown_metadata(self):
        for kind in ['id','range','window','content','extra','owner','kind','role','uncertain','duplicate']:
            p=deepcopy(self.payload);h=p['query_handoff'];a=h['code_anchors'][0];c=h['callable_evidence']['primary']
            if kind=='id':a['record_ids']=[9999]
            if kind=='range':a['source_ranges'][0]['start_line']=9
            if kind=='window':a['read_window']['start_line']=9
            if kind=='content':a['source_excerpts'][0]['content']+=' '
            if kind=='extra':a['source_excerpts'][0]['unknown']='preserve'
            if kind=='owner':c['owner_name']='Wrong'
            if kind=='kind':c['owner_kind']='Wrong'
            if kind=='role':a['role']='supporting'
            if kind=='uncertain':h['callable_evidence']['certainty']='uncertain'
            if kind=='duplicate':h['callable_evidence']['alternatives']=[deepcopy(c)]
            self.assertIs(self.apply(p),p,kind)

    def test_missing_owner_name_requires_exact_unique_index_identity(self):
        p=deepcopy(self.payload);p['query_handoff']['callable_evidence']['primary'].pop('owner_name')
        self.assertIsNot(self.apply(p),p)
        with connect(self.project)as conn:
            conn.execute("UPDATE code_symbols SET qualified_name='Other.recordSuccessfulUse' WHERE symbol='recordSuccessfulUse'");conn.commit()
        self.assertIs(self.apply(p),p)

    def test_same_name_other_owner_is_ambiguous(self):
        with connect(self.project)as conn:
            row=dict(conn.execute("SELECT * FROM code_symbols WHERE symbol='recordSuccessfulUse'").fetchone());row.pop('id');row.update(symbol_key='different-owner',qualified_name='Other.recordSuccessfulUse',owner_name='Other')
            conn.execute('INSERT INTO code_symbols ('+','.join(row)+') VALUES ('+','.join('?'for _ in row)+')',list(row.values()));conn.commit()
        self.assertIs(self.apply(),self.payload)

    def test_stale_source_and_generation(self):
        p=deepcopy(self.payload);p['source_freshness']['generation']+=1;self.assertIs(self.apply(p),p)
        f=self.root/next(iter(self.case['sources']));f.write_text(f.read_text()+'\n');self.assertIs(self.apply(),self.payload)

    def test_atomic_budget_and_extra_line_separator(self):
        out=self.apply();p=deepcopy(self.payload);p['output_budget']['target_tokens']=estimate_payload_tokens(out)-1
        self.assertIs(self.apply(p),p)
        f=self.root/next(iter(self.case['sources']));f.write_text(f.read_text().replace('usageCount:','\u2028usageCount:'))
        self.assertIs(self.apply(),self.payload)
