# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime.query_lifecycle_selection import (
    qualify_lifecycle,lifecycle_request,lifecycle_focus,LifecycleTrial,LifecycleContext,
    bind_lifecycle_context,lifecycle_context_view,enrich_lifecycle_context,
)
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.query_code_selection import diverse_code_matches

D=Path(__file__).parents[1]/'docs/evidence/lifecycle-source-prerequisites'


class Rows:
    def __init__(self,rows,files,edges):self.rows=rows;self.files=files;self.edges=edges
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def execute(self,sql,args):
        return self.rows if 'FROM code_symbols' in sql else self.files if 'FROM code_files' in sql else self.edges


class LifecycleSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.load('original-four','lifecycle-1')

    def load(self,family,case):
        p=json.loads((D/'protocol.json').read_text());f=next(x for x in p['families']if x['id']==family)
        for path,source in f['sources'].items():
            target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source)
        self.example=next(x for x in json.loads((D/'before-public.json').read_text())if x['case']['id']==case)
        t=json.loads((D/self.example['trace']).read_text());self.items=next(x for x in t if x['function']=='focus_code_candidates')['items']
        self.rows=self.example['symbols'];self.files=[r for r in self.items if r.get('kind')=='file']
        self.edges=json.loads((D/('before-edges-'+family+'.json')).read_text())
        self.query=self.example['case']['query'];self.project=SimpleNamespace(root=self.root,project_id=self.rows[0]['project_id'])
        self.baseline=copy.deepcopy(self.example['raw']);self.baseline['project_path']=str(self.root)

    def authority(self):
        with patch('tools.agent_memory_runtime.query_lifecycle_selection.connect',return_value=Rows(self.rows,self.files,self.edges)):
            return qualify_lifecycle(self.project,self.query,self.items)

    def trial(self,authority):
        result=LifecycleTrial(copy.deepcopy(self.baseline));result._lifecycle_authority=authority
        result['wiki_matches']=lifecycle_focus(authority,self.query,self.items)
        result['query_handoff']['code_anchors']=[]
        return result

    def test_full_request_and_source_identity(self):
        self.assertTrue(lifecycle_request(self.query));a=self.authority();self.assertIsNotNone(a)
        self.assertEqual([r['parsed']['owner']for r in a._receipts],['BufferSession'])
        for c in json.loads((D/'protocol.json').read_text())['request_negatives']:
            self.assertFalse(lifecycle_request(c['query']))
        self.assertFalse(lifecycle_request('Find the owner combining lifecycle restore, current text state and storage commit after restart.'))

    def test_source_view_keeps_public_baseline(self):
        a=self.authority();result=bind_lifecycle_context(self.query,self.baseline,self.trial(a))
        self.assertIsInstance(result,LifecycleContext);self.assertEqual(dict(result),self.baseline)
        payload=compact_context(result);anchors=payload['query_handoff']['code_anchors']
        self.assertEqual([x['file_path']for x in anchors],['BufferSession.ets'])
        self.assertEqual(anchors[0]['source_excerpts'][0]['end_line'],12)
        self.assertEqual(anchors[0]['source_excerpts'][0]['source'],'validated_request_snapshot')
        for clone in [dict(result),copy.copy(result),copy.deepcopy(result),json.loads(json.dumps(result))]:
            self.assertIsNone(lifecycle_context_view(clone)[1])
            self.assertEqual(compact_context(clone)['query_handoff'],compact_context(self.baseline)['query_handoff'])

    def test_original_query_pool_and_receipt_mutation(self):
        a=self.authority();self.assertIsNone(lifecycle_focus(a,self.query+'extra',self.items))
        changed=copy.deepcopy(self.items);changed[0]['id']+=1
        self.assertIsNone(lifecycle_focus(a,self.query,changed))
        r=bind_lifecycle_context(self.query,self.baseline,self.trial(a));r._view['query']='changed'
        self.assertIsNone(lifecycle_context_view(r)[1])

    def test_all_positive_files_survive_lexical_similarity(self):
        self.load('two-complete-owners','two-complete-owners');a=self.authority();self.assertEqual(len(a._receipts),2)
        selected=diverse_code_matches(copy.deepcopy(self.items),12,query=self.query,lifecycle_authority=a)
        self.assertEqual({x['file_path']for x in selected},{'BufferSession.ets','EditorSession.ets'})
        r=bind_lifecycle_context(self.query,self.baseline,self.trial(a));self.assertIsInstance(r,LifecycleContext)
        payload=compact_context(r);self.assertEqual(len(payload['query_handoff']['code_anchors']),2)

    def test_edge_and_node_freshness_are_independent(self):
        edge=next(e for e in self.edges if e.get('evidence_kind')=='static_semantic_calls')
        original=edge['evidence'];v=json.loads(original);v['source_digest']='0'*64;edge['evidence']=json.dumps(v)
        self.assertIsNone(self.authority());edge['evidence']=original
        edge['valid_to']='old';self.assertIsNone(self.authority())

    def test_both_baseline_and_trial_protection(self):
        a=self.authority()
        for side in ('baseline','trial'):
            for key in ('identity_match','log_identity_match','graph_neighbor','graph_relation'):
                b=copy.deepcopy(self.baseline);t=self.trial(a);h=(b if side=='baseline' else t)['query_handoff'];h['code_anchors']=[{'file_path':'Protected.ets',key:True}]
                self.assertIs(bind_lifecycle_context(self.query,b,t),b)

    def test_accounting_direct_and_facade_once(self):
        from tools.agent_memory_runtime.query_results import limited_context
        from tools.agent_memory_runtime.context_facade import ContextFacade
        a=self.authority();trial=self.trial(a)
        with patch('tools.agent_memory_runtime.query_results._context_pass',side_effect=[self.baseline,trial]) as run, patch('tools.agent_memory_runtime.query_results.record_context_use') as use, patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
            result=limited_context(self.project,self.query)
            self.assertIsInstance(result,LifecycleContext);self.assertEqual(run.call_count,2)
            use.assert_called_once();miss.assert_called_once()
            self.assertEqual(use.call_args.args[1]['query_handoff']['code_anchors'][0]['file_path'],'BufferSession.ets')
        with patch('tools.agent_memory_runtime.query_results._context_pass',side_effect=[self.baseline,self.trial(a)]), patch('tools.agent_memory_runtime.query_results.record_context_use') as use, patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
            result=limited_context(self.project,self.query,defer_lifecycle_accounting=True)
            use.assert_not_called();miss.assert_not_called()
            payload={'activated':False,'path_candidates':[],'activation_reason':'missing_log_anchor'}
            facade=ContextFacade(self.project,lambda *args:result,SimpleNamespace(build=lambda query:payload))
            final=facade.execute(self.query);self.assertIsInstance(final,LifecycleContext)
            use.assert_called_once();miss.assert_called_once()
        with patch('tools.agent_memory_runtime.query_results._context_pass',return_value=self.baseline) as run, patch('tools.agent_memory_runtime.query_results.record_context_use'), patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty'):
            limited_context(self.project,'Find BufferSession source.');self.assertEqual(run.call_count,1)

    def test_source_drift_and_inactive_enrichment(self):
        a=self.authority();r=bind_lifecycle_context(self.query,self.baseline,self.trial(a))
        payload={'activated':False,'path_candidates':[],'activation_reason':'missing_log_anchor'}
        enriched=enrich_lifecycle_context(r,self.query,payload,r['source_freshness'])
        self.assertIsInstance(enriched,LifecycleContext)
        self.assertNotIsInstance(enrich_lifecycle_context(r,self.query,{**payload,'activated':True},r['source_freshness']),LifecycleContext)
        path=self.root/'BufferSession.ets';path.write_text(path.read_text()+'class Added {}\n')
        self.assertIsNone(lifecycle_context_view(r)[1])


if __name__=='__main__':unittest.main()
