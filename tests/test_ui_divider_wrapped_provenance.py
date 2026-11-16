"""Self-contained provenance units; synthetic rows do not replace public learn tests."""
import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime import query_ui_divider_wrapped_provenance as api


class WrappedNegativeProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.project = SimpleNamespace(root=Path(self.temp.name), project_id='unit-project')
        sources={'Caller.ets':"export class Caller {\n run() {\n  this.sink.report('notice')\n }\n}\n",'Sink.ets':"export class Sink {\n report(message: string) {\n  Logger.error(message)\n }\n}\n"}
        self.files=[]; self.symbols=[]
        for i,(file,source) in enumerate(sources.items(),1):
            (self.project.root/file).write_text(source)
            digest=hashlib.sha256(source.encode()).hexdigest()
            self.files.append(dict(id=i,project_id='unit-project',file_path=file,source_digest=digest,index_generation=i))
            name='run' if i==1 else 'report'
            self.symbols.append(dict(id=i,project_id='unit-project',file_path=file,source_digest=digest,index_generation=i,symbol=name,symbol_key=api.symbol_key('ArkTS',file,file[:-4]+'.'+name,name+'():void'),signature=name+'():void',qualified_name=file[:-4]+'.'+name,symbol_type='function',start_line=2,end_line=4,evidence_class='static',semantic_adapter='arkts-static@1.2'))
        common=dict(project_id='unit-project',file_path='Sink.ets',source_digest=self.files[1]['source_digest'],index_generation=2)
        self.sink=dict(common,id=1,line=3,function='report',logger='logger',level='error',message_template='{message}',raw_statement='Logger.error(message)')
        self.effect=dict(project_id='unit-project',id=1,file_path='Caller.ets',source_digest=self.files[0]['source_digest'],index_generation=1,line=3,function='run',wrapper_symbol='report',sink_log_id=1,logger='logger',level='error',message_template='notice',evidence_class='static_wrapped',wrapper_depth=1,truncated=0,call_path=json.dumps(['run','report','logger.error']),call_path_locations=json.dumps(['Caller.ets#run','Sink.ets#report','Sink.ets#logger.error']))
        self.calls=dict(id=1,project_id='unit-project',source_type='code_symbol',source_id=1,relation='calls',target_type='code_symbol',target_id=2,valid_to=None,valid_from='indexed',evidence_kind='static_semantic_calls',evidence=json.dumps(dict(schema_version='semantic-evidence/v1',line=3,source_digest=self.files[0]['source_digest'],evidence_class='static')))
        self.emit=dict(id=2,project_id='unit-project',source_type='code_symbol',source_id=2,relation='emits_log',target_type='code_log_statement',target_id=1,valid_to=None,valid_from='indexed',evidence_kind='code_observability',evidence='Sink.ets:3')
        self.log={k:self.effect[k] for k in ('file_path','line','function','wrapper_symbol','logger','message_template','evidence_class','wrapper_depth')}
        self.log.update(effect_id=1,log_id=1,truncated=False,call_path=json.loads(self.effect['call_path']),call_path_locations=json.loads(self.effect['call_path_locations']))
        self.logs=[self.log]
        self.frames=dict(contract='multilingual-negative-static-divider/v1',descriptor=dict(excluded_names=['Excluded']),negative_identities=[dict(name='Excluded',declaration=dict(file_path='Excluded.ets',start_line=1,end_line=4))])
        self.calls.update(source_revision='unversioned',extractor_version='semantic-index:v1/arkts-static@1.2');self.emit.update(source_revision='unversioned',extractor_version='code-wiki:v4')
        self.index=dict(project_id='unit-project',generation=2,status='active',source_revision='unversioned',extractor_version='code-derived:v1');self.graph=dict(project_id='unit-project',graph_revision=1)

    def run_api(self):
        tables=dict(code_files=self.files,code_symbols=self.symbols,code_log_statements=[self.sink],code_log_effects=[self.effect],memory_edges=[self.calls,self.emit],code_index_state=[self.index],graph_runtime_state=[self.graph])
        conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
        self.addCleanup(conn.close)
        for name,rows in tables.items():
            keys=list(rows[0]);conn.execute('CREATE TABLE '+name+' ('+','.join('"'+k+'"' for k in keys)+')')
            for row in rows:conn.execute('INSERT INTO '+name+' VALUES ('+','.join('?'for _ in keys)+')',[row.get(k)for k in keys])
        conn.commit()
        @contextmanager
        def connect(_):yield conn
        with patch.object(api,'connect',connect):
            return api.wrapped_negative_provenance(self.project,{'query_handoff':{'log_anchors':self.logs}},json.dumps(self.frames))

    def test_current_static_and_per_file_mixed_generations(self):
        receipt=self.run_api();self.assertIsInstance(receipt,str);self.assertEqual(json.loads(receipt)['logs'],self.logs)
    def test_inferred_preserved(self):
        self.effect['evidence_class']=self.log['evidence_class']='inferred_wrapped';self.calls['evidence_kind']='inferred_semantic_calls'
        e=json.loads(self.calls['evidence']);e['evidence_class']='inferred';self.calls['evidence']=json.dumps(e)
        self.assertIsNotNone(self.run_api())
    def test_cross_project_rows(self):
        for row in (self.effect,self.sink,self.symbols[0],self.files[1],self.calls,self.emit,self.index,self.graph):
            old=row['project_id'];row['project_id']='other'
            with self.subTest(row=row):self.assertIsNone(self.run_api())
            row['project_id']=old
    def test_stale_source_and_generation(self):
        for row in (self.effect,self.sink,self.symbols[0],self.symbols[1]):
            old=row['index_generation'];row['index_generation']=99;self.assertIsNone(self.run_api());row['index_generation']=old
        (self.project.root/'Sink.ets').write_text('changed');self.assertIsNone(self.run_api())
    def test_symbol_key_alias_and_name_ambiguity(self):
        other=copy.deepcopy(self.symbols[1]);other['id']=3;other['symbol']='unrelated';self.symbols.append(other)
        self.assertIsNone(self.run_api());other['symbol_key']='different';other['symbol']='report';self.assertIsNone(self.run_api())
    def test_missing_key_or_invalid_range(self):
        for key,value in [('symbol_key',None),('symbol_key','symbol:'+'0'*24),('start_line',5),('end_line',100),('evidence_class','unknown')]:
            row=self.symbols[0];old=row[key];row[key]=value;self.assertIsNone(self.run_api());row[key]=old
    def test_retired_or_wrong_typed_edge(self):
        for row in (self.calls,self.emit):
            for key,value in [('valid_to','retired'),('target_type','unknown'),('source_id',99),('target_id',99),('evidence_kind','legacy')]:
                old=row[key];row[key]=value;self.assertIsNone(self.run_api());row[key]=old
    def test_projection_and_bool_rejection(self):
        for key,value in [('effect_id',True),('log_id',True),('line',True),('wrapper_depth',True),('truncated',0),('message_template','changed'),('file_path','../Caller.ets')]:
            old=self.log[key];self.log[key]=value;self.assertIsNone(self.run_api());self.log[key]=old
    def test_optional_level_projection(self):
        self.log['level']='error';self.assertIsNotNone(self.run_api())
        self.log['level']='info';self.assertIsNone(self.run_api())

    def test_revision_and_extractor_mismatch(self):
        for row in (self.calls,self.emit):
            for key in ('source_revision','extractor_version'):
                old=row[key];row[key]='unknown';self.assertIsNone(self.run_api());row[key]=old

    def test_paths_unknown_and_depth(self):
        for key,value in [('call_path',[]),('call_path_locations',['Caller.ets#run','Sink.ets#report','Other.ets#logger.error']),('wrapper_depth',2)]:
            old=self.log[key];self.log[key]=value;self.assertIsNone(self.run_api());self.log[key]=old
    def test_negative_whole_file_conflict(self):
        for file in ('Caller.ets','Sink.ets'):
            self.frames['negative_identities'][0]['declaration']['file_path']=file
            self.frames['negative_identities'][0]['declaration']['start_line']=90
            self.assertIsNone(self.run_api())
    def test_all_raw_logs_and_direct_rules(self):
        direct=dict(evidence_class='direct',effect_id=None,file_path='Elsewhere.ets',line=1)
        self.logs.append(direct);self.assertIsNotNone(self.run_api())
        direct['file_path']='Excluded.ets';self.assertIsNone(self.run_api())
        direct['file_path']='Elsewhere.ets';direct['effect_id']=5;self.assertIsNone(self.run_api())
    def test_no_authority_for_invalid_frames(self):
        self.frames['descriptor']['excluded_names']=[];self.assertIsNone(self.run_api())
        self.frames['descriptor']['excluded_names']=['Excluded'];self.frames['contract']='other';self.assertIsNone(self.run_api())
    def test_snapshot_changes_for_row_and_graph_mutation(self):
        old=self.run_api();self.graph['graph_revision']=2;self.assertNotEqual(old,self.run_api())
        old=self.run_api();self.sink['message_template']='other';self.assertNotEqual(old,self.run_api())
    def test_calls_evidence_unknown_or_wrong_line(self):
        old=self.calls['evidence']
        for key,value in [('line',True),('line',4),('source_digest','0'*64),('evidence_class','inferred'),('schema_version','other')]:
            e=json.loads(old);e[key]=value;self.calls['evidence']=json.dumps(e);self.assertIsNone(self.run_api())


class WrappedDividerReceiptTests(unittest.TestCase):
    """Normal learn + public facade control; fixtures contain sources only."""
    @classmethod
    def setUpClass(cls):
        from tests.archive_create_write_test_support import cli, snapshot_database
        from tools.agent_memory_runtime.storage import resolve_project
        from tools.agent_memory_runtime.context_composition import build_context_facade
        from tools.agent_memory_runtime.context_compact import compact_context
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.samples={}
        ui=json.loads((Path(__file__).parent/'fixtures/ui_divider_multilingual.json').read_text())['sources']['supp-noop']
        for kind in ('static','inferred'):
            root=Path(cls.tmp.name)/kind;source=root/'source';source.mkdir(parents=True)
            sources=dict(ui)
            if kind=='static':
                sources['audit/GlyphNoticeSink.ets']="export class GlyphNoticeSink {\n report(message: string): void {\n  Logger.error(message)\n }\n}\n"
                sources['audit/GlyphNoticeService.ets']="import { GlyphNoticeSink } from './GlyphNoticeSink'\nexport class GlyphNoticeService {\n private sink: GlyphNoticeSink = new GlyphNoticeSink()\n render(): void {\n  this.sink.report('glyph divider render failed')\n }\n}\n"
            else:
                sources['audit/GlyphNoticePort.ets']="export interface GlyphNoticePort {\n report(message: string): void\n}\n"
                sources['audit/GlyphNoticeService.ets']="import { GlyphNoticePort } from './GlyphNoticePort'\nexport class GlyphNoticeService {\n private sink: GlyphNoticePort\n render(): void {\n  this.sink.report('glyph divider render failed')\n }\n}\n"
                for name in ('GlyphConsoleNotice','GlyphFileNotice'):
                    sources['audit/'+name+'.ets']=f"import {{ GlyphNoticePort }} from './GlyphNoticePort'\nexport class {name} implements GlyphNoticePort {{\n report(message: string): void {{\n  Logger.error(message)\n }}\n}}\n"
            for name,body in sources.items():
                path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
            project=resolve_project(str(source),str(root/'memory'));cli(project,'init');cli(project,'learn-path','--path','.','--json')
            saved=snapshot_database(project);cls.addClassCleanup(saved.close)
            query='字形列表分隔线粗细错误，请定位 divider 的源码，不要返回 GlyphModel。';capture=[]
            def observe(_p,_q,baseline,pool):capture.append(copy.deepcopy(pool));return baseline
            with patch('tools.agent_memory_runtime.query_ui_divider_selection.bind_divider_context',side_effect=observe):
                raw=build_context_facade(project).execute(query);compact=compact_context(raw)
            cls.samples[kind]=(project,saved,query,copy.deepcopy(dict(raw)),compact,capture[0])

    def setUp(self):
        from tests.archive_create_write_test_support import restore_database
        for project,saved,*_ in self.samples.values():restore_database(project,saved)

    def bind(self,kind='static'):
        from tools.agent_memory_runtime.query_ui_divider_selection import bind_divider_context, DividerContext, divider_receipt
        project,_,query,raw,compact,pool=self.samples[kind];raw=copy.deepcopy(raw)
        data=bind_divider_context(project,query,raw,copy.deepcopy(pool))
        self.assertIsInstance(data,DividerContext);self.assertIsNotNone(divider_receipt(data))
        return project,data,raw,compact

    def test_normal_static_and_inferred_receipt_compact_enrich(self):
        from tools.agent_memory_runtime.query_ui_divider_selection import compact_divider, enrich_divider, divider_receipt
        from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
        from tools.agent_memory_runtime.context_budget import estimate_payload_tokens
        for kind in self.samples:
            with self.subTest(kind=kind):
                _,data,raw,baseline=self.bind(kind)
                self.assertTrue(any(l['evidence_class']==kind+'_wrapped' for l in raw['query_handoff']['log_anchors']))
                compact=compact_divider(data,baseline)
                self.assertEqual(restore_whitelist(compact,baseline),baseline)
                self.assertLessEqual(estimate_payload_tokens(compact),1500)
                self.assertEqual(compact['query_handoff']['log_anchors'],baseline['query_handoff']['log_anchors'])
                self.assertEqual(len(compact['query_handoff']['code_anchors']),2)
                enriched=enrich_divider(data,data['query'],raw['query_handoff']['path_context'],raw['source_freshness'])
                self.assertIsNotNone(divider_receipt(enriched))

    def test_graph_and_effect_mutation_revoke_receipt(self):
        from tools.agent_memory_runtime.storage import connect
        from tools.agent_memory_runtime.query_ui_divider_selection import divider_receipt
        from tests.archive_create_write_test_support import restore_database
        for statement in ('UPDATE graph_runtime_state SET graph_revision=graph_revision+1', "UPDATE code_log_effects SET message_template='changed'"):
            project,data,_,_=self.bind()
            with connect(project)as db:db.execute(statement)
            self.assertIsNone(divider_receipt(data));restore_database(project,self.samples['static'][1])

    def test_raw_log_add_remove_and_copy_revoke_receipt(self):
        from tools.agent_memory_runtime.query_ui_divider_selection import divider_receipt
        for operation in ('add','remove','copy','json'):
            _,data,_,_=self.bind()
            if operation=='add':data['query_handoff']['log_anchors'].append(copy.deepcopy(data['query_handoff']['log_anchors'][0]))
            elif operation=='remove':data['query_handoff']['log_anchors'].pop()
            elif operation=='copy':data=copy.copy(data)
            else:data=json.loads(json.dumps(data))
            self.assertIsNone(divider_receipt(data))
