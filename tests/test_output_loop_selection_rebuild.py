# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime.query_output_loop_selection import (
    qualify_output_loop,output_loop_request,output_loop_focus,OutputLoopTrial,OutputLoopContext,
    bind_output_loop_context,output_loop_context_view,enrich_output_loop_context,
)
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.query_output_loop_selection import output_loop_focus

D=Path(__file__).parents[1]/'docs/evidence/rebuild-output30'


class Rows:
    def __init__(self,rows,files,edges):self.rows=rows;self.files=files;self.edges=edges
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def execute(self,sql,args):
        return self.rows if 'FROM code_symbols' in sql else self.files if 'FROM code_files' in sql else self.edges


class OutputLoopSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        protocol=json.loads((D/'independent-protocol.json').read_text())
        for path,source in protocol['sources'].items():(self.root/path).write_text(source)
        trace=json.loads((D/'trace.json').read_text())
        self.items=trace['items'];self.rows=trace['rows'];self.files=trace['files'];self.edges=[]
        self.query=protocol['queries'][0]['query'];self.project=SimpleNamespace(root=self.root,project_id=self.rows[0]['project_id'])
        self.baseline=json.loads((D/'before.json').read_text())['results'][0]['raw'];self.baseline['project_path']=str(self.root)

    def authority(self):
        with patch('tools.agent_memory_runtime.query_output_loop_selection.connect',return_value=Rows(self.rows,self.files,self.edges)):
            return qualify_output_loop(self.project,self.query,self.items)

    def trial(self,authority):
        result=OutputLoopTrial(copy.deepcopy(self.baseline));result._output_loop_authority=authority
        result['wiki_matches']=output_loop_focus(authority,self.query,self.items)
        result['query_handoff']['code_anchors']=[]
        return result

    def test_full_request_and_source_identity(self):
        self.assertTrue(output_loop_request(self.query));a=self.authority();self.assertIsNotNone(a)
        self.assertEqual([r['parsed']['owner']for r in a._receipts],['PipeCollector'])
        for copied in (copy.copy(a),copy.deepcopy(a)):
            self.assertIsNone(output_loop_focus(copied,self.query,self.items))

    def test_source_view_keeps_public_baseline(self):
        a=self.authority();result=bind_output_loop_context(self.query,self.baseline,self.trial(a))
        self.assertIsInstance(result,OutputLoopContext);self.assertEqual(dict(result),self.baseline)
        payload=compact_context(result);anchors=payload['query_handoff']['code_anchors']
        self.assertEqual([x['file_path']for x in anchors],['PipeCollector.ts'])
        self.assertEqual(anchors[0]['source_excerpts'][0]['end_line'],10)
        self.assertEqual(anchors[0]['source_excerpts'][0]['source'],'validated_request_snapshot')
        for clone in [dict(result),copy.copy(result),copy.deepcopy(result),json.loads(json.dumps(result))]:
            self.assertIsNone(output_loop_context_view(clone)[1])
            self.assertEqual(compact_context(clone)['query_handoff'],compact_context(self.baseline)['query_handoff'])

    def test_original_query_pool_and_receipt_mutation(self):
        a=self.authority();self.assertIsNone(output_loop_focus(a,self.query+'extra',self.items))
        changed=copy.deepcopy(self.items);changed[0]['id']+=1
        self.assertIsNone(output_loop_focus(a,self.query,changed))
        r=bind_output_loop_context(self.query,self.baseline,self.trial(a));r._view['query']='changed'
        self.assertIsNone(output_loop_context_view(r)[1])

    def test_unknown_freshness_and_pool(self):
        for key,value in [('source_digest','0'*64),('index_generation',0),('id',0),('owner_name','Wrong'),('start_line',99),('semantic_adapter','unknown@1')]:
            original=copy.deepcopy(self.rows)
            row=next(r for r in self.rows if r['symbol']=='collect');row[key]=value
            self.assertIsNone(self.authority(),key);self.rows=original
        self.items=[r for r in self.items if r.get('file_path')!='PipeCollector.ts']
        self.assertIsNone(self.authority())

    def test_two_current_witnesses_and_budget_fallback(self):
        path=self.root/'OtherCollector.ts';path.write_text((self.root/'PipeCollector.ts').read_text())
        # Separate current indexed file identity, never a uniqueness-based certificate.
        for collection in (self.rows,self.files,self.items):
            clones=[]
            for r in collection:
                if r.get('file_path')=='PipeCollector.ts':
                    r=copy.deepcopy(r);r['file_path']='OtherCollector.ts';r['id']+=100
                    if r.get('symbol_key'):r['symbol_key']='other:'+r['symbol_key']
                    clones.append(r)
            collection.extend(clones)
        a=self.authority();self.assertIsNotNone(a);self.assertEqual(len(a._receipts),2)
        result=bind_output_loop_context(self.query,self.baseline,self.trial(a))
        self.assertIsInstance(result,OutputLoopContext)
        self.assertEqual({x['file_path']for x in compact_context(result)['query_handoff']['code_anchors']},{'PipeCollector.ts','OtherCollector.ts'})
        with patch('tools.agent_memory_runtime.context_compact._compact_context',return_value={'query_handoff':{'code_anchors':[]}}):
            self.assertIs(bind_output_loop_context(self.query,self.baseline,self.trial(a)),self.baseline)

    def test_both_baseline_and_trial_protection(self):
        a=self.authority()
        for side in ('baseline','trial'):
            for key in ('identity_match','log_identity_match','graph_neighbor','graph_relation'):
                b=copy.deepcopy(self.baseline);t=self.trial(a);h=(b if side=='baseline' else t)['query_handoff'];h['code_anchors']=[{'file_path':'Protected.ets',key:True}]
                self.assertIs(bind_output_loop_context(self.query,b,t),b)

    def test_accounting_direct_and_facade_once(self):
        from tools.agent_memory_runtime.query_results import limited_context
        from tools.agent_memory_runtime.context_facade import ContextFacade
        a=self.authority();trial=self.trial(a)
        with patch('tools.agent_memory_runtime.query_results._context_pass',side_effect=[self.baseline,trial]) as run, patch('tools.agent_memory_runtime.query_results.record_context_use') as use, patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
            result=limited_context(self.project,self.query)
            self.assertIsInstance(result,OutputLoopContext);self.assertEqual(run.call_count,2)
            use.assert_called_once();miss.assert_called_once()
            self.assertEqual(use.call_args.args[1]['query_handoff']['code_anchors'][0]['file_path'],'PipeCollector.ts')
        with patch('tools.agent_memory_runtime.query_results._context_pass',side_effect=[self.baseline,self.trial(a)]), patch('tools.agent_memory_runtime.query_results.record_context_use') as use, patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
            result=limited_context(self.project,self.query,defer_output_loop_accounting=True)
            use.assert_not_called();miss.assert_not_called()
            payload={'activated':False,'path_candidates':[],'activation_reason':'missing_log_anchor'}
            facade=ContextFacade(self.project,lambda *args:result,SimpleNamespace(build=lambda query:payload))
            final=facade.execute(self.query);self.assertIsInstance(final,OutputLoopContext)
            use.assert_called_once();miss.assert_called_once()
        with patch('tools.agent_memory_runtime.query_results._context_pass',return_value=self.baseline) as run, patch('tools.agent_memory_runtime.query_results.record_context_use') as use, patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
            limited_context(self.project,'Find BufferSession source.');self.assertEqual(run.call_count,1)
            use.assert_called_once();miss.assert_called_once()
        with patch('tools.agent_memory_runtime.query_results._context_pass',side_effect=[self.baseline,self.trial(a)]), patch('tools.agent_memory_runtime.query_results.record_context_use') as use, patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
            result=limited_context(self.project,self.query,defer_output_loop_accounting=True)
            payload={'activated':True,'path_candidates':[],'activation_reason':'test active'}
            facade=ContextFacade(self.project,lambda *args:result,SimpleNamespace(build=lambda query:payload))
            final=facade.execute(self.query);self.assertNotIsInstance(final,OutputLoopContext)
            use.assert_called_once();miss.assert_called_once()
            self.assertEqual(use.call_args.args[1]['query_handoff']['code_anchors'],self.baseline['query_handoff']['code_anchors'])

    def test_source_drift_and_inactive_enrichment(self):
        a=self.authority();r=bind_output_loop_context(self.query,self.baseline,self.trial(a))
        payload={'activated':False,'path_candidates':[],'activation_reason':'missing_log_anchor'}
        enriched=enrich_output_loop_context(r,self.query,payload,r['source_freshness'])
        self.assertIsInstance(enriched,OutputLoopContext)
        self.assertNotIsInstance(enrich_output_loop_context(r,self.query,{**payload,'activated':True},r['source_freshness']),OutputLoopContext)
        path=self.root/'PipeCollector.ts';path.write_text(path.read_text()+'class Added {}\n')
        self.assertIsNone(output_loop_context_view(r)[1])


if __name__=='__main__':unittest.main()
