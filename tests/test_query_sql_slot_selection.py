"""Development binding/consumption controls, not product query acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime.sql_slot_source import inventory_source
from tools.agent_memory_runtime.query_sql_slot_request import sql_slot_request
from tools.agent_memory_runtime import query_sql_slot_snapshot as snap
from tools.agent_memory_runtime import query_sql_slot_selection as sel
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.context_sufficiency import diagnosis_sufficiency
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens

CORPUS=Path(__file__).resolve().parents[1]/'docs/evidence/sql-method-container/SOURCE-CONTROLS.json'


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.project=SimpleNamespace(root=self.root,project_id='independent')
        case=json.loads(CORPUS.read_text())['source_cases'][0]
        self.query=case['request']['query'];self.descriptor=sql_slot_request(self.query)
        self.files=[];self.rows=[];self.pool=[]
        for i,(name,source) in enumerate(case['sources'].items(),1):
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source)
            digest=hashlib.sha256(source.encode()).hexdigest()
            f=dict(id=i,project_id='independent',file_path=name,language='ArkTS',source_digest=digest,index_generation=1)
            self.files.append(f)
            for owner in inventory_source(source)['declarations']:
                kind='component' if owner['kind']=='struct' else 'service'
                for decl in [owner]+owner['methods']:
                    isowner=decl is owner
                    row=dict(f,id=len(self.rows)+1,symbol=decl['name'],symbol_key='key:'+str(len(self.rows)+1),
                        qualified_name=owner['name']+('' if isowner else '.'+decl['name']),
                        start_line=decl['span']['start_line'],end_line=decl['span']['end_line'],
                        owner_name='' if isowner else owner['name'],owner_kind=kind,
                        symbol_type=('component' if kind=='component' else 'class') if isowner else 'function',
                        semantic_adapter='arkts-static@1.2',evidence_class='static')
                    self.rows.append(row)
                    if decl['name'] in ('findRows','submit','build'):self.pool.append(dict(row,kind='symbol'))
        self.mock=patch.object(snap,'project_rows',side_effect=lambda *_:(copy.deepcopy(self.files),copy.deepcopy(self.rows)))
        self.mock.start();self.addCleanup(self.mock.stop)
        h=dict(code_anchors=[],log_anchors=[],callable_evidence=dict(schema_version='agent-callable-evidence/v1',
            certainty='unavailable',primary=None,alternatives=[],boundary='retrieval_evidence_not_root_cause'),
            path_context=dict(activated=False,path_candidates=[]))
        self.base=dict(query=self.query,query_handoff=h,source_freshness=dict(status='current',generation=1),
            evidence_gaps=['no_code_anchor','custom'],output_budget=dict(target_tokens=1500,estimated_tokens=0,truncated=False))
        self.base['sufficiency']=diagnosis_sufficiency(h,self.base['evidence_gaps'],self.base['source_freshness'])

    def bind(self):return sel.bind_sql_slot_context(self.project,self.query,self.base,self.pool)

    def test_actual_request_source_bind_and_compact_atomic(self):
        data=self.bind();self.assertIsInstance(data,sel.SqlSlotContext)
        self.assertEqual(dict(data),self.base)
        result=sel.compact_sql_slot(data,self.base)
        self.assertIsNot(result,self.base)
        self.assertEqual(len(result['query_handoff']['code_anchors']),3)
        self.assertEqual(result['query_handoff']['callable_evidence']['certainty'],'uncertain')
        self.assertIsNone(result['query_handoff']['callable_evidence']['primary'])
        self.assertEqual(restore_whitelist(result,self.base),self.base)
        self.assertEqual(result['output_budget']['estimated_tokens'],estimate_payload_tokens(result))

    def test_missing_each_method_root_does_not_db_complete(self):
        original=copy.deepcopy(self.pool)
        for i in range(3):
            self.pool=original[:i]+original[i+1:]
            self.assertIs(self.bind(),self.base)

    def test_copy_json_and_plain_dict_no_authority(self):
        data=self.bind()
        for other in (dict(data),copy.copy(data),copy.deepcopy(data),json.loads(json.dumps(data))):
            self.assertIsNone(sel.sql_slot_receipt(other))
        self.assertIsNone(sel.sql_slot_receipt(sel.SqlSlotContext(data)))

    def test_query_pool_anchor_and_scope_tamper(self):
        mutations=[lambda d:d.update(query=self.query+' '),lambda d:d._pool.reverse(),
            lambda d:d._qualified['anchors'][0]['source_excerpts'][0].update(content='same\nlines\nhere\nnow'),
            lambda d:d._qualified['scope']['digests'].update({'new':'0'*64}),
            lambda d:d._descriptor.update(method='different')]
        for mutate in mutations:
            data=self.bind();mutate(data);self.assertIsNone(sel.sql_slot_receipt(data))

    def test_db_and_source_consumption_checks(self):
        data=self.bind();self.rows[0]['index_generation']=2
        self.assertIsNone(sel.sql_slot_receipt(data));self.rows[0]['index_generation']=1
        path=self.root/self.files[0]['file_path'];path.write_bytes(path.read_bytes()+b'\n')
        self.assertIsNone(sel.sql_slot_receipt(data))

    def test_unknown_callable_nested_and_budget_rollback(self):
        data=self.bind()
        bad=copy.deepcopy(self.base);bad['query_handoff']['callable_evidence']['primary']={'file_path':'a','symbol':'b','source_range':{'start_line':1,'end_line':2,'unknown':{}}}
        self.assertIs(sel.compact_sql_slot(data,bad),bad)
        small=copy.deepcopy(self.base);small['output_budget']['target_tokens']=10
        self.assertIs(sel.compact_sql_slot(data,small),small)
        huge=copy.deepcopy(self.base);huge['retained']='word '*6000
        self.assertIs(sel.compact_sql_slot(data,huge),huge)

    def test_actual_compact_path_and_log_authority_rechecked(self):
        data=self.bind()
        bad=copy.deepcopy(self.base);bad['query_handoff']['path_context']['activated']=True
        self.assertIs(sel.compact_sql_slot(data,bad),bad)
        bad=copy.deepcopy(self.base);bad['query_handoff']['log_anchors']=[dict(log_identity_match=True)]
        self.assertIs(sel.compact_sql_slot(data,bad),bad)

    def test_existing_state_index_conflict_even_when_pool_matches(self):
        sourcepath=next(n for n in (r['file_path'] for r in self.files) if '/pages/' in n)
        source=(self.root/sourcepath).read_text();owner=inventory_source(source)['declarations'][0]
        field=next(f for f in owner['fields'] if f['name']=='rows')
        template=next(r for r in self.rows if r['file_path']==sourcepath)
        row=dict(template,id=100,symbol='rows',symbol_key='state-key',qualified_name=owner['name']+'.rows',
            symbol_type='state',owner_name='',owner_kind='',start_line=field['span']['start_line'],end_line=field['span']['end_line'])
        self.rows.append(row);self.pool.append(dict(row,kind='symbol'))
        self.assertIsInstance(self.bind(),sel.SqlSlotContext)
        for key,value in [('start_line',1),('owner_name','Wrong'),('qualified_name','Wrong.rows'),('symbol_type','function')]:
            old=row[key];row[key]=value;self.pool[-1][key]=value
            self.assertIs(self.bind(),self.base);row[key]=old;self.pool[-1][key]=old
        row.update(symbol_type='function',qualified_name='Wrong.rows')
        self.pool[-1].update(symbol_type='function',qualified_name='Wrong.rows')
        self.assertIs(self.bind(),self.base)

    def test_facade_single_accounting_and_dispatch(self):
        from tools.agent_memory_runtime.context_facade import ContextFacade
        from tools.agent_memory_runtime.context_compact_dispatch import dispatch_compact_context
        data=self.bind();data._pending_accounting=True
        paths=SimpleNamespace(build=lambda q:copy.deepcopy(self.base['query_handoff']['path_context']))
        facade=ContextFacade(self.project,lambda *a:data,paths)
        with patch('tools.agent_memory_runtime.context_facade.filter_fresh_path_context',side_effect=lambda p,path,f:(path,f)), \
             patch('tools.agent_memory_runtime.query_results.record_context_use') as used, \
             patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as missed, \
             patch('tools.agent_memory_runtime.context_compact._compact_context',return_value=self.base):
            result=facade.execute(self.query)
            self.assertIsInstance(result,sel.SqlSlotContext)
            used.assert_called_once();missed.assert_called_once()
            self.assertEqual(len(used.call_args.args[1]['query_handoff']['code_anchors']),3)
            self.assertEqual(dict(result),self.base)
            facade.execute(self.query)
            used.assert_called_once();missed.assert_called_once()
        compact=dispatch_compact_context(result,lambda x:self.base)
        self.assertEqual(len(compact['query_handoff']['code_anchors']),3)

    def test_enrich_preserves_and_blocks_active_path(self):
        data=self.bind();h=self.base['query_handoff'];fresh=self.base['source_freshness']
        self.assertIsInstance(sel.enrich_sql_slot(data,self.query,h['path_context'],fresh),sel.SqlSlotContext)
        self.assertNotIsInstance(sel.enrich_sql_slot(data,self.query,dict(activated=True,path_candidates=[]),fresh),sel.SqlSlotContext)

if __name__=='__main__':unittest.main()
