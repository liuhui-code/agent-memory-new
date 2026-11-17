"""Normally learned callback identities; no saved query outputs or DB recall."""
from copy import copy,deepcopy
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.command_table_test_support import prepare
from tools.agent_memory_runtime.query_results import _context_pass
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import _compact_context
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.query_touch_index_trial import make_touch_trial,trial_state,PassCaptures
from tools.agent_memory_runtime.query_touch_index_selection import (
    TouchIndexContext,qualified_touch_index,bind_touch_index_context,touch_index_receipt,
    compact_touch_index,enrich_touch_index,accounting_touch_index,
)
from tools.agent_memory_runtime.storage import connect

P=json.loads((Path(__file__).parent/'fixtures/touch_index_source.json').read_text())
Q=P['requests'][0]['query']


class TouchIndexSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.samples={};cls.log_captures={}
        for world in ('original-two-positive','supplement-three-positive','supplement-four-positive','supplement-positive-plus-unknown','original-length-only'):
            folder=Path(cls.temp.name)/world;folder.mkdir()
            project=prepare(folder,sources=P['sources'][world]);state=trial_state(project)
            baseline_capture=PassCaptures();capture=PassCaptures()
            base=_context_pass(project,Q,touch_capture=baseline_capture)
            trial=_context_pass(project,Q,allow_touch_recall=True,touch_capture=capture)
            assert len(capture)==1
            cls.log_captures[project.project_id]=(baseline_capture.logs[0],capture.logs[0])
            path=build_context_facade(project).path_context.build(Q)
            cls.samples[world]=(project,base,trial,capture[0],state,path)
    def setUp(self):
        for world,(project,*_) in self.samples.items():
            for name,text in P['sources'][world].items():(project.root/name).write_text(text)
    def sample(self,world='original-two-positive'):
        project,base,trial,pool,state,path=self.samples[world]
        return project,deepcopy(base),deepcopy(trial),deepcopy(pool),state,deepcopy(path)
    def make_trial(self,project,query,base,raw,pool,state):
        captures=self.log_captures[project.project_id]
        return make_touch_trial(project,query,base,raw,pool,state,*captures)
    def bind(self,world='original-two-positive'):
        project,base,raw,pool,state,path=self.sample(world)
        trial=self.make_trial(project,Q,base,raw,pool,state)
        return project,base,trial,bind_touch_index_context(project,Q,base,trial),path
    def test_actual_callback_ranges_and_all_positive_scope(self):
        for world,count in [('original-two-positive',2),('supplement-three-positive',3),('supplement-positive-plus-unknown',2)]:
            project,base,raw,pool,_,_=self.sample(world)
            result=qualified_touch_index(project,pool);self.assertIsNotNone(result)
            anchors,members,files,_=result;self.assertEqual(len(anchors),count)
            self.assertEqual(len(members),count)
            for a,r in zip(anchors,members):
                self.assertEqual(r['symbol'],'onTouch');self.assertTrue(r['signature'].startswith('callback onTouch@'))
                self.assertTrue(any(x.get('kind')=='symbol' and x['id']==r['id'] for x in pool))
                self.assertEqual((r['start_line'],r['end_line']),(5,8))
                self.assertEqual(a['source_excerpts'][0]['content'],'\n'.join(P['sources'][world][a['file_path']].splitlines()[4:8]))
            self.assertEqual(len(files),len({x['file_path']for x in pool}))
    def test_db_only_owner_file_witnesses_are_bound_not_serving_roots(self):
        project,base,trial,bound,_=self.bind()
        self.assertIsInstance(bound,TouchIndexContext)
        self.assertTrue(all(r['kind']=='symbol' and r['symbol'] in ('build','onTouch') for r in trial._pool))
        frames=json.loads(bound._frames)
        self.assertTrue(all(f['file'] and len(f['owner_witnesses'])==1 for f in frames))
        self.assertTrue(all(r['symbol']=='onTouch' for r in bound._members))
        with connect(project)as db:
            owner=dict(db.execute("SELECT * FROM code_symbols WHERE project_id=? AND symbol='CanvasTouchPane'",(project.project_id,)).fetchone())
        for key,value in [('project_id','other'),('owner_kind','class'),('qualified_name','Other'),('start_line',3),('end_line',9),('source_digest','0'*64),('index_generation',999),('signature','changed-only-witness')]:
            with connect(project)as db:db.execute('UPDATE code_symbols SET '+key+'=? WHERE id=?',(value,owner['id']))
            try:
                self.assertIsNone(touch_index_receipt(bound,pending=True),key)
            finally:
                with connect(project)as db:db.execute('UPDATE code_symbols SET '+key+'=? WHERE id=?',(owner[key],owner['id']))
        self.assertIsNotNone(touch_index_receipt(bound,pending=True))
    def test_duplicate_owner_alias_any_admitted_path_fails(self):
        project,_,_,pool,_,_=self.sample()
        with connect(project)as db:
            owners=[dict(r)for r in db.execute("SELECT * FROM code_symbols WHERE project_id=? AND symbol_type='component'",(project.project_id,))]
        self.assertEqual(len(owners),2)
        with connect(project)as db:db.execute('UPDATE code_symbols SET symbol_key=? WHERE id=?',(owners[0]['symbol_key'],owners[1]['id']))
        try:self.assertIsNone(qualified_touch_index(project,pool))
        finally:
            with connect(project)as db:db.execute('UPDATE code_symbols SET symbol_key=? WHERE id=?',(owners[1]['symbol_key'],owners[1]['id']))
    def test_no_callback_completion_from_db(self):
        project,_,_,pool,_,_=self.sample()
        callbacks=[r for r in pool if str(r.get('signature','')).startswith('callback onTouch@')]
        self.assertEqual(len(callbacks),2)
        removed=[r for r in pool if r is not callbacks[0]]
        self.assertIsNone(qualified_touch_index(project,removed))
        only_build=[r for r in pool if not str(r.get('signature','')).startswith('callback ')]
        self.assertIsNone(qualified_touch_index(project,only_build))
    def test_four_positive_and_no_witness_fallback(self):
        for world in ('supplement-four-positive','original-length-only'):
            project,base,trial,bound,_=self.bind(world)
            self.assertIs(bound,base)
    def test_bound_raw_copy_mutation_and_original_query(self):
        project,base,trial,bound,path=self.bind();self.assertIsInstance(bound,TouchIndexContext)
        self.assertEqual(dict(bound),base);self.assertEqual(accounting_touch_index(bound),base)
        self.assertIsNotNone(touch_index_receipt(bound,pending=True))
        for cloned in (dict(bound),copy(bound),deepcopy(bound),json.loads(json.dumps(bound)),TouchIndexContext(dict(bound))):
            self.assertIsNone(touch_index_receipt(cloned,pending=True))
        forged=TouchIndexContext(dict(bound));forged._issuer=object()
        self.assertIsNone(touch_index_receipt(forged,pending=True))
        bound['query']=Q+'x';self.assertIsNone(touch_index_receipt(bound,pending=True))
        _,_,_,bound,_=self.bind();bound._pool[0]['score']=999
        self.assertIsNone(touch_index_receipt(bound,pending=True))
        _,_,trial,bound,_=self.bind();trial._pool[0]['score']=999
        self.assertIsNone(touch_index_receipt(bound,pending=True))
    def test_baseline_signature_and_forged_trial(self):
        project,base,raw,pool,state,_=self.sample();trial=self.make_trial(project,Q,base,raw,pool,state)
        for forged in (dict(trial),copy(trial),deepcopy(trial),None):
            self.assertIs(bind_touch_index_context(project,Q,base,forged),base)
        base['advisory_notice']='changed after pass'
        self.assertIs(bind_touch_index_context(project,Q,base,trial),base)
    def test_both_pass_logs_identity_graph_and_paths_reject(self):
        for side in ('base','trial'):
            for key in ('log','identity_match','graph_neighbor','graph_relation','log_identity_match','path','candidate_log','unknown_candidate_log'):
                project,base,raw,pool,state,_=self.sample();target=base if side=='base'else raw
                h=target['query_handoff']
                if key in ('candidate_log','unknown_candidate_log'):
                    target['query_audit']['candidate_recall']['tables']['code_log_statements']['candidate_count']=1 if key=='candidate_log' else None
                elif key=='log':h['log_anchors']=[{'message_template':'unrelated log'}]
                elif key=='path':h['path_context']={'activated':True,'path_candidates':[]}
                else:h['code_anchors']=[{'file_path':'Protected.ets',key:True}]
                trial=self.make_trial(project,Q,base,raw,pool,state)
                self.assertIs(bind_touch_index_context(project,Q,base,trial),base,(side,key))
    def test_pool_corruption_and_cross_project_types_reject(self):
        for key,value in [('id',True),('source_digest','0'*64),('index_generation',999),('project_id','other'),('symbol_key',None),('signature','build():unknown'),('end_line',99)]:
            project,_,_,pool,_,_=self.sample()
            callback=next(r for r in pool if str(r.get('signature','')).startswith('callback '));callback[key]=value
            self.assertIsNone(qualified_touch_index(project,pool),key)
    def test_source_drift_unreadable_and_unknown_drift_are_atomic(self):
        for name in ('CanvasTouchPane.ets','OffsetTouchPane.ets'):
            project,base,trial,bound,path=self.bind('supplement-positive-plus-unknown')
            self.assertIsInstance(bound,TouchIndexContext)
            file=project.root/name;original=file.read_bytes();file.write_bytes(original+b'// drift\n')
            self.assertIsNone(touch_index_receipt(bound,pending=True));file.write_bytes(original)
        project,_,_,bound,_=self.bind();file=project.root/'CanvasTouchPane.ets';old=file.with_suffix('.saved');file.rename(old)
        try:self.assertIsNone(touch_index_receipt(bound,pending=True))
        finally:old.rename(file)
    def test_changed_index_state_invalidates_issued_trial(self):
        project,base,trial,bound,_=self.bind()
        with connect(project)as db:
            row=dict(db.execute('SELECT * FROM code_files WHERE project_id=? LIMIT 1',(project.project_id,)).fetchone())
            db.execute('UPDATE code_files SET index_generation=index_generation+1 WHERE id=?',(row['id'],))
        try:self.assertIsNone(touch_index_receipt(bound,pending=True))
        finally:
            with connect(project)as db:db.execute('UPDATE code_files SET index_generation=? WHERE id=?',(row['index_generation'],row['id']))
    def test_enrichment_rechecks_path_and_binding(self):
        _,base,_,bound,path=self.bind()
        changed=dict(path,activated=True)
        self.assertNotIsInstance(enrich_touch_index(bound,Q,changed,base['source_freshness']),TouchIndexContext)
        self.assertNotIsInstance(enrich_touch_index(bound,Q+'x',path,base['source_freshness']),TouchIndexContext)
    def test_empty_baseline_report_is_preserved_with_independent_current_receipt(self):
        _,base,_,bound,path=self.bind();self.assertEqual(base['source_freshness']['status'],'empty')
        enriched=enrich_touch_index(bound,Q,path,base['source_freshness']);ordinary=_compact_context(dict(enriched))
        after=compact_touch_index(enriched,ordinary)
        self.assertIsNot(after,ordinary)
        self.assertEqual(restore_whitelist(after,ordinary),ordinary)
        self.assertEqual(len(after['query_handoff']['code_anchors']),2)
        self.assertEqual(enriched['source_freshness']['status'],'empty')
        self.assertEqual(after['source_freshness'],ordinary['source_freshness'])

    def test_fake_empty_partial_trial_bool_generation_and_stale_reports_reject(self):
        changes=[('base','candidate_file_count',1),('base','checked_file_count',1),
                 ('base','current_file_count',1),('base','generation',True),
                 ('base','blocked_rows',1),('base','stale_paths',['a.ets']),
                 ('trial','generation',True),('trial','generation',99),
                 ('trial','status','partial_current'),('trial','blocked_rows_by_table',{'symbols':1}),
                 ('trial','missing_paths',['missing.ets']),('trial','boundary_drift_scope_ids',['scope'])]
        for side,key,value in changes:
            project,base,raw,pool,state,_=self.sample()
            (base if side=='base'else raw)['source_freshness'][key]=value
            trial=self.make_trial(project,Q,base,raw,pool,state)
            self.assertIs(bind_touch_index_context(project,Q,base,trial),base,(side,key))
    def test_complete_set_budget_fallback_and_no_trial_accounting(self):
        _,base,_,bound,path=self.bind('supplement-three-positive')
        self.assertIsInstance(bound,TouchIndexContext)
        enriched=enrich_touch_index(bound,Q,path,base['source_freshness'])
        ordinary=_compact_context(dict(enriched));out=compact_touch_index(enriched,ordinary)
        self.assertEqual(len(out['query_handoff']['code_anchors']),3)
        self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
        self.assertEqual(accounting_touch_index(enriched),dict(enriched))
        tiny=deepcopy(ordinary);tiny['output_budget']['target_tokens']=100
        self.assertIs(compact_touch_index(enriched,tiny),tiny)


if __name__=='__main__':unittest.main()
