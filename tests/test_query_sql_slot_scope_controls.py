"""Independent temporary-fixture scope controls; never execute product queries."""
import copy
import hashlib
import unittest
import test_query_sql_slot_selection as fixtures
from tools.agent_memory_runtime import query_sql_slot_selection as sel
from tools.agent_memory_runtime.sql_slot_source import inventory_source


class ScopeControls(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.BindingTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.sources = {r['file_path']: (self.f.root/r['file_path']).read_text()
                        for r in self.f.files}
        self.sql = next(p for p in self.sources if '/services/' in p)
        self.ui = next(p for p in self.sources if '/pages/' in p)

    def rebuild(self, sources):
        """Rebuild complete synthetic DB/pool consistently, never issue a fake receipt."""
        f = self.f
        f.files.clear(); f.rows.clear(); f.pool.clear()
        for i, (name, source) in enumerate(sources.items(), 1):
            path = f.root/name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(source.encode())
            file = dict(id=i, project_id=f.project.project_id, file_path=name,
                        language='ArkTS', source_digest=hashlib.sha256(source.encode()).hexdigest(),
                        index_generation=1)
            f.files.append(file)
            inventory = inventory_source(source)
            self.assertEqual(inventory['status'], 'known')
            for owner in inventory['declarations']:
                kind = 'component' if owner['kind']=='struct' else 'service'
                for declaration in [owner]+owner['methods']:
                    isowner = declaration is owner
                    row = dict(file, id=len(f.rows)+1, symbol=declaration['name'],
                               symbol_key='key:'+str(len(f.rows)+1),
                               qualified_name=owner['name']+('' if isowner else '.'+declaration['name']),
                               owner_name='' if isowner else owner['name'], owner_kind=kind,
                               symbol_type=('component' if kind=='component' else 'class') if isowner else 'function',
                               semantic_adapter='arkts-static@1.2', evidence_class='static',
                               start_line=declaration['span']['start_line'], end_line=declaration['span']['end_line'])
                    f.rows.append(row)
                    if not isowner:
                        f.pool.append(dict(row, kind='symbol'))

    def issued(self):
        data = self.f.bind()
        self.assertIsInstance(data, sel.SqlSlotContext)
        self.assertIsNotNone(sel.sql_slot_receipt(data))
        return data

    def rejected(self):
        self.assertIs(self.f.bind(), self.f.base)

    def consumed_reject(self, data):
        baseline = copy.deepcopy(self.f.base)
        self.assertIs(sel.compact_sql_slot(data, baseline), baseline)

    def outside(self):
        sources = dict(self.sources)
        sources['src/Other.ets'] = 'export class Other {\n  idle() { return [] }\n}\n'
        self.rebuild(sources)
        return self.f.root/'src/Other.ets'

    def test_p01_real_view_ordinary_outside_graph(self):
        self.outside()
        for row in self.f.pool:
            if row['file_path']=='src/Other.ets':
                row.update(graph_neighbor=True,graph_relation='imports',match_reasons=['graph_neighbor','imports'])
        data=self.issued();result=sel.compact_sql_slot(data,self.f.base)
        self.assertIsNot(result,self.f.base)
        self.assertEqual(dict(data),self.f.base)
        self.assertTrue(all(a['file_path']!='src/Other.ets' for a in result['query_handoff']['code_anchors']))

    def test_p02_t10_stronger_clauses_bind_unchanged(self):
        query=self.f.query
        for clause in ('并返回调用图','并返回路径 src/Other.ets','并返回事件 LookupFailed','及错误日志','并返回 ExtraOwner'):
            self.f.query=query+clause;self.f.base['query']=self.f.query
            self.rejected()

    def test_a16_a17_a18_full_scope_binder_wrappers(self):
        sources=dict(self.sources)
        for i in range(11):sources[f'src/Outside{i}.ets']=f'export class Outside{i} {{ idle() {{ return [] }} }}'
        self.rebuild(sources);self.rejected()
        self.rebuild(self.sources)
        path=self.f.root/self.sql;path.write_bytes(path.read_bytes()+b' '*(2*1024*1024))
        self.rejected()
        self.rebuild(self.sources)
        from unittest.mock import patch
        with patch('tools.agent_memory_runtime.query_sql_slot_snapshot.source_bytes',side_effect=OSError('unreadable')):
            self.rejected()
        names={p.replace('.ets','.ts'):text for p,text in self.sources.items()}
        self.rebuild(names);self.rejected()

    def test_a08_contradictory_file_containers(self):
        self.f.files.append(dict(self.f.files[0], id=100, source_digest='0'*64))
        self.rejected()

    def test_a09_pool_project_identity(self):
        self.f.pool[0]['project_id']='other'
        self.rejected()

    def test_a10_escaping_symlink(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as outside:
            target=Path(outside)/'source.ets'; target.write_text(self.sources[self.sql])
            path=self.f.root/self.sql; path.unlink(); path.symlink_to(target)
            self.rejected()

    def test_a11_a12_a13_synchronized_method_metadata(self):
        for key,value in [('source_digest','0'*64),('index_generation',2),
                          ('semantic_adapter','arkts-static@different')]:
            with self.subTest(key=key):
                self.rebuild(self.sources)
                row=next(r for r in self.f.rows if r['symbol']=='findRows')
                pool=next(r for r in self.f.pool if r['id']==row['id'])
                row[key]=value; pool[key]=value
                self.rejected()

    def test_a14_synchronized_method_declaration_corruption(self):
        for key,value in [('owner_name','Wrong'),('symbol','wrong'),('start_line',1),('end_line',6)]:
            with self.subTest(key=key):
                self.rebuild(self.sources)
                row=next(r for r in self.f.rows if r['symbol']=='findRows')
                pool=next(r for r in self.f.pool if r['id']==row['id'])
                row[key]=value; pool[key]=value
                self.rejected()

    def test_a15_missing_or_wrong_import_target(self):
        for before,after in [("'../services/IndexGateway'", "'../services/Missing'"),
                             ('import { IndexGateway }', 'import { Wrong as IndexGateway }')]:
            with self.subTest(after=after):
                sources=dict(self.sources); sources[self.ui]=sources[self.ui].replace(before,after)
                self.rebuild(sources); self.rejected()

    def test_a19_unknown_same_slot_outsider(self):
        outsiders = [
            'export class Other {\n  findRows(term: string) { return [] }\n}\n',
            '@Component\nexport struct Other {\n  @State rows: string[] = []\n  build() { Text("x") }\n}\n',
        ]
        for source in outsiders:
            with self.subTest(source=source):
                sources=dict(self.sources);sources['src/Other.ets']=source
                self.rebuild(sources);self.rejected()

    def test_a20_all_positive_chains_not_first_winner(self):
        # Each renamed family qualifies alone. Together there are six method roots.
        other={p.replace('Index','Second'):s.replace('Index','Second') for p,s in self.sources.items()}
        self.rebuild(other);self.issued()
        self.rebuild(self.sources);self.issued()
        self.rebuild(dict(self.sources, **other));self.rejected()

    def query(self, excluded):
        q=self.f.query[:-1]+'，不要返回 '+excluded+'。'
        self.f.query=q;self.f.base['query']=q

    def test_p12_imported_entity_type_not_output_owner(self):
        sources=dict(self.sources)
        sources[self.ui]="import { EntityRecord } from '../EntityRecord'\n"+sources[self.ui].replace('export struct IndexView {', 'export struct IndexView {\n  private entity: EntityRecord = new EntityRecord()')
        sources['src/EntityRecord.ets']='export class EntityRecord {\n  value: string = ""\n  idle() { return [] }\n}\n'
        self.rebuild(sources);self.query('EntityRecord')
        data=self.issued();result=sel.compact_sql_slot(data,self.f.base)
        self.assertIsNot(result,self.f.base)

    def test_p13_output_owner_exclusion(self):
        for owner in ['IndexView','IndexGateway']:
            with self.subTest(owner=owner):
                original=self.f.query
                self.query(owner);self.rejected()
                self.f.query=original;self.f.base['query']=original

    def test_p14_owner_prefix_suffix_not_excluded(self):
        original=self.f.query
        for excluded in ['Index','View','IndexViewExtra','PreIndexGateway']:
            with self.subTest(excluded=excluded):
                self.f.query=original;self.f.base['query']=original
                self.query(excluded);self.issued()

    def test_r01_r02_selected_source_changes(self):
        for path in [self.sql,self.ui]:
            with self.subTest(path=path):
                self.rebuild(self.sources);data=self.issued()
                p=self.f.root/path;p.write_bytes(p.read_bytes()+b'\n')
                self.consumed_reject(data)

    def test_r03_r04_r14_outside_scope_source_changes(self):
        for extra in ['\n','\nexport class New { findRows(term: string) { return [] } }\n',
                      '\n@Component\nexport struct New { @State rows: string[] = [] }\n']:
            with self.subTest(extra=extra):
                path=self.outside();data=self.issued()
                path.write_bytes(path.read_bytes()+extra.encode());self.consumed_reject(data)

    def test_r05_accepted_observation_swap(self):
        data=self.issued()
        data['query']='档案名称只能精确搜索，'+self.f.query
        self.assertIsNotNone(sel.sql_slot_request(data['query']))
        self.consumed_reject(data)

    def test_r06_all_descriptor_slots(self):
        for key,value in [('method','other'),('state','other'),('excluded_owner','Other'),('sql_kind','SQL')]:
            with self.subTest(key=key):
                data=self.issued();data._descriptor[key]=value;self.consumed_reject(data)

    def test_r07_pool_order_content_identity(self):
        for mutate in [lambda p:p.reverse(), lambda p:p.append(dict(p[0])),
                       lambda p:p[0].update(id=900),lambda p:p[0].update(match_reasons=['new'])]:
            data=self.issued();mutate(data._pool);self.consumed_reject(data)

    def test_r08_project_root_and_id(self):
        for key,value in [('root',self.f.root/'elsewhere'),('project_id','other')]:
            data=self.issued();old=getattr(self.f.project,key)
            try:
                setattr(self.f.project,key,value);self.consumed_reject(data)
            finally:setattr(self.f.project,key,old)

    def test_r12_anchor_span_and_same_line_excerpt(self):
        mutations=[lambda a:a.update(symbol='wrong'),
                   lambda a:a['source_ranges'][0].update(start_line=1),
                   lambda a:a['source_excerpts'][0].update(content='\n'.join('changed' for _ in a['source_excerpts'][0]['content'].split('\n')))]
        for mutate in mutations:
            data=self.issued();mutate(data._qualified['anchors'][0]);self.consumed_reject(data)

    def test_r13_db_only_identity_and_container_changes(self):
        for table,key,value in [('rows','symbol_key','changed'),('rows','index_generation',2),
                                ('rows','owner_name','Wrong'),('files','id',100),
                                ('files','source_digest','0'*64),('files','index_generation',2)]:
            with self.subTest(table=table,key=key):
                data=self.issued();row=getattr(self.f,table)[0];old=row[key]
                try:row[key]=value;self.consumed_reject(data)
                finally:row[key]=old


if __name__=='__main__':unittest.main()
