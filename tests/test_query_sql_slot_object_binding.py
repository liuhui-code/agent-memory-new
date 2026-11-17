"""Original-scope object proof and non-output identity controls, no CLI."""
import copy
import json
from pathlib import Path
import unittest
import test_query_sql_slot_scope_controls as scope_tests
from tools.agent_memory_runtime import query_sql_slot_selection as sel
from tools.agent_memory_runtime.sql_slot_source import inventory_source
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist

D=Path(__file__).resolve().parents[1]/'docs/evidence/sql-method-container'
CORPUS=json.loads((D/'SOURCE-EXTENSION-CONTROLS.json').read_text())


class ObjectBindingTests(unittest.TestCase):
    def setUp(self):
        self.scope=scope_tests.ScopeControls();self.scope.setUp();self.addCleanup(self.scope.doCleanups)
        self.f=self.scope.f
        self.sources=copy.deepcopy(CORPUS['cases'][0]['sources'])
        self.f.query=CORPUS['query'];self.f.base['query']=self.f.query
        self.rebuild(self.sources)

    def rebuild(self,sources):
        self.scope.rebuild(sources)
        for row in self.f.files:
            if '/entities/' in row['file_path']:
                self.f.pool.append(dict(row,kind='file',match_reasons=['graph_neighbor','imports']))

    def issue(self):
        data=self.f.bind();self.assertIsInstance(data,sel.SqlSlotContext)
        self.assertIsNotNone(sel.sql_slot_receipt(data));return data

    def test_complete_object_view_and_noncode(self):
        data=self.issue();out=sel.compact_sql_slot(data,self.f.base)
        self.assertIsNot(out,self.f.base)
        self.assertEqual(len(out['query_handoff']['code_anchors']),3)
        self.assertTrue(all('/entities/' not in a['file_path'] for a in out['query_handoff']['code_anchors']))
        self.assertEqual(restore_whitelist(out,self.f.base),self.f.base)
        self.assertEqual(dict(data),self.f.base)

    def test_missing_admitted_entity_cannot_add_db_scope(self):
        self.f.pool[:]=[r for r in self.f.pool if '/entities/' not in r['file_path']]
        self.assertIs(self.f.bind(),self.f.base)

    def test_same_name_different_entity_paths_reject(self):
        case=next(x for x in CORPUS['cases'] if x['id']=='e22')
        self.rebuild(case['sources']);self.assertIs(self.f.bind(),self.f.base)

    def test_nonoutput_entity_bytes_and_db_identity_rechecked(self):
        data=self.issue();path=next(p for p in self.sources if '/entities/' in p)
        f=self.f.root/path;old=f.read_bytes();f.write_bytes(old+b'\n')
        self.assertIs(sel.compact_sql_slot(data,self.f.base),self.f.base)
        f.write_bytes(old);data=self.issue()
        owner=next(r for r in self.f.rows if r['file_path']==path and r['symbol_type']=='class')
        owner['symbol_key']='changed-entity-key'
        self.assertIs(sel.compact_sql_slot(data,self.f.base),self.f.base)

    def test_entity_metadata_conflict_before_binding(self):
        path=next(p for p in self.sources if '/entities/' in p)
        owner=next(r for r in self.f.rows if r['file_path']==path and r['symbol_type']=='class')
        owner['end_line']+=1
        self.assertIs(self.f.bind(),self.f.base)

    def test_entity_property_existing_index_is_authenticated(self):
        path=next(p for p in self.sources if '/entities/' in p)
        inv=inventory_source(self.sources[path]);owner=inv['declarations'][0]
        field=next(f for f in owner['fields'] if f['name']=='caption')
        template=next(r for r in self.f.rows if r['file_path']==path)
        row=dict(template,id=999,symbol_key='property:key',symbol='caption',
                 qualified_name=owner['name']+'.caption',owner_name=owner['name'],symbol_type='property',
                 start_line=field['span']['start_line'],end_line=field['span']['end_line'])
        self.f.rows.append(row);self.f.pool.append(dict(row,kind='symbol'))
        self.issue()
        for changes in ({'symbol_type':'function','qualified_name':'Wrong.caption'},
                        {'start_line':1},{'owner_name':'Wrong'}):
            original=copy.deepcopy(row);pool_original=copy.deepcopy(self.f.pool[-1])
            row.update(changes);self.f.pool[-1].update(changes)
            self.assertIs(self.f.bind(),self.f.base)
            row.clear();row.update(original);self.f.pool[-1]=pool_original
        data=self.issue();row['end_line']+=1
        self.assertIs(sel.compact_sql_slot(data,self.f.base),self.f.base)

    def test_missing_each_output_method_stays_missing(self):
        initial=copy.deepcopy(self.f.pool)
        for name in ('scanLines','submit','build'):
            self.f.pool[:]=[r for r in initial if r.get('symbol')!=name]
            self.assertIs(self.f.bind(),self.f.base,name)
        self.f.pool[:]=initial

    def test_budget_atomic_fallback_and_excluded_type_reference(self):
        data=self.issue();small=copy.deepcopy(self.f.base);small['output_budget']['target_tokens']=10
        self.assertIs(sel.compact_sql_slot(data,small),small)
        self.f.query=CORPUS['query'].rstrip('。')+'，不要返回 ArchiveLine。'
        self.f.base['query']=self.f.query
        self.issue()

if __name__=='__main__':unittest.main()
