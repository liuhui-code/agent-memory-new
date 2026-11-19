"""Requested declarations must be authenticated, not borrowed from a file ID."""
from copy import deepcopy
from pathlib import Path
import json,tempfile
from agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_declaration_excerpt import append_requested_declaration
from tools.agent_memory_runtime.storage import resolve_project,connect
from tools.agent_memory_runtime.context_budget import synchronize_estimate
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens
P=Path(__file__).resolve().parents[1]/'docs/releases/explicit-declaration-body-20261119/protocol.json'

class DeclarationExcerptTests(AgentMemoryTestBase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'project';self.root.mkdir();self.case=json.loads(P.read_text())['cases'][0]
        for name,text in self.case['sources'].items():(self.root/name).write_text(text)
        self.run_memory(self.root,'learn-path','--path','.')
        self.project=resolve_project(str(self.root),str(self.memory_home(self.root)))
        self.payload=json.loads(self.run_memory(self.root,'context','--query',self.case['queries'][2]['query'],'--compact','--json').stdout)
        a=self.payload['query_handoff']['code_anchors'][0]
        a['source_excerpts']=[e for e in a['source_excerpts']if e.get('selection_reason')!='authenticated_requested_declaration']
        p=self.payload['query_handoff']['source_excerpt_policy'];p.update(excerpt_count=1,excerpt_chars=len(a['source_excerpts'][0]['content']));synchronize_estimate(self.payload)

    def apply(self,p=None):return append_requested_declaration(self.project,self.payload if p is None else p)

    def test_body_added_old_data_exactly_preserved_and_idempotent(self):
        out=self.apply();self.assertIsNot(out,self.payload);a=out['query_handoff']['code_anchors'][0];e=a['source_excerpts'][-1]
        self.assertEqual((e['start_line'],e['end_line']),(1,4));self.assertIn('usageCount: number',e['content']);self.assertEqual(a['source_excerpts'][0],self.payload['query_handoff']['code_anchors'][0]['source_excerpts'][0])
        r=deepcopy(out);r['query_handoff']['code_anchors'][0]['source_excerpts'].pop();r['query_handoff']['source_excerpt_policy']=self.payload['query_handoff']['source_excerpt_policy'];r['output_budget']=self.payload['output_budget'];self.assertEqual(r,self.payload)
        self.assertIs(self.apply(out),out)

    def test_negative_quoted_comparison_unknown_and_case_mismatch(self):
        for q in [c['query']for c in self.case['queries']if c['id']!='declaration']+['Locate Missing entity definition.','Locate voucherrecord entity definition.']:
            p=deepcopy(self.payload);p['query']=q;self.assertIs(self.apply(p),p,q)

    def test_record_id_and_range_binding(self):
        with connect(self.project)as conn:r=dict(conn.execute("SELECT * FROM code_symbols WHERE symbol='VoucherRecord'").fetchone())
        for kind in ['id','duplicateid','range','path','type','content','coordinate','recordtype']:
            p=deepcopy(self.payload);a=p['query_handoff']['code_anchors'][0]
            if kind=='id':a['record_ids'].remove(r['id'])
            if kind=='duplicateid':a['record_ids'].append(r['id'])
            if kind=='range':a['source_ranges'][0]['end_line']=5
            if kind=='path':a['file_path']='../VoucherUsageCoordinator.ets'
            if kind=='type':a['symbol_type']='class'
            if kind=='content':a['source_excerpts'][0]['content']+='!'
            if kind=='coordinate':a['source_excerpts'][0]['start_line']=0
            if kind=='recordtype':a['record_type']='code_file'
            self.assertIs(self.apply(p),p,kind)

    def test_index_qualified_name_and_duplicate_name_decline(self):
        with connect(self.project)as conn:
            row=dict(conn.execute("SELECT * FROM code_symbols WHERE symbol='VoucherRecord'").fetchone());conn.execute("UPDATE code_symbols SET qualified_name='Other.VoucherRecord' WHERE id=?",(row['id'],));conn.commit()
        self.assertIs(self.apply(),self.payload)
        with connect(self.project)as conn:
            conn.execute('UPDATE code_symbols SET qualified_name=? WHERE id=?',(row['qualified_name'],row['id']));row.pop('id');row['symbol_key']='another';conn.execute('INSERT INTO code_symbols ('+','.join(row)+') VALUES ('+','.join('?'for _ in row)+')',list(row.values()));conn.commit()
        self.assertIs(self.apply(),self.payload)

    def test_stale_digest_generation_and_unknown_separator(self):
        p=deepcopy(self.payload);p['source_freshness']['generation']+=1;self.assertIs(self.apply(p),p)
        f=self.root/next(iter(self.case['sources']));f.write_text(f.read_text()+'\u2028');self.assertIs(self.apply(),self.payload)

    def test_budget_excerpt_cap_and_ambiguous_selected_owner(self):
        out=self.apply();p=deepcopy(self.payload);p['control_padding']='x'*2000;synchronize_estimate(p)
        enlarged=deepcopy(out);enlarged['control_padding']=p['control_padding'];synchronize_estimate(enlarged)
        self.assertLessEqual(estimate_payload_tokens(p),1500);self.assertGreater(estimate_payload_tokens(enlarged),1500);self.assertIs(self.apply(p),p)
        p=deepcopy(self.payload);a=p['query_handoff']['code_anchors'][0];a['source_excerpts'].append(deepcopy(a['source_excerpts'][0]));self.assertIs(self.apply(p),p)
        p=deepcopy(self.payload);p['query_handoff']['code_anchors'].append(deepcopy(p['query_handoff']['code_anchors'][0]));self.assertIs(self.apply(p),p)

    def test_already_whole_declaration_noop(self):
        p=deepcopy(self.payload);e=p['query_handoff']['code_anchors'][0]['source_excerpts'][0];e.update(start_line=1,end_line=14,content=next(iter(self.case['sources'].values())).rstrip('\n'));self.assertIs(self.apply(p),p)
