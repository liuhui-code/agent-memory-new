# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from copy import copy, deepcopy
import hashlib, json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime.query_cache_scan_selection import (
    bind_cache_scan_context, cache_scan_context_view, CacheScanContext, enrich_cache_scan_context)
from tools.agent_memory_runtime.context_compact import compact_context

D = Path(__file__).parents[1]/'docs/evidence'
P = json.loads((D/'cache-eviction-current/protocol.json').read_text())
B = json.loads((D/'cache-positive-scan-current/before.json').read_text())
Q = P['queries'][0]['query']

class Rows:
    def __init__(self, rows, files): self.rows, self.files = rows, files
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql, args): return self.rows if 'FROM code_symbols' in sql else self.files

class CacheScanSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, source in P['sources'].items(): (self.root/name).write_text(source)
        self.rows = deepcopy(B['symbols'])
        self.project = SimpleNamespace(root=self.root, project_id=self.rows[0]['project_id'])
        self.base = deepcopy(B['public'][Q]['raw']); self.base['project_path'] = str(self.root)
        self.files = [dict(project_id=self.project.project_id, file_path=name,
            source_digest=hashlib.sha256(source.encode()).hexdigest(), index_generation=1)
            for name,source in P['sources'].items()]
    def bind(self):
        with patch('tools.agent_memory_runtime.query_cache_scan_selection.connect', return_value=Rows(self.rows,self.files)):
            return bind_cache_scan_context(self.project,Q,self.base)
    def test_positive_snapshot_not_unique_owner_or_timestamp(self):
        result = self.bind(); self.assertIsInstance(result,CacheScanContext)
        self.assertEqual(dict(result),self.base)
        out = compact_context(result); h = out['query_handoff']
        self.assertEqual([a['file_path'] for a in h['code_anchors']],['ExpiryStore.ts'])
        e = h['code_anchors'][0]['source_excerpts'][0]
        self.assertEqual((e['start_line'],e['end_line']),(3,14)); self.assertFalse(e['truncated'])
        self.assertEqual(e['content'],'\n'.join(P['sources']['ExpiryStore.ts'].splitlines()[2:14]))
        self.assertIsNone(h['callable_evidence']['primary'])
        self.assertEqual(h['callable_evidence']['certainty'],'uncertain')
        self.assertIn('non_exhaustive_runtime_eviction_and_timestamp_unproven',h['callable_evidence']['boundary'])
        self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
    def test_copy_json_query_and_view_tamper(self):
        result=self.bind()
        for value in [dict(result),copy(result),deepcopy(result),json.loads(json.dumps(result))]:
            self.assertEqual(value,self.base); self.assertIsNone(cache_scan_context_view(value)[1])
        for mutation in [lambda r:r.update(query=Q.replace('Locate','Find')),
                         lambda r:r._view['query_handoff']['code_anchors'].clear(),
                         lambda r:setattr(r,'_receipts',()),lambda r:delattr(r,'_binding')]:
            result=self.bind(); mutation(result); self.assertIsNone(cache_scan_context_view(result)[1])
    def test_same_read_snapshot_not_late_source(self):
        result=self.bind(); (self.root/'ExpiryStore.ts').write_text('changed after request snapshot')
        with patch('tools.agent_memory_runtime.context_compact.attach_source_excerpts',side_effect=AssertionError('late read')):
            self.assertIn('this.records.delete(chosen)',compact_context(result)['query_handoff']['code_anchors'][0]['source_excerpts'][0]['content'])
    def test_freshness_identity_conflicts_fail_closed(self):
        original=deepcopy(self.rows)
        for field,value in [('source_digest','0'*64),('start_line',4),('owner_name','Other'),
                            ('index_generation',2),('symbol_key',''),('semantic_adapter','unknown'),('id',0)]:
            self.rows=deepcopy(original); row=next(r for r in self.rows if r['file_path']=='ExpiryStore.ts' and r['symbol']=='trim')
            row[field]=value; self.assertIs(self.bind(),self.base,field)
        self.rows=deepcopy(original); self.rows.append(deepcopy(next(r for r in self.rows if r['file_path']=='ExpiryStore.ts' and r['symbol']=='trim')))
        self.assertIs(self.bind(),self.base)
        self.rows=original; self.files.append(deepcopy(next(r for r in self.files if r['file_path']=='ExpiryStore.ts')))
        self.assertIs(self.bind(),self.base)
    def test_owner_and_recalled_identity(self):
        original=deepcopy(self.rows)
        for field,value in [('start_line',2),('end_line',16),('index_generation',2)]:
            self.rows=deepcopy(original); next(r for r in self.rows if r['symbol']=='ExpiryStore')[field]=value
            self.assertIs(self.bind(),self.base,field)
        self.rows=original
        row=next(r for r in self.base['wiki_matches'] if r['file_path']=='ExpiryStore.ts')
        row['symbol_key']='wrong'; self.assertIs(self.bind(),self.base)
    def test_unknown_competitor_not_absence_and_stale_positive(self):
        (self.root/'CacheMonitor.ts').write_text('unknown syntax `anything`')
        self.assertIsInstance(self.bind(),CacheScanContext)
        (self.root/'ExpiryStore.ts').write_text(P['sources']['ExpiryStore.ts']+'\n// changed')
        self.assertIs(self.bind(),self.base)
    def test_protected_context_and_escape(self):
        h=self.base['query_handoff']; old=deepcopy(h)
        for key in ['identity_match','log_identity_match','graph_neighbor','graph_relation']:
            h['code_anchors']=[{'file_path':'protected.ts',key:True}]; self.assertIs(self.bind(),self.base,key)
        self.base['query_handoff']=deepcopy(old); h=self.base['query_handoff']; h['log_anchors']=[{}]
        self.assertIs(self.bind(),self.base)
        h['log_anchors']=[]; h['path_context']['activated']=True; self.assertIs(self.bind(),self.base)
        self.base['query_handoff']=old; self.base['wiki_matches'].append({'file_path':'../outside.ts'})
        self.assertIs(self.bind(),self.base)
    def clone(self,name):
        source=P['sources']['ExpiryStore.ts'].replace('ExpiryStore',name); file=name+'.ts'
        (self.root/file).write_text(source); digest=hashlib.sha256(source.encode()).hexdigest()
        for collection in (self.rows,self.base['wiki_matches']):
            clones=[]
            for r in collection:
                if r['file_path']=='ExpiryStore.ts':
                    r=deepcopy(r); r.update(file_path=file,source_digest=digest,id=r['id']+100*len(self.files),symbol_key=name+':'+r['symbol_key'])
                    for key in ('owner_name','symbol','qualified_name'): r[key]=r[key].replace('ExpiryStore',name)
                    clones.append(r)
            collection.extend(clones)
        self.files.append(dict(project_id=self.project.project_id,file_path=file,source_digest=digest,index_generation=1))
    def test_multiple_positive_atomic_limits(self):
        for i in range(2):
            self.clone('Another'+str(i)); result=self.bind(); self.assertIsInstance(result,CacheScanContext)
            self.assertEqual(len(compact_context(result)['query_handoff']['code_anchors']),i+2)
        self.clone('Fourth'); self.assertIs(self.bind(),self.base)
    def test_budget_and_facade_enrichment(self):
        with patch('tools.agent_memory_runtime.context_compact._compact_context',return_value={'query_handoff':{'code_anchors':[]}}):
            self.assertIs(self.bind(),self.base)
        r=self.bind(); empty=dict(activated=False,path_candidates=[])
        good=enrich_cache_scan_context(r,Q,empty,r['source_freshness']); self.assertIsInstance(good,CacheScanContext)
        for path in [dict(activated=True,path_candidates=[]),dict(activated=False,path_candidates=[],gaps=['unknown']),dict(activated=False,path_candidates=[],extra=True)]:
            self.assertNotIsInstance(enrich_cache_scan_context(r,Q,path,r['source_freshness']),CacheScanContext)
    def test_unsupported_requests_no_source_work(self):
        with patch('tools.agent_memory_runtime.query_cache_scan_selection.connect',side_effect=AssertionError('must not inspect')):
            for q in [P['queries'][1]['query'],P['queries'][2]['query'],P['queries'][3]['query'],Q+' and return literal text']:
                self.assertIs(bind_cache_scan_context(self.project,q,self.base),self.base)
    def test_accounting_uses_adopted_view_once(self):
        from tools.agent_memory_runtime.query_results import limited_context
        result=self.bind()
        with patch('tools.agent_memory_runtime.query_results._context_pass',return_value=self.base) as call, \
             patch('tools.agent_memory_runtime.query_cache_scan_selection.bind_cache_scan_context',return_value=result), \
             patch('tools.agent_memory_runtime.query_results.record_context_use') as record, \
             patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
            self.assertIs(limited_context(self.project,Q),result)
            self.assertEqual(call.call_count,1); record.assert_called_once(); miss.assert_called_once()
            self.assertIs(record.call_args.args[1],result._view)

    def test_facade_success_and_fallback_record_once_after_enrichment(self):
        from tools.agent_memory_runtime.context_facade import ContextFacade
        for path in [dict(activated=False,path_candidates=[]),dict(activated=True,path_candidates=[])]:
            result=self.bind(); result._pending_accounting=True
            facade=ContextFacade(self.project,lambda *args:result,SimpleNamespace(build=lambda query:path))
            with patch('tools.agent_memory_runtime.context_facade.filter_fresh_path_context',return_value=(path,result['source_freshness'])), \
                 patch('tools.agent_memory_runtime.query_results.record_context_use') as record, \
                 patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
                enriched=facade.execute(Q); record.assert_called_once(); miss.assert_called_once()
                adopted,_=cache_scan_context_view(enriched)
                self.assertIs(record.call_args.args[1],adopted)
                self.assertEqual(isinstance(enriched,CacheScanContext),not path['activated'])

    def test_semantic_identity_and_conflicting_aliases(self):
        original=deepcopy(self.base)
        for field,value in [('owner_name','Wrong'),('owner_kind','class'),('semantic_adapter','unknown'),
                            ('evidence_class','dynamic'),('symbol_type','class')]:
            self.base=deepcopy(original)
            next(r for r in self.base['wiki_matches'] if r['file_path']=='ExpiryStore.ts')[field]=value
            self.assertIs(self.bind(),self.base,field)
        self.base=original
        original_rows=deepcopy(self.rows)
        for field,value in [('qualified_name','Other'),('owner_name','Other'),('owner_kind','')]:
            self.rows=deepcopy(original_rows)
            next(r for r in self.rows if r['symbol']=='ExpiryStore')[field]=value
            self.assertIs(self.bind(),self.base,field)
        self.rows=original_rows
        alias=deepcopy(next(r for r in self.rows if r['symbol']=='trim' and r['file_path']=='ExpiryStore.ts'))
        alias['start_line']=4; self.rows.append(alias)
        self.assertIs(self.bind(),self.base)
