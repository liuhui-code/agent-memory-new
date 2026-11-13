# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.query_caller_ownership import collect_bounded_caller_owners
P=Path(__file__).resolve().parents[1]/'docs/eval/indirect-caller-current/protocol.json'
class CallerTargetIdentityTests(AgentMemoryTestBase):
    def setup_fixture(self,root,extra=False):
        sources=json.loads(P.read_text())['sources']
        if extra:sources['ReviewPanel.ets']=sources['ConfirmPanel.ets'].replace('ConfirmPanel','ReviewPanel')
        for name,source in sources.items():(root/name).write_text(source)
        self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
    def callers(self,root,query):
        project=resolve_project(str(root),str(self.memory_home(root)))
        return collect_bounded_caller_owners(project,[{'file_path':'ModalBridge.ets','score':20}],query)
    def test_public_explicit_method_is_not_other_method_in_same_file(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.setup_fixture(root)
            out=json.loads(self.run_memory(root,'context','--query','Find the actual caller of ModalBridge.finish.','--json').stdout)
            callers={w['file_path'] for w in out['wiki_matches'] if 'caller_owner' in w.get('match_reasons',[])}
            self.assertEqual({'ConfirmPanel.ets'},callers)
            compact=json.loads(self.run_memory(root,'context','--query','Find the actual caller of ModalBridge.finish.','--compact','--json').stdout)
            paths={a['file_path'] for a in compact['query_handoff']['code_anchors']}
            self.assertIn('ConfirmPanel.ets',paths);self.assertNotIn('ResetPanel.ets',paths)
    def test_actual_edges_respect_member_and_broad_file_targets(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.setup_fixture(root)
            for query,expected in [('Find actual caller of ModalBridge.finish.',{'ConfirmPanel.ets'}),('Find actual caller of ModalBridge.reset.',{'ResetPanel.ets'}),('Find actual callers of ModalBridge.ets.',{'ConfirmPanel.ets','ResetPanel.ets'}),('Find actual callers of ModalBridge.finish and ModalBridge.reset.',{'ConfirmPanel.ets','ResetPanel.ets'}),('Find actual caller of ModalBridge.missing.',set())]:
                with self.subTest(query=query):self.assertEqual(expected,{x['file_path'] for x in self.callers(root,query)})
    def test_two_real_callers_are_not_collapsed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.setup_fixture(root,True)
            rows=self.callers(root,'Find actual callers of ModalBridge.finish.')
            self.assertEqual({'ConfirmPanel.ets','ReviewPanel.ets'},{r['file_path'] for r in rows})
