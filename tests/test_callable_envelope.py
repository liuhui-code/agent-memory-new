# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""New opt-in display capability; synthetic payloads do not establish public reds."""
from copy import deepcopy
from pathlib import Path
import tempfile
from agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_callable_envelope import expand_callable_envelopes
from tools.agent_memory_runtime.storage import resolve_project,connect
from tools.agent_memory_runtime.context_budget import synchronize_estimate
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens

SOURCE='''@Component
export struct FoldingPanel {
  @State open: boolean = false
  @Builder
  private toggleRegion() {
    Column() {
      Text('Details')
      Button('Toggle').onClick(() => { this.open = !this.open })
    }
  }
  build() { this.toggleRegion() }
}
'''

class CallableEnvelopeTests(AgentMemoryTestBase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'project';self.root.mkdir();self.file=self.root/'Panel.ets';self.file.write_text(SOURCE)
        self.run_memory(self.root,'learn-path','--path','.')
        self.project=resolve_project(str(self.root),str(self.memory_home(self.root)))
        with connect(self.project)as conn:
            self.row=dict(conn.execute("SELECT * FROM code_symbols WHERE symbol='toggleRegion'").fetchone())
            file=dict(conn.execute("SELECT * FROM code_files WHERE file_path='Panel.ets'").fetchone())
        r=self.row;self.candidate=dict(file_path='Panel.ets',owner_name='FoldingPanel',owner_kind=r['owner_kind'],symbol=r['symbol'],score=9,source_range=dict(start_line=r['start_line'],end_line=r['end_line'],selection_reason='callable_symbol_range'))
        self.old=dict(symbol='Column',start_line=6,end_line=9,content='\n'.join(SOURCE.splitlines()[5:9]),source='current_worktree',selection_reason='callable_mechanism_window',focus_line=None,truncated=False)
        anchor=dict(file_path='Panel.ets',symbol='FoldingPanel',record_type='code_file',record_ids=[file['id']],source_excerpts=[self.old])
        self.payload=dict(source_freshness=dict(status='current',generation=r['index_generation']),query_handoff=dict(code_anchors=[anchor],callable_evidence=dict(primary=self.candidate,alternatives=[]),log_anchors=[{'message':'preserve me'}],relation_hints=[{'kind':'imports'}],source_excerpt_policy=dict(excerpt_count=1,excerpt_chars=len(self.old['content']))),output_budget=dict(target_tokens=2000,estimated_tokens=0,truncated=False));synchronize_estimate(self.payload)

    def apply(self,payload=None):return expand_callable_envelopes(self.project,self.payload if payload is None else payload,enabled=True)

    def test_additive_exactly_reversible_and_idempotent(self):
        before=deepcopy(self.payload);out=self.apply();self.assertIsNot(out,self.payload);self.assertEqual(before,self.payload)
        new=out['query_handoff']['code_anchors'][0]['source_excerpts'][0]
        self.assertEqual((new['start_line'],new['end_line']),(5,10));self.assertEqual(new['content'],'\n'.join(SOURCE.splitlines()[4:10]))
        prior=dict(new['expanded_from']);prior['content']='\n'.join(new['content'].splitlines()[prior['start_line']-new['start_line']:prior['end_line']-new['start_line']+1]);self.assertEqual(prior,self.old)
        restored=deepcopy(out);restored['query_handoff']['code_anchors'][0]['source_excerpts'][0]=prior;restored['query_handoff']['source_excerpt_policy']=before['query_handoff']['source_excerpt_policy'];restored['output_budget']=before['output_budget'];self.assertEqual(restored,before)
        self.assertEqual(out['output_budget']['estimated_tokens'],estimate_payload_tokens(out));self.assertIs(self.apply(out),out)

    def test_default_disabled(self):self.assertIs(expand_callable_envelopes(self.project,self.payload),self.payload)

    def test_budget_atomic_noop(self):
        out=self.apply();p=deepcopy(self.payload);p['output_budget']['target_tokens']=estimate_payload_tokens(out)-1;synchronize_estimate(p);self.assertIs(self.apply(p),p)

    def test_bad_candidate_identity_or_window(self):
        for key,value in [('owner_name','Other'),('symbol','missing'),('owner_kind','wrong')]:
            p=deepcopy(self.payload);p['query_handoff']['callable_evidence']['primary'][key]=value;self.assertIs(self.apply(p),p)
        p=deepcopy(self.payload);p['query_handoff']['callable_evidence']['primary']['source_range']['selection_reason']='semantic_mechanism_window';self.assertIs(self.apply(p),p)

    def test_stale_bytes_and_generation(self):
        p=deepcopy(self.payload);p['source_freshness']['generation']+=1;self.assertIs(self.apply(p),p)
        self.file.write_text(SOURCE+'// modified\n');self.assertIs(self.apply(),self.payload)

    def test_changed_excerpt_missing_identity_or_ambiguity(self):
        for operation in ['content','record','multiple','range','source']:
            p=deepcopy(self.payload);a=p['query_handoff']['code_anchors'][0];e=a['source_excerpts'][0]
            if operation=='content':e['content']+='!'
            if operation=='record':a['record_ids']=[]
            if operation=='multiple':p['query_handoff']['callable_evidence']['alternatives']=[deepcopy(self.candidate)]
            if operation=='range':e['end_line']=200
            if operation=='source':e['source']='cached'
            self.assertIs(self.apply(p),p)

    def test_unknown_metadata_and_caps(self):
        p=deepcopy(self.payload);p['query_handoff']['code_anchors'][0]['source_excerpts'][0]['unknown']=True;self.assertIs(self.apply(p),p)
        p=deepcopy(self.payload);p['query_handoff']['callable_evidence']['primary']['source_range']['end_line']=100;self.assertIs(self.apply(p),p)
        p=deepcopy(self.payload);p['query_handoff']['code_anchors'].append({'file_path':'Extra.ets','source_excerpts':[dict(self.old,content='x'*2600)]});self.assertIs(self.apply(p),p)

    def test_contradictory_index_owner_declines(self):
        with connect(self.project)as conn:conn.execute("UPDATE code_symbols SET owner_name='Other' WHERE id=?",(self.row['id'],));conn.commit()
        self.assertIs(self.apply(),self.payload)

    def test_unknown_other_excerpt_noop(self):
        for bad in [{}, {'content':None}, {'content':23}]:
            p=deepcopy(self.payload);p['query_handoff']['code_anchors'].append({'source_excerpts':[bad]});self.assertIs(self.apply(p),p)

    def test_hook_after_reading_and_no_reentry(self):
        import inspect
        from tools.agent_memory_runtime.command_handlers import context
        source=inspect.getsource(context)
        self.assertLess(source.index('data = static_reading_order'),source.index('data = expand_callable_envelopes'))
        self.assertLess(source.index('data = expand_callable_envelopes'),source.index('record_query_usage'))
        self.assertEqual(source.count('data = static_reading_order'),1)
