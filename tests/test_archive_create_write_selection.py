from copy import copy, deepcopy
import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime.query_archive_create_write_selection import (
    ArchiveCreateWriteContext, bind_archive_create_write_context,
    archive_create_write_receipt, compact_archive_create_write,
    enrich_archive_create_write, accounting_archive_create_write)
from tests.archive_create_write_test_support import fixture, prepare, ordinary_context
from tools.agent_memory_runtime.storage import connect
class Rows:
    def __init__(self,s,f):self.s,self.f=s,f
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def execute(self,sql,args):return self.s if 'FROM code_symbols' in sql else self.f
class ArchiveSelectionTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        self.project=prepare(self.root, 'two-positive')
        self.root=self.project.root
        case=next(c for c in fixture()['cases'] if c['id']=='two-positive-head')
        self.query=case['query']
        self.base,self.compact,self.pool=ordinary_context(self.project,self.query)
        with connect(self.project) as connection:
            self.rows=[dict(r) for r in connection.execute('SELECT * FROM code_symbols WHERE project_id=?',(self.project.project_id,))]
            self.files=[dict(r) for r in connection.execute('SELECT * FROM code_files WHERE project_id=?',(self.project.project_id,))]
    def bind(self):
        with patch('tools.agent_memory_runtime.query_archive_create_write_selection.connect',return_value=Rows(self.rows,self.files)):
            return bind_archive_create_write_context(self.project,self.query,self.base,self.pool)
    def test_complete_positive_set_and_no_raw_change(self):
        r=self.bind();self.assertIsInstance(r,ArchiveCreateWriteContext);self.assertEqual(dict(r),self.base)
        after=compact_archive_create_write(r,self.compact)
        self.assertEqual([a['file_path']for a in after['query_handoff']['code_anchors']],['DeliveryBuffer.ets','PackageStager.ets'])
        for a in after['query_handoff']['code_anchors']:
            self.assertIn('await unzip(',a['source_excerpts'][0]['content']);self.assertFalse(a['source_excerpts'][0]['truncated'])
        self.assertLessEqual(after['output_budget']['estimated_tokens'],1500)
        self.assertEqual(after['query_handoff']['log_anchors'],self.compact['query_handoff']['log_anchors'])
        self.assertEqual(dict(r),self.base)
    def test_copy_serialization_mutation_replay(self):
        r=self.bind()
        for x in [dict(r),copy(r),deepcopy(r),json.loads(json.dumps(r))]:self.assertIsNone(archive_create_write_receipt(x))
        r['query']='Return archive creation and write ownership.';self.assertIsNone(archive_create_write_receipt(r))
        r=self.bind();r._anchors[0]['record_ids']=[999];self.assertIsNone(archive_create_write_receipt(r))
        r=self.bind();r._pool[0]['score']=999;self.assertIsNone(archive_create_write_receipt(r))
    def test_method_identity_all_fields(self):
        original=deepcopy(self.rows)
        for key,value in [('id',0),('project_id','other'),('qualified_name','Other.store'),('owner_name','Other'),('owner_kind','Other'),('semantic_adapter','unknown'),('evidence_class','unknown'),('source_digest','0'*64),('index_generation',99),('symbol_type','class'),('start_line',1)]:
            self.rows=deepcopy(original);next(x for x in self.rows if x['symbol']=='store')[key]=value
            self.assertIs(self.bind(),self.base,key)
    def test_file_identity_and_duplicate_aliases(self):
        original=deepcopy(self.pool)
        for key,value in [('id',999),('project_id','other'),('source_digest','0'*64),('index_generation',99),('language','Java')]:
            self.pool=deepcopy(original);next(x for x in self.pool if x['kind']=='file' and x['file_path']=='PackageStager.ets')[key]=value
            self.assertIs(self.bind(),self.base,key)
        self.pool=original;bad=deepcopy(next(x for x in self.rows if x['symbol']=='store'));bad['source_digest']='0'*64;self.rows.append(bad)
        self.assertIs(self.bind(),self.base)
    def test_missing_method_and_owner_identity(self):
        self.pool=[x for x in self.pool if not(x['kind']=='symbol' and x['symbol']=='store')]
        self.assertIs(self.bind(),self.base)
        self.setUp();next(x for x in self.rows if x['symbol']=='PackageStager')['qualified_name']='Unrelated'
        self.assertIs(self.bind(),self.base)
    def test_final_source_and_freshness(self):
        r=self.bind();(self.root/'PackageStager.ets').write_text('changed after binding')
        self.assertIs(compact_archive_create_write(r,self.compact),self.compact)
        self.setUp();r=self.bind();fresh=dict(self.base['source_freshness'],status='stale')
        self.assertNotIsInstance(enrich_archive_create_write(r,self.query,self.base['query_handoff']['path_context'],fresh),ArchiveCreateWriteContext)
    def test_active_path_graph_and_identity_protection(self):
        original=deepcopy(self.base)
        for key in ['activated','wrapped_log_evidence','path_candidates','seeds']:
            self.base=deepcopy(original);self.base['query_handoff']['path_context'][key]=True
            self.assertIs(self.bind(),self.base,key)
        self.base=original;pool=deepcopy(self.pool)
        for key in ['identity_match','log_identity_match','graph_neighbor','graph_relation']:
            self.pool=deepcopy(pool);self.pool[0][key]=True;self.assertIs(self.bind(),self.base,key)
    def test_pending_missing_path_no_adoption(self):
        self.base['query_handoff'].pop('path_context');r=self.bind();self.assertIsInstance(r,ArchiveCreateWriteContext)
        self.assertIs(compact_archive_create_write(r,self.compact),self.compact)
        self.assertIs(accounting_archive_create_write(r),r)
    def test_budget_overflow_whole_fallback(self):
        r=self.bind();baseline=deepcopy(self.compact);baseline['output_budget']['target_tokens']=100
        self.assertIs(compact_archive_create_write(r,baseline),baseline)
    def test_facade_once_success_or_fallback(self):
        from tools.agent_memory_runtime.context_facade import ContextFacade
        for path in [dict(activated=False,path_candidates=[]),dict(activated=True,path_candidates=[])]:
            r=self.bind();r._pending_accounting=True
            facade=ContextFacade(self.project,lambda *args:r,SimpleNamespace(build=lambda query:path))
            with patch('tools.agent_memory_runtime.context_facade.filter_fresh_path_context',return_value=(path,r['source_freshness'])),patch('tools.agent_memory_runtime.query_results.record_context_use')as use,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
                result=facade.execute(self.query);use.assert_called_once();miss.assert_called_once()
                self.assertEqual(isinstance(result,ArchiveCreateWriteContext),not path['activated'])
    def test_nonempty_unmatched_log_and_unknown_noncode_preserved(self):
        from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
        from tools.agent_memory_runtime.context_sufficiency import diagnosis_sufficiency
        log={'message_template':'background timer idle','file_path':'Timer.ts','function':'tick','level':'info'}
        self.base['query_handoff']['log_anchors']=[deepcopy(log)]
        r=self.bind();self.assertIsInstance(r,ArchiveCreateWriteContext)
        baseline=deepcopy(self.compact);baseline['query_handoff']['log_anchors']=[deepcopy(log)]
        baseline['query_handoff']['path_context']['sentinel']={'untouched':[1,2]}
        baseline['query_handoff']['relation_hints']=[{'opaque':'retained'}]
        baseline['unknown_future_field']={'a':[3]}
        baseline['sufficiency']=diagnosis_sufficiency(baseline['query_handoff'],baseline['evidence_gaps'],baseline['source_freshness'])
        after=compact_archive_create_write(r,baseline)
        self.assertIsNot(after,baseline);self.assertEqual(restore_whitelist(after,baseline),baseline)
        self.assertEqual(after['query_handoff']['log_anchors'],[log])
    def test_real_matched_log_identity_protects(self):
        from tools.agent_memory_runtime.log_event_identity import event_match
        log={'message_template':'archive creation and write ownership','file_path':'Audit.ts','function':'notice','level':'info'}
        self.assertGreater(event_match(log,self.query)['priority'],0)
        self.base['query_handoff']['log_anchors']=[log]
        self.assertIs(self.bind(),self.base)
    def test_source_escape_and_member_alias_rejected(self):
        positive=self.root/'PackageStager.ets';source=positive.read_text();positive.unlink()
        with tempfile.TemporaryDirectory()as other:
            target=Path(other)/'outside.ets';target.write_text(source);positive.symlink_to(target)
            self.assertIs(self.bind(),self.base)
        self.setUp();row=deepcopy(next(x for x in self.pool if x.get('kind')=='symbol' and x['symbol']=='store'))
        row['index_generation']=999;self.pool.append(row);self.assertIs(self.bind(),self.base)

    def test_missing_unreadable_invalid_and_oversize_source_whole_fallback(self):
        target=self.root/'PackageStager.ets';original=target.read_bytes()
        target.unlink();self.assertIs(self.bind(),self.base)
        for data in [b'\xff',b'x'*(2*1024*1024+1)]:
            target.write_bytes(data);self.assertIs(self.bind(),self.base)
        target.write_bytes(original)
        original_open=Path.open
        def denied(path,*args,**kwargs):
            if path==target:raise PermissionError('controlled unreadable source')
            return original_open(path,*args,**kwargs)
        with patch.object(Path,'open',denied):self.assertIs(self.bind(),self.base)

    def test_cross_path_symbol_aliases_whole_fallback(self):
        original=deepcopy(self.pool)
        for change in [('file_path','DifferentPath.ets'),('qualified_name','Other.store'),('id',999),('symbol_key','other-key')]:
            self.pool=deepcopy(original)
            alias=deepcopy(next(x for x in self.pool if x.get('kind')=='symbol' and x['symbol']=='store'))
            alias[change[0]]=change[1];self.pool.append(alias)
            self.assertIs(self.bind(),self.base,change)
