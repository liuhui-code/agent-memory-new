# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime.query_explicit_owner_certificate import certificate_members, CertifiedPortfolio
from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors
from tools.agent_memory_runtime.query_callable_passage_portfolio import build_callable_passage_portfolio

class ExplicitOwnerCertificateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.project=SimpleNamespace(root=self.root,db_path=self.root/'test.db',project_id='p')
        self.conn=sqlite3.connect(self.project.db_path);self.addCleanup(self.conn.close)
        self.conn.execute('CREATE TABLE code_symbols(id INTEGER PRIMARY KEY,project_id TEXT,file_path TEXT,symbol TEXT,symbol_type TEXT,symbol_key TEXT,qualified_name TEXT,owner_name TEXT,owner_kind TEXT,start_line INTEGER,end_line INTEGER,source_digest TEXT,index_generation INTEGER)')
        self.conn.execute('CREATE INDEX idx_code_symbols_project_symbol ON code_symbols(project_id,symbol)')
        self.conn.execute('CREATE TABLE code_files(project_id TEXT,file_path TEXT,source_digest TEXT,index_generation INTEGER)')
        self.conn.execute('CREATE UNIQUE INDEX idx_code_files_project_file ON code_files(project_id,file_path)')
        self.candidates=[];self.ranges=[];self.receipts=[]
        names=[x[1] for x in self.conn.execute('PRAGMA table_info(code_symbols)')]
        for n,(owner,method) in enumerate([('OrderComposer','dispatchOrder'),('OrderSender','transmitOrder')]):
            path=owner+'.ts';source=f'class {owner} {{\n {method}() {{\n }}\n}}\n';(self.root/path).write_text(source);digest=hashlib.sha256(source.encode()).hexdigest()
            declaration=(n*2+1,'p',path,owner,'class','decl'+str(n),owner,'','service',1,4,digest,1)
            row=(n*2+2,'p',path,method,'function','method'+str(n),owner+'.'+method,owner,'service',2,3,digest,1)
            self.conn.executemany('INSERT INTO code_symbols VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',[declaration,row]);self.conn.execute('INSERT INTO code_files VALUES(?,?,?,?)',('p',path,digest,1))
            receipt=dict(zip(names,row));receipt['kind']='symbol';self.receipts.append(receipt)
            item={k:receipt[k] for k in ('file_path','symbol','owner_name','owner_kind','qualified_name','start_line','end_line')};item.update(symbol_id=row[0],reasons=['exact_symbol']);self.candidates.append(item)
            self.ranges.append(dict(symbol_id=row[0],file_path=path,symbol=method,start_line=2,end_line=3,callable_start_line=2,callable_end_line=3,selection_reason='callable_symbol_range'))
        self.conn.commit();self.primary={**self.candidates[0],'source_range':{k:self.ranges[0][k] for k in ('start_line','end_line','selection_reason')}}
        self.query='Return OrderComposer dispatchOrder and OrderSender transmitOrder.'
    def cert(self,query=None):
        return certificate_members(query or self.query,self.primary,self.candidates,self.ranges,self.candidates,self.project,self.receipts)
    def update(self,sql):
        self.conn.execute(sql);self.conn.commit()
    def test_positive_and_reversed(self):
        self.assertEqual([x['symbol'] for x in self.cert()],['dispatchOrder','transmitOrder'])
        self.assertEqual(len(self.cert('Return OrderSender transmitOrder and OrderComposer dispatchOrder.')),2)
    def test_grammar_zero_connections(self):
        for q in ['Return OrderComposer deadline and insertion sequence','Return OrderComposer dispatchOrder if ready and OrderSender transmitOrder otherwise','Return only OrderComposer dispatchOrder and OrderSender transmitOrder','Return OrderComposer dispatchOrder and not OrderSender transmitOrder','"'+self.query+'"',self.query+' unless ready',self.query+' versus X','Return OrderComposer dispatchOrder or OrderSender transmitOrder','Return OrderComposer dispatchOrder and OrderComposer transmitOrder']:
            with self.subTest(q=q),patch('sqlite3.connect',side_effect=AssertionError('unexpected SQL')):self.assertIsNone(self.cert(q))
    def test_competing_kinds_paths(self):
        for kind in ['class','interface','component','struct','object','unknown']:
            for path in ['OrderSender.ts','Other.ts']:
                self.conn.execute("INSERT INTO code_symbols(id,project_id,file_path,symbol,symbol_type) VALUES(99,'p',?,'OrderSender',?)",(path,kind));self.conn.commit();self.assertIsNone(self.cert());self.update('DELETE FROM code_symbols WHERE id=99')
    def test_missing_index(self):
        self.update('DROP INDEX idx_code_symbols_project_symbol');self.assertIsNone(self.cert())
    def test_missing_columns(self):
        self.update('ALTER TABLE code_symbols RENAME COLUMN source_digest TO old_digest');self.assertIsNone(self.cert())
    def test_stale_receipt(self):
        self.update("UPDATE code_symbols SET source_digest='"+'f'*64+"' WHERE id=4");self.assertIsNone(self.cert())
    def test_missing_conflicting_receipt(self):
        row=self.receipts.pop();self.assertIsNone(self.cert());self.receipts.extend([row,{**row,'index_generation':2}]);self.assertIsNone(self.cert())
    def test_file_namespace_other_project(self):
        self.receipts[1]['kind']='file';self.assertIsNone(self.cert());self.receipts[1]['kind']='symbol';self.receipts[1]['project_id']='other';self.assertIsNone(self.cert())
    def test_crossing_bounds(self):
        self.update('UPDATE code_symbols SET end_line=2 WHERE id=3');self.assertIsNone(self.cert())
    def test_file_generation(self):
        self.update("UPDATE code_files SET index_generation=2 WHERE file_path='OrderSender.ts'");self.assertIsNone(self.cert())
    def test_deleted_reinserted(self):
        self.update('UPDATE code_symbols SET id=44 WHERE id=4');self.assertIsNone(self.cert())
    def test_live_source(self):
        (self.root/'OrderSender.ts').write_text('//changed');self.assertIsNone(self.cert())
    def test_primary_binding(self):
        self.primary['source_range']['start_line']=1;self.assertIsNone(self.cert())
    def test_integration_guards_and_mutated_certificate(self):
        other={**self.candidates[1],'owner_name':'TelemetrySender','file_path':'Other.ts','symbol_id':30}
        loc={'callable_candidates':[*self.candidates,other],'source_ranges':self.ranges};ev={'primary':self.primary,'certainty':'bounded'}
        p=build_callable_passage_portfolio(self.query,loc,ev,project=self.project,symbol_receipts=self.receipts);self.assertIsInstance(p,CertifiedPortfolio);ev['passage_portfolio']=p
        anchors=[{'file_path':'OrderComposer.ts'}];self.assertEqual(len(focus_callable_anchors(anchors,ev,False)),2)
        for key in ('graph_neighbor','graph_relation','identity_match','log_identity_match'):
            a=[{'file_path':'Other.ts',key:True}];self.assertEqual(focus_callable_anchors(a,ev,False),a)
        self.assertEqual(focus_callable_anchors(anchors,ev,True),anchors)
        self.assertEqual(len(focus_callable_anchors([{'file_path':'path.ts'}],ev,{'activated':True})),3)
        p['members'][0]['source_range']['start_line']=1;self.assertEqual(focus_callable_anchors(anchors,ev,False),anchors)
    def test_default_no_connection(self):
        with patch('sqlite3.connect',side_effect=AssertionError('unexpected SQL')):
            p=build_callable_passage_portfolio(self.query,{'callable_candidates':self.candidates,'source_ranges':self.ranges},{'primary':self.primary})
        self.assertEqual(p['state'],'inactive')

    def test_one_readonly_connection_and_explicit_begin(self):
        real=sqlite3.connect;statements=[]
        def connect(*args,**kwargs):
            self.assertIn('?mode=ro',args[0]);self.assertTrue(kwargs['uri'])
            c=real(*args,**kwargs);c.set_trace_callback(statements.append);return c
        with patch('sqlite3.connect',side_effect=connect) as opened:
            self.assertIsNotNone(self.cert());self.assertEqual(opened.call_count,1)
        self.assertEqual(statements[0],'BEGIN')
        self.assertFalse(any(s.startswith(('UPDATE','INSERT','PRAGMA')) for s in statements))

    def test_complete_snapshot_with_concurrent_wal_duplicate(self):
        self.conn.execute('PRAGMA journal_mode=WAL');self.conn.commit()
        real=sqlite3.connect;changed=[]
        def connect(*args,**kwargs):
            c=real(*args,**kwargs)
            def observe(sql):
                if sql.startswith('SELECT * FROM code_symbols') and not changed:
                    self.conn.execute("INSERT INTO code_symbols(id,project_id,file_path,symbol,symbol_type) VALUES(99,'p','Else.ts','OrderSender','class')")
                    self.conn.commit();changed.append(True)
            c.set_trace_callback(observe);return c
        with patch('sqlite3.connect',side_effect=connect):self.assertIsNotNone(self.cert())
        self.assertTrue(changed);self.assertIsNone(self.cert())

    def test_lock_fails_closed(self):
        self.conn.execute('BEGIN EXCLUSIVE')
        try:self.assertIsNone(self.cert())
        finally:self.conn.rollback()

    def test_same_key_distinct_declaration_and_pk_binding(self):
        self.update("INSERT INTO code_symbols SELECT 99,project_id,'Other.ts',symbol,symbol_type,symbol_key,qualified_name,owner_name,owner_kind,start_line,end_line,source_digest,index_generation FROM code_symbols WHERE id=3")
        self.assertIsNone(self.cert())

    def portfolio(self):
        return build_callable_passage_portfolio(self.query,
            {'callable_candidates':self.candidates,'source_ranges':self.ranges},
            {'primary':self.primary},project=self.project,symbol_receipts=self.receipts)

    def test_copy_provenance_failclosed_cross_product(self):
        import copy
        import json
        original=self.portfolio()
        for transform in (dict, lambda p:json.loads(json.dumps(p))):
            for tamper in (False,True):
                for path in (False,{'activated':True},True):
                    for flag in (None,'graph_neighbor','graph_relation','identity_match','log_identity_match'):
                        for bounded in (False,True):
                            for typed in (False,True):
                                with self.subTest(transform=transform,tamper=tamper,path=path,flag=flag,bounded=bounded,typed=typed):
                                    p=transform(copy.deepcopy(original))
                                    if tamper:p['members'][0]['source_range']['start_line']=1
                                    anchors=[{'file_path':'Other.ts',**({flag:True} if flag else {})}]
                                    primary={**self.primary,**({'typed_contract_match':True} if typed else {})}
                                    evidence={'primary':primary,'certainty':'bounded' if bounded else 'unknown','passage_portfolio':p}
                                    self.assertIs(focus_callable_anchors(anchors,evidence,path),anchors)

    def test_deepcopy_authority_and_mutation(self):
        import copy
        p=copy.deepcopy(self.portfolio());anchors=[{'file_path':'Other.ts'}]
        ev={'primary':self.primary,'certainty':'bounded','passage_portfolio':p}
        self.assertTrue(p.valid_for(self.primary))
        self.assertEqual(len(focus_callable_anchors(anchors,ev,False)),2)
        p['members'][1]['source_range']['end_line']=4
        self.assertIs(focus_callable_anchors(anchors,ev,{'activated':True}),anchors)

    def test_marker_and_state_controls(self):
        import copy
        original=self.portfolio();anchors=[{'file_path':'Other.ts'}];variants=[]
        plain=dict(copy.deepcopy(original));plain['selection_basis']=['indexed_explicit_owner_methods'];variants.append(plain)
        private=copy.deepcopy(original);private['selection_basis']=['explicit_cross_file_targets'];variants.append(private)
        private=copy.deepcopy(original);private['state']='inactive';variants.append(private)
        for p in variants:
            for path in (False,{'activated':True}):
                self.assertIs(focus_callable_anchors(anchors,{'primary':self.primary,'certainty':'bounded','passage_portfolio':p},path),anchors)

    def test_unmarked_legacy_portfolio_still_projects(self):
        import copy
        p=dict(copy.deepcopy(self.portfolio()));p['selection_basis']=['existing_localization','explicit_cross_file_targets']
        anchors=[{'file_path':'Other.ts','graph_neighbor':True}]
        ev={'primary':self.primary,'certainty':'bounded','passage_portfolio':p}
        projected=focus_callable_anchors(anchors,ev,{'activated':True})
        self.assertEqual([x['file_path'] for x in projected],['OrderComposer.ts','OrderSender.ts','Other.ts'])
        self.assertEqual(projected[-1],anchors[0])
