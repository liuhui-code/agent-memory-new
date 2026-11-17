"""Self-contained normal learn/query evidence; no saved outputs."""
from copy import deepcopy
import json,sys,tempfile,unittest
from pathlib import Path
from tools.agent_memory_runtime.storage import resolve_project,connect
from tools.agent_memory_runtime.query_results import _context_pass
from tools.agent_memory_runtime.query_touch_log_provenance import touch_log_provenance
from tests.archive_create_write_test_support import cli
SOURCES={'one-direct': {'CanvasTouchPane.ets': "@Component\nexport struct CanvasTouchPane {\n horizontal: number = 0\n build() {\n  Stack() { Text('surface') }.onTouch((sample: TouchEvent) => {\n   const contact = sample.touches[0]\n   this.horizontal = contact.x\n  })\n }\n}\n", 'notice/PointerNoticeWriter.ets': "export class PointerNoticeWriter {\n report(): void {\n  Logger.error('touch contact state unavailable')\n }\n}\n"}, 'one-depth1': {'CanvasTouchPane.ets': "@Component\nexport struct CanvasTouchPane {\n horizontal: number = 0\n build() {\n  Stack() { Text('surface') }.onTouch((sample: TouchEvent) => {\n   const contact = sample.touches[0]\n   this.horizontal = contact.x\n  })\n }\n}\n", 'notice/PointerNoticeSink.ets': 'export class PointerNoticeSink {\n emit(message: string): void {\n  Logger.error(message)\n }\n}\n', 'notice/PointerNoticeWorker.ets': "import { PointerNoticeSink } from './PointerNoticeSink'\nexport class PointerNoticeWorker {\n private sink: PointerNoticeSink = new PointerNoticeSink()\n run(): void {\n  this.sink.emit('touch contact state unavailable')\n }\n}\n"}, 'one-depth2': {'CanvasTouchPane.ets': "@Component\nexport struct CanvasTouchPane {\n horizontal: number = 0\n build() {\n  Stack() { Text('surface') }.onTouch((sample: TouchEvent) => {\n   const contact = sample.touches[0]\n   this.horizontal = contact.x\n  })\n }\n}\n", 'notice/PointerNoticeSink.ets': 'export class PointerNoticeSink {\n emit(message: string): void {\n  Logger.error(message)\n }\n}\n', 'notice/PointerNoticeRelay.ets': "import { PointerNoticeSink } from './PointerNoticeSink'\nexport class PointerNoticeRelay {\n private sink: PointerNoticeSink = new PointerNoticeSink()\n report(message: string): void {\n  this.sink.emit(message)\n }\n}\n", 'notice/PointerNoticeWorker.ets': "import { PointerNoticeRelay } from './PointerNoticeRelay'\nexport class PointerNoticeWorker {\n private relay: PointerNoticeRelay = new PointerNoticeRelay()\n run(): void {\n  this.relay.report('touch contact state unavailable')\n }\n}\n"}, 'two-depth2': {'CanvasTouchPane.ets': "@Component\nexport struct CanvasTouchPane {\n horizontal: number = 0\n build() {\n  Stack() { Text('surface') }.onTouch((sample: TouchEvent) => {\n   const contact = sample.touches[0]\n   this.horizontal = contact.x\n  })\n }\n}\n", 'TimelineTouchPanel.ets': "@Component\nexport struct TimelineTouchPanel {\n position: number = 0\n build() {\n  Stack() { Text('surface') }.onTouch((motion: TouchEvent) => {\n   const primaryContact = motion.touches[2]\n   this.position = primaryContact.x\n  })\n }\n}\n", 'notice/PointerNoticeSink.ets': 'export class PointerNoticeSink {\n emit(message: string): void {\n  Logger.error(message)\n }\n}\n', 'notice/PointerNoticeRelay.ets': "import { PointerNoticeSink } from './PointerNoticeSink'\nexport class PointerNoticeRelay {\n private sink: PointerNoticeSink = new PointerNoticeSink()\n report(message: string): void {\n  this.sink.emit(message)\n }\n}\n", 'notice/PointerNoticeWorker.ets': "import { PointerNoticeRelay } from './PointerNoticeRelay'\nexport class PointerNoticeWorker {\n private relay: PointerNoticeRelay = new PointerNoticeRelay()\n run(): void {\n  this.relay.report('touch contact state unavailable')\n }\n}\n"}}
QUERY='触摸输入没有首个触点时界面操作异常，请只返回触摸回调和索引读取所在源码。'

class TouchLogProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup);cls.samples={}
        for name,sources in SOURCES.items():
            root=Path(cls.temp.name)/name;root.mkdir();source=root/'source';source.mkdir()
            for path,text in sources.items():
                f=source/path;f.parent.mkdir(exist_ok=True,parents=True);f.write_text(text)
            project=resolve_project(str(source),str(root/'memory'));cli(project,'init');cli(project,'learn-path','--path','.','--json')
            captured=[]
            def observer(frame,event,result):
                if frame.f_code.co_name=='collect_matches_with_audit'and event=='return':
                    recalled=frame.f_locals['recalled'];captured.append(dict(direct=[dict(r)for r in recalled.rows.get('code_log_statements',[])],effects=deepcopy(frame.f_locals.get('log_effects',[]))))
            sys.setprofile(observer)
            try:raw=_context_pass(project,QUERY)
            finally:sys.setprofile(None)
            cls.samples[name]=(project,captured[0],raw['query_handoff']['log_anchors'])
    def sample(self,name='one-depth2'):
        p,i,l=self.samples[name];return p,deepcopy(i),deepcopy(l)
    def test_real_direct_depth1_depth2_two_source(self):
        for name in SOURCES:
            p,i,l=self.sample(name);self.assertIsNotNone(touch_log_provenance(p,i,l),name)
            self.assertEqual(touch_log_provenance(p,i,l),touch_log_provenance(p,i,l))
    def test_discarded_direct_candidate_and_trial_only_effect(self):
        p,i,l=self.sample();self.assertIsNotNone(touch_log_provenance(p,i,[]))
        effects=[r for r in l if r['effect_id']is not None]
        self.assertIsNotNone(touch_log_provenance(p,dict(direct=[],effects=i['effects']),effects))
        i['direct'][0]['source_digest']='0'*64;self.assertIsNone(touch_log_provenance(p,i,[]))
    def test_namespace_collision_and_missing_candidate(self):
        p,i,l=self.sample();self.assertEqual(i['direct'][0]['id'],i['effects'][0]['id'])
        self.assertIsNotNone(touch_log_provenance(p,i,l))
        i['effects']=i['effects'][1:];self.assertIsNone(touch_log_provenance(p,i,l))
    def test_malformed_inventory_and_projections(self):
        p,i,l=self.sample()
        for bad in (None,{},dict(i,unknown=[]),dict(direct=None,effects=[]),dict(direct=i['direct']*2,effects=i['effects'])):
            self.assertIsNone(touch_log_provenance(p,bad,l))
        for key,value in [('wrapper_depth',3),('evidence_class','inferred_wrapped'),('truncated',1),('call_path',[]),('project_id','other'),('id',True)]:
            x=deepcopy(i);x['effects'][0][key]=value;self.assertIsNone(touch_log_provenance(p,x,l),key)
        x=deepcopy(l);x[0]['line']+=1;self.assertIsNone(touch_log_provenance(p,i,x))
    def mutate(self,table,ident,key,value):
        p,i,l=self.sample()
        with connect(p)as db:
            old=db.execute('SELECT '+key+' FROM '+table+' WHERE id=?',(ident,)).fetchone()[0]
            db.execute('UPDATE '+table+' SET '+key+'=? WHERE id=?',(value,ident))
        try:return touch_log_provenance(p,i,l)
        finally:
            with connect(p)as db:db.execute('UPDATE '+table+' SET '+key+'=? WHERE id=?',(old,ident))
    def test_edge_wrong_retired_crossproject_endpoint_schema_line(self):
        p,i,l=self.sample()
        with connect(p)as db:edges=[dict(r)for r in db.execute("SELECT * FROM memory_edges WHERE source_type='code_symbol' AND relation='calls' AND valid_to IS NULL")]
        for e in edges:
            for key,value in [('valid_to','retired'),('project_id','other'),('target_id',99999),('source_revision','wrong')]:
                self.assertIsNone(self.mutate('memory_edges',e['id'],key,value),(e['id'],key))
            evidence=json.loads(e['evidence'])
            for key,value in [('schema_version','unknown'),('line',4),('line',9999),('source_digest','0'*64)]:
                self.assertIsNone(self.mutate('memory_edges',e['id'],'evidence',json.dumps(dict(evidence,**{key:value}))))
    def test_duplicate_edge_and_bad_emits(self):
        p,i,l=self.sample()
        with connect(p)as db:
            e=dict(db.execute("SELECT * FROM memory_edges WHERE source_type='code_symbol' AND relation='calls' AND valid_to IS NULL LIMIT 1").fetchone());e.pop('id');keys=list(e)
            new=db.execute('INSERT INTO memory_edges ('+','.join(keys)+') VALUES ('+','.join('?'for _ in keys)+')',[e[k]for k in keys]).lastrowid
        try:self.assertIsNone(touch_log_provenance(p,i,l))
        finally:
            with connect(p)as db:db.execute('DELETE FROM memory_edges WHERE id=?',(new,))
        with connect(p)as db:e=dict(db.execute("SELECT * FROM memory_edges WHERE relation='emits_log' LIMIT 1").fetchone())
        self.assertIsNone(self.mutate('memory_edges',e['id'],'evidence','wrong:99'))
    def test_stale_middle_sink_and_changed_graph_receipt(self):
        p,i,l=self.sample();original=touch_log_provenance(p,i,l)
        for path in ('notice/PointerNoticeRelay.ets','notice/PointerNoticeSink.ets'):
            f=p.root/path;old=f.read_bytes();f.write_bytes(old+b'// drift\n')
            try:self.assertIsNone(touch_log_provenance(p,i,l))
            finally:f.write_bytes(old)
        with connect(p)as db:db.execute('UPDATE graph_runtime_state SET graph_revision=graph_revision+1')
        try:self.assertNotEqual(touch_log_provenance(p,i,l),original)
        finally:
            with connect(p)as db:db.execute('UPDATE graph_runtime_state SET graph_revision=graph_revision-1')
    def test_index_drift_changes_receipt_and_unknown_schema_rejects(self):
        p,i,l=self.sample();before=touch_log_provenance(p,i,l)
        with connect(p)as db:db.execute('UPDATE code_index_state SET generation=generation+1')
        try:self.assertNotEqual(touch_log_provenance(p,i,l),before)
        finally:
            with connect(p)as db:db.execute('UPDATE code_index_state SET generation=generation-1')
        with connect(p)as db:
            old=db.execute('SELECT extractor_version FROM code_index_state').fetchone()[0]
            db.execute("UPDATE code_index_state SET extractor_version='unknown'")
        try:self.assertIsNone(touch_log_provenance(p,i,l))
        finally:
            with connect(p)as db:db.execute('UPDATE code_index_state SET extractor_version=?',(old,))
    def test_duplicate_shadow_method_rejects_current_bytes(self):
        p,i,l=self.sample()
        with connect(p)as db:
            row=dict(db.execute("SELECT * FROM code_symbols WHERE symbol='report' AND file_path='notice/PointerNoticeRelay.ets'").fetchone());row.pop('id');keys=list(row)
            new=db.execute('INSERT INTO code_symbols ('+','.join(keys)+') VALUES ('+','.join('?'for _ in keys)+')',[row[k]for k in keys]).lastrowid
        try:self.assertIsNone(touch_log_provenance(p,i,l))
        finally:
            with connect(p)as db:db.execute('DELETE FROM code_symbols WHERE id=?',(new,))
    def test_visible_effect_paths_and_sink_are_bound(self):
        p,i,l=self.sample()
        for key,value in [('call_path',[]),('call_path_locations',[]),('log_id',999),('log_id',True),('wrapper_depth',True),('truncated',True)]:
            x=deepcopy(l);next(r for r in x if r['effect_id']is not None)[key]=value
            self.assertIsNone(touch_log_provenance(p,i,x),key)
