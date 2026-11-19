"""Default path hints retain all current evidence and exploration limits."""
from copy import deepcopy
from unittest.mock import patch
from tests import test_graph_field_navigation as fixtures
from tools.agent_memory_runtime.context_graph_field_followup import append_graph_field_followup
from tools.agent_memory_runtime.context_budget import synchronize_estimate

class GraphFieldFollowupTests(fixtures.GraphFieldNavigationTests):
    def follow(self,base=None,raw=None):
        if base is None:
            base=deepcopy(self.empty);base['output_budget']['target_tokens']=1500;base['query_handoff']['next_queries']=[];synchronize_estimate(base)
        return append_graph_field_followup(self.project,self.raw if raw is None else raw,base)

    def test_default_two_paths_preserve_evidence(self):
        b=deepcopy(self.empty);b['output_budget']['target_tokens']=1500;b['query_handoff']['next_queries']=['old'];synchronize_estimate(b)
        d=self.follow(b);self.assertEqual(len(d['query_handoff']['next_queries']),3)
        self.assertEqual(d['query_handoff']['next_queries'][0],'old')
        restored=deepcopy(d);restored['query_handoff']['next_queries']=b['query_handoff']['next_queries'];restored['output_budget']=b['output_budget'];self.assertEqual(restored,b)

    def test_full_and_atomic_slots_unknown_shapes(self):
        for hints in (['a','b','c'],['a','b'],['x'*101],None,[1]):
            b=deepcopy(self.empty);b['output_budget']['target_tokens']=1500;b['query_handoff']['next_queries']=hints
            self.assertIs(self.follow(b),b)
        for b in (None,{}, {'output_budget':'bad'}):self.assertIs(append_graph_field_followup(self.project,self.raw,b),b)

    def test_duplicate_and_overflow(self):
        b=deepcopy(self.empty);b['output_budget']['target_tokens']=1500;b['query_handoff']['next_queries']=['src/pages/ProfileEditor.ets'];synchronize_estimate(b)
        d=self.follow(b);self.assertEqual(d['query_handoff']['next_queries'].count('src/pages/ProfileEditor.ets'),1)
        b['padding']='z'*7000;self.assertIs(self.follow(b),b)
        with patch('tools.agent_memory_runtime.context_graph_field_followup.estimate_payload_tokens',return_value=1501):
            b.pop('padding');self.assertIs(self.follow(b),b)

    def test_2000_raw_and_stale_noop(self):
        b=deepcopy(self.empty);self.assertIs(self.follow(b),b)
        raw=deepcopy(self.raw);raw['source_freshness']['generation']=-1
        b['output_budget']['target_tokens']=1500;self.assertIs(self.follow(b,raw),b)
        b.pop('output_budget');self.assertIs(self.follow(b),b)

    def test_hint_rejects_ambiguous_search_strings(self):
        for path in ('src/a:1.ets','src/"a".ets','src/../a.ets','src/a\n.ets','src/a b.ets'):
            with patch('tools.agent_memory_runtime.context_graph_field_followup.qualify_graph_field_navigation',return_value=[{'file_path':path}]):
                b=deepcopy(self.empty);b['output_budget']['target_tokens']=1500;b['query_handoff']['next_queries']=[];self.assertIs(self.follow(b),b)

    def test_default_wrong_field_log_and_identity_controls(self):
        for query in ['Find displayName in logs.', '必填客户编号为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。']:
            raw,b=deepcopy(self.raw),deepcopy(self.empty);raw['query']=b['query']=query;b['output_budget']['target_tokens']=1500;b['query_handoff']['next_queries']=[]
            self.assertIs(self.follow(b,raw),b)
        for key,value in [('source_id',999),('valid_to','expired')]:
            raw,b=deepcopy(self.raw),deepcopy(self.empty);raw['edge_matches'][0][key]=value;b['output_budget']['target_tokens']=1500;b['query_handoff']['next_queries']=[]
            self.assertIs(self.follow(b,raw),b)

    def test_default_source_import_resource_controls(self):
        b=deepcopy(self.empty);b['output_budget']['target_tokens']=1500;b['query_handoff']['next_queries']=[]
        twin=self.project.root/'src/services/ProfileGateway.ts';twin.write_text('export class ProfileGateway {}')
        try:self.assertIs(self.follow(b),b)
        finally:twin.unlink()
        for key in ['MAX_SECONDS','MAX_FILE_BYTES','MAX_TOTAL_BYTES','MAX_ROWS_PER_FILE','MAX_EDGES']:
            with patch('tools.agent_memory_runtime.context_graph_field_navigation.'+key,0):self.assertIs(self.follow(b),b)

    def test_only_one_positive_fits_budget_does_not_partially_append(self):
        from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens
        b=deepcopy(self.empty);b['output_budget']['target_tokens']=1500;b['query_handoff']['next_queries']=[]
        paths=self.follow(b)['query_handoff']['next_queries'];self.assertEqual(len(paths),2)
        found=False
        for n in range(3000):
            b['padding']='x'*n;single=deepcopy(b);single['query_handoff']['next_queries']=paths[:1];synchronize_estimate(single)
            both=deepcopy(b);both['query_handoff']['next_queries']=paths;synchronize_estimate(both)
            if estimate_payload_tokens(single)<=1500<estimate_payload_tokens(both):
                found=True;self.assertIs(self.follow(b),b);break
        self.assertTrue(found)

    def test_frozen_two_match_public_cli_default_and_2000(self):
        import json, tempfile, subprocess, sys
        from pathlib import Path
        from tools.agent_memory_runtime.storage import resolve_project
        from tests.archive_create_write_test_support import cli
        root_repo=Path(__file__).resolve().parents[1]
        frozen=json.loads((root_repo/'docs/releases/graph-field-navigation-20261118/development-controls/protocol.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'source';root.mkdir()
            for name,source in frozen['controls']['two-matches']['sources'].items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source)
            project=resolve_project(str(root),str(Path(temp)/'memory'))
            cli(project,'init');cli(project,'learn-path','--path','.','--json')
            args=['context','--query',frozen['query'],'--compact','--json','--project',str(root),'--memory-home',str(project.memory_home)]
            # Disable only the newly added terminal hook in a fresh process.
            runner="import sys,runpy;sys.path.insert(0,sys.argv[1]+'/tools');import agent_memory_runtime.context_graph_field_followup as f;f.append_graph_field_followup=lambda project,original,payload:payload;import agent_memory_runtime.context_graph_field_body as g;g.append_graph_field_display=lambda project,original,payload,**kw:payload;p=sys.argv.pop(1)+'/tools/agent_memory.py';sys.argv[0]=p;runpy.run_path(p,run_name='__main__')"
            before=subprocess.run([sys.executable,'-B','-c',runner,str(root_repo),*args],text=True,capture_output=True)
            self.assertEqual(before.returncode,0,before.stderr);b=json.loads(before.stdout)
            after=json.loads(cli(project,'context','--query',frozen['query'],'--compact','--json'))
            paths=after['query_handoff']['next_queries'];self.assertEqual(paths,['src/pages/ProfileEditor.ets'])
            self.assertIn(paths[0],[a['file_path']for a in after['query_handoff']['code_anchors']])
            added=after['query_handoff']['code_anchors'][-1];self.assertEqual((added['source_excerpts'][0]['start_line'],added['source_excerpts'][0]['end_line']),(6,12))
            restored=deepcopy(after);restored['query_handoff']['next_queries']=b['query_handoff']['next_queries'];restored['output_budget']=b['output_budget'];restored['query_handoff']['code_anchors']=b['query_handoff']['code_anchors'];restored['query_handoff']['source_excerpt_policy']=b['query_handoff']['source_excerpt_policy'];self.assertEqual(restored,b)
            large=json.loads(cli(project,'context','--query',frozen['query'],'--compact','--compact-token-budget','2000','--preserve-selected-source-anchors','--json'))
            self.assertEqual(large['query_handoff']['next_queries'],b['query_handoff']['next_queries'])
            self.assertIn(paths[0],[a['file_path']for a in large['query_handoff']['code_anchors']])
