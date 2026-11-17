"""Normal learned global-script alternatives, never saved output replay."""
from copy import deepcopy
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools.agent_memory_runtime.storage import resolve_project,connect
from tools.agent_memory_runtime.query_results import _context_pass
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
import tools.agent_memory_runtime.query_touch_log_provenance as provenance
from tests.archive_create_write_test_support import cli
F=json.loads((Path(__file__).parent/'fixtures/touch_inferred_log.json').read_text());Q=F['query']

class TouchInferredLogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.samples={}
        for name,sources in F['sources'].items():
            root=Path(cls.tmp.name)/name;root.mkdir();source=root/'source';source.mkdir()
            for path,text in sources.items():
                f=source/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text)
            p=resolve_project(str(source),str(root/'memory'));cli(p,'init');cli(p,'learn-path','--path','.','--json');captured=[]
            def observer(frame,event,result):
                if frame.f_code.co_name=='collect_matches_with_audit'and event=='return':
                    r=frame.f_locals['recalled'];captured.append(dict(direct=[dict(x)for x in r.rows.get('code_log_statements',[])],effects=deepcopy(frame.f_locals['log_effects'])))
            sys.setprofile(observer)
            try:raw=_context_pass(p,Q)
            finally:sys.setprofile(None)
            cls.samples[name]=(p,captured[0],raw['query_handoff']['log_anchors'])
    def sample(self,name='global-script-depth1-two'):
        p,i,l=self.samples[name];return p,deepcopy(i),deepcopy(l)
    def test_two_true_alternatives_retained_without_upgrade(self):
        p,i,l=self.sample();self.assertEqual(len(i['effects']),2)
        receipt=provenance.touch_log_provenance(p,i,l);self.assertIsNotNone(receipt)
        self.assertTrue(all(e['evidence_class']=='inferred_wrapped'for e in i['effects']))
        d=json.loads(receipt);self.assertEqual([x['witness']['calls'][0]['confidence']for x in d['items']if x['kind']=='effects'],[.55,.55])
        self.assertEqual(d['inventory'],i);self.assertEqual(d['logs'],l)
    def test_unshown_alternative_still_invalidates_all(self):
        p,i,l=self.sample();l=[x for x in l if x.get('effect_id')!=i['effects'][1]['id']]
        self.assertIsNotNone(provenance.touch_log_provenance(p,i,l))
        i['effects'][1]['source_digest']='0'*64
        self.assertIsNone(provenance.touch_log_provenance(p,i,l))
    def edges(self,p):
        with connect(p)as db:return[dict(r)for r in db.execute("SELECT * FROM memory_edges WHERE evidence_kind='inferred_semantic_calls' AND valid_to IS NULL")]
    def mutation(self,e,key,value,inventory=None,logs=None):
        p,i,l=self.sample();i=i if inventory is None else inventory;l=l if logs is None else logs
        with connect(p)as db:db.execute('UPDATE memory_edges SET '+key+'=? WHERE id=?',(value,e['id']))
        try:return provenance.touch_log_provenance(p,i,l)
        finally:
            with connect(p)as db:db.execute('UPDATE memory_edges SET '+key+'=? WHERE id=?',(e[key],e['id']))
    def test_each_missing_wrong_edge_and_unknown_evidence_rejected(self):
        p,i,l=self.sample()
        for e in self.edges(p):
            for key,value in [('valid_to','retired'),('evidence_kind','static_semantic_calls'),('source_revision','wrong'),('target_id',999999)]:
                self.assertIsNone(self.mutation(e,key,value),(key,e['id']))
            for key,value in [('schema_version','unknown'),('adapter','wrong'),('evidence_class','static'),('source_digest','0'*64),('line',6)]:
                proof=json.loads(e['evidence']);proof[key]=value
                self.assertIsNone(self.mutation(e,'evidence',json.dumps(proof)),key)
    def test_confidence_invalid_and_changed_receipt(self):
        p,i,l=self.sample();before=provenance.touch_log_provenance(p,i,l);e=self.edges(p)[0]
        changed=self.mutation(e,'confidence',.4);self.assertIsNotNone(changed);self.assertNotEqual(changed,before)
        calls=[call for item in json.loads(changed)['items'] if item['kind']=='effects' for call in item['witness']['calls']]
        self.assertEqual(next(call['confidence']for call in calls if call['id']==e['id']),.4)
        original=provenance.one
        for value in (True,None,'0.55',float('inf'),float('nan'),-1,0,.9,1,2):
            def fake(db,table,clause,args):
                r=original(db,table,clause,args)
                if table=='memory_edges'and r['id']==e['id']:r['confidence']=value
                return r
            with patch.object(provenance,'one',side_effect=fake):self.assertIsNone(provenance.touch_log_provenance(p,i,l),repr(value))
    def test_effect_static_label_with_inferred_edge_rejected(self):
        p,i,l=self.sample();id=i['effects'][0]['id']
        with connect(p)as db:db.execute("UPDATE code_log_effects SET evidence_class='static_wrapped' WHERE id=?",(id,))
        i['effects'][0]['evidence_class']='static_wrapped'
        for x in l:
            if x.get('effect_id')==id:x['evidence_class']='static_wrapped'
        try:self.assertIsNone(provenance.touch_log_provenance(p,i,l))
        finally:
            with connect(p)as db:db.execute("UPDATE code_log_effects SET evidence_class='inferred_wrapped' WHERE id=?",(id,))
    def test_mixed_depth2_unsupported_whole_inventory(self):
        p,i,l=self.sample('mixed');self.assertTrue(any(x['wrapper_depth']==2 and x['evidence_class']=='inferred_wrapped'for x in i['effects']))
        self.assertIsNone(provenance.touch_log_provenance(p,i,l))
        self.assertIsNone(provenance.touch_log_provenance(p,i,[]))
    def test_global_complete_set_but_module_graph_and_event_fallback(self):
        for name,accepted in [('global-script-depth1-two',True),('existing-module-graph-rejection',False),('strong',False)]:
            p,_,_=self.sample(name);raw=build_context_facade(p).execute(Q);ordinary=compact_context(dict(raw));result=compact_context(raw)
            if not accepted:self.assertEqual(result,ordinary,name);continue
            anchors=result['query_handoff']['code_anchors'];self.assertEqual({a['file_path']for a in anchors},{'CanvasTouchPane.ets','TimelineTouchPanel.ets'})
            for a in anchors:
                excerpt=a['source_excerpts'][0];self.assertEqual((excerpt['start_line'],excerpt['end_line']),(5,8));self.assertEqual(excerpt['content'],'\n'.join(F['sources'][name][a['file_path']].splitlines()[4:8]))
            self.assertEqual(result['query_handoff']['log_anchors'],ordinary['query_handoff']['log_anchors']);self.assertLessEqual(result['output_budget']['estimated_tokens'],1500)
    def test_inferred_label_with_static_edge_rejected(self):
        p,i,l=self.sample('static');self.assertIsNotNone(provenance.touch_log_provenance(p,i,l));id=i['effects'][0]['id']
        with connect(p)as db:db.execute("UPDATE code_log_effects SET evidence_class='inferred_wrapped' WHERE id=?",(id,))
        i['effects'][0]['evidence_class']='inferred_wrapped'
        for x in l:
            if x.get('effect_id')==id:x['evidence_class']='inferred_wrapped'
        try:self.assertIsNone(provenance.touch_log_provenance(p,i,l))
        finally:
            with connect(p)as db:db.execute("UPDATE code_log_effects SET evidence_class='static_wrapped' WHERE id=?",(id,))
    def test_inferred_duplicate_edge_and_unshown_missing_sink(self):
        p,i,l=self.sample();e=self.edges(p)[0];row=dict(e);row.pop('id');keys=list(row)
        with connect(p)as db:new=db.execute('INSERT INTO memory_edges ('+','.join(keys)+') VALUES ('+','.join('?'for _ in keys)+')',[row[k]for k in keys]).lastrowid
        try:self.assertIsNone(provenance.touch_log_provenance(p,i,l))
        finally:
            with connect(p)as db:db.execute('DELETE FROM memory_edges WHERE id=?',(new,))
        # Keep candidate but hide its visible effect: sink still must validate.
        chosen=i['effects'][1];l=[x for x in l if x.get('effect_id')!=chosen['id']]
        with connect(p)as db:
            emit=dict(db.execute("SELECT * FROM memory_edges WHERE relation='emits_log' AND target_id=?",(chosen['sink_log_id'],)).fetchone())
            db.execute("UPDATE memory_edges SET valid_to='retired' WHERE id=?",(emit['id'],))
        try:self.assertIsNone(provenance.touch_log_provenance(p,i,l))
        finally:
            with connect(p)as db:db.execute('UPDATE memory_edges SET valid_to=? WHERE id=?',(emit['valid_to'],emit['id']))
