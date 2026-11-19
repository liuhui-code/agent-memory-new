from copy import deepcopy
from unittest.mock import patch
from tests.test_graph_field_navigation import GraphFieldNavigationTests
from tools.agent_memory_runtime.context_graph_field_body import append_graph_field_display
from tools.agent_memory_runtime.context_graph_field_followup import append_graph_field_followup
from tools.agent_memory_runtime.context_budget import synchronize_estimate

class GraphFieldBodyTests(GraphFieldNavigationTests):
    def base1500(self):
        b=deepcopy(self.empty);b['output_budget']['target_tokens']=1500;b['query_handoff']['next_queries']=[]
        b['query_handoff']['source_excerpt_policy'].update(excerpt_count=0,excerpt_chars=0)
        synchronize_estimate(b);return b
    def test_two_bodies_and_full_hint_independent(self):
        for hints in ([],['a','b','c']):
            b=self.base1500();b['query_handoff']['next_queries']=hints
            d=append_graph_field_display(self.project,self.raw,b,enabled=True)
            self.assertEqual(len(d['query_handoff']['code_anchors']),2)
            self.assertTrue(all(a['source_excerpts'][0]['content'].endswith('  }') for a in d['query_handoff']['code_anchors']))
            old=append_graph_field_followup(self.project,self.raw,b)
            restored=deepcopy(d);restored['query_handoff']['code_anchors']=old['query_handoff']['code_anchors'];restored['query_handoff']['source_excerpt_policy']=old['query_handoff']['source_excerpt_policy'];restored['output_budget']=old['output_budget'];self.assertEqual(restored,old)
    def test_body_overflow_keeps_old_hints(self):
        b=self.base1500();old=append_graph_field_followup(self.project,self.raw,b)
        with patch('tools.agent_memory_runtime.context_graph_field_body.estimate_payload_tokens',return_value=1501):
            self.assertEqual(append_graph_field_display(self.project,self.raw,b,enabled=True),old)
    def test_disabled_modes_and_unknown_shape(self):
        for b in (None,{}, {'output_budget':'bad'},self.base):
            self.assertEqual(append_graph_field_display(self.project,self.raw,b,enabled=True),append_graph_field_followup(self.project,self.raw,b))
        b=self.base1500();self.assertEqual(append_graph_field_display(self.project,self.raw,b,enabled=False),append_graph_field_followup(self.project,self.raw,b))

    def test_full_slots_body_atomic_and_hints_retained(self):
        b=self.base1500()
        b['query_handoff']['code_anchors']=[dict(file_path='unrelated.ets',role='expansion')]
        old=append_graph_field_followup(self.project,self.raw,b)
        self.assertEqual(append_graph_field_display(self.project,self.raw,b,enabled=True),old)

    def test_oversize_body_receipt_keeps_hint(self):
        from tools.agent_memory_runtime.context_graph_field_navigation import qualify_graph_field_navigation, _DisplayReceipt
        b=self.base1500();r=qualify_graph_field_navigation(self.project,self.raw,b,_capture_body=True)
        invalid=_DisplayReceipt(r.query,r.project_id,r.generation,r.navigation,None)
        with patch('tools.agent_memory_runtime.context_graph_field_body.qualify_graph_field_navigation',return_value=invalid):
            self.assertEqual(append_graph_field_display(self.project,self.raw,b,enabled=True),append_graph_field_followup(self.project,self.raw,b))

    def test_identity_source_and_unknown_permission_noop(self):
        for q in ('Find displayName in logs.','不要显示名源码，只看日志。','必填客户编号为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。'):
            b=self.base1500();r=deepcopy(self.raw);r['query']=b['query']=q
            self.assertEqual(append_graph_field_display(self.project,r,b,enabled=True),b)
        for key,value in [('source_id',999),('valid_to','expired')]:
            b=self.base1500();r=deepcopy(self.raw);r['edge_matches'][0][key]=value
            self.assertEqual(append_graph_field_display(self.project,r,b,enabled=True),b)
        for key in ['MAX_SECONDS','MAX_FILE_BYTES','MAX_TOTAL_BYTES','MAX_ROWS_PER_FILE','MAX_EDGES']:
            b=self.base1500()
            with patch('tools.agent_memory_runtime.context_graph_field_navigation.'+key,0):
                self.assertEqual(append_graph_field_display(self.project,self.raw,b,enabled=True),b)

    def test_body_timeout_retains_qualified_hints(self):
        from tools.agent_memory_runtime.context_graph_field_navigation import qualify_graph_field_navigation
        b=self.base1500()
        with patch('tools.agent_memory_runtime.context_graph_field_navigation.monotonic',return_value=0) as clock:
            qualify_graph_field_navigation(self.project,self.raw,b)
            calls=clock.call_count
        with patch('tools.agent_memory_runtime.context_graph_field_navigation.monotonic',side_effect=[0]*calls+[100]*100):
            d=append_graph_field_display(self.project,self.raw,b,enabled=True)
        self.assertEqual(d,append_graph_field_followup(self.project,self.raw,b))

    def test_unknown_old_body_schema_preserves_hint_baseline(self):
        for key,value in [('source_excerpt',{'content':'old'}),('source_excerpts','old')]:
            b=self.base1500();b['query_handoff']['code_anchors']=[dict(file_path='unrelated.ets',role='primary',**{key:value})]
            old=append_graph_field_followup(self.project,self.raw,b)
            self.assertEqual(append_graph_field_display(self.project,self.raw,b,enabled=True),old)

    def test_frozen_sql_field_permissions_disjoint_and_order_compatible(self):
        import json
        from pathlib import Path
        from tools.agent_memory_runtime.context_field_alternative import field_read_request
        from tools.agent_memory_runtime.query_sql_reading_request import sql_reading_request
        from tools.agent_memory_runtime.context_sql_reading import append_sql_reading
        from tests.test_sql_reading import SqlReadingTests
        root=Path(__file__).resolve().parents[1]
        protocol=json.loads((root/'docs/evidence/sql-reading/protocol.json').read_text())
        for query in protocol['positive_queries']:
            self.assertIsNone(field_read_request(query))
        self.assertIsNone(sql_reading_request(self.raw['query']))
        b=self.base1500();old=append_sql_reading(self.project,self.raw,append_graph_field_followup(self.project,self.raw,b))
        sql_first=append_graph_field_followup(self.project,self.raw,append_sql_reading(self.project,self.raw,b))
        self.assertEqual(sql_first,old)

    def test_real_oversize_source_body_retains_navigation(self):
        import tempfile,json
        from pathlib import Path
        from tools.agent_memory_runtime.storage import resolve_project
        from tools.agent_memory_runtime.context_composition import build_context_facade
        from tools.agent_memory_runtime.context_compact import compact_context
        from tools.agent_memory_runtime.source_exploration import exploration_contract
        from tests.archive_create_write_test_support import cli
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'source';root.mkdir()
            for src in self.project.root.rglob('*.ets'):
                dest=root/src.relative_to(self.project.root);dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text('\n'.join((' '*300+line if 6<=i<=12 else line) for i,line in enumerate(src.read_text().splitlines(),1))+'\n')
            project=resolve_project(str(root),str(Path(temp)/'memory'));cli(project,'init');cli(project,'learn-path','--path','.','--json')
            raw=deepcopy(dict(build_context_facade(project).execute(self.raw['query'])))
            b=compact_context(deepcopy(raw));b['query_handoff']['code_anchors']=[];b['query_handoff']['source_exploration']=exploration_contract();b['query_handoff']['next_queries']=[];b['query_handoff']['source_excerpt_policy']=dict(source='current_worktree',body_persisted=False,excerpt_count=0,excerpt_chars=0);synchronize_estimate(b)
            # Unit input supplies current typed edges; not a natural public retrieval claim.
            from tools.agent_memory_runtime.storage import connect
            with connect(project) as db:
                raw['edge_matches']=[dict(r) for r in db.execute("SELECT * FROM memory_edges WHERE relation='imports' AND valid_to IS NULL")]
            raw['source_freshness']['status']='current';b['source_freshness']['status']='current'
            old=append_graph_field_followup(project,raw,b)
            self.assertEqual(len(old['query_handoff']['next_queries']),2)
            self.assertEqual(append_graph_field_display(project,raw,b,enabled=True),old)

    def test_only_one_body_fits_atomic_budget(self):
        from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens
        b=self.base1500();full=append_graph_field_display(self.project,self.raw,b,enabled=True)
        self.assertEqual(len(full['query_handoff']['code_anchors']),2)
        found=False
        for n in range(2000):
            trial=deepcopy(full);trial['padding']='x'*n
            single=deepcopy(trial);single['query_handoff']['code_anchors'].pop();es=[a['source_excerpts'][0]for a in single['query_handoff']['code_anchors']];single['query_handoff']['source_excerpt_policy'].update(excerpt_count=len(es),excerpt_chars=sum(len(e['content'])for e in es));synchronize_estimate(single);synchronize_estimate(trial)
            if estimate_payload_tokens(single)<=1500<estimate_payload_tokens(trial):
                b['padding']='x'*n;synchronize_estimate(b)
                self.assertEqual(append_graph_field_display(self.project,self.raw,b,enabled=True),append_graph_field_followup(self.project,self.raw,b));found=True;break
        self.assertTrue(found)
