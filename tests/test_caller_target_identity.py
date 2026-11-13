# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.query_caller_ownership import collect_bounded_caller_owners, explicit_caller_target_ids
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

    def test_target_identity_not_incidental_literal_or_file_mention(self):
        targets=[{'id':1,'file_path':'ModalBridge.ets','owner_name':'ModalBridge','symbol':'finish'},
                 {'id':2,'file_path':'ModalBridge.ets','owner_name':'ModalBridge','symbol':'reset'}]
        self.assertEqual([1],explicit_caller_target_ids(targets,'Find actual caller of ModalBridge.finish with console.error logging.'))
        self.assertEqual([1],explicit_caller_target_ids(targets,'Find actual caller of ModalBridge.finish in ModalBridge.ets.'))
        self.assertIsNone(explicit_caller_target_ids(targets,'Find actual caller of ModalBridge with console.error logging.'))
        self.assertIsNone(explicit_caller_target_ids(targets,'Find actual caller context for the literal "ModalBridge.finish".'))
        self.assertEqual([],explicit_caller_target_ids(targets,'Find actual caller of MissingBridge.finish.'))
        self.assertEqual([1],explicit_caller_target_ids(targets,'Find actual caller of `ModalBridge.finish`.'))
        ambiguous=targets+[{'id':3,'file_path':'other/ModalBridge.ets','owner_name':'ModalBridge','symbol':'finish'}]
        self.assertEqual([],explicit_caller_target_ids(ambiguous,'Find actual caller of ModalBridge.finish.'))
        self.assertEqual([1,2],explicit_caller_target_ids(ambiguous,'Find actual callers of ModalBridge.ets.'))

    def test_missing_graph_does_not_substitute_same_file_method(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            sources=json.loads(P.read_text())['sources']
            sources['ConfirmPanel.ets']=sources['ConfirmPanel.ets'].replace('this.bridge.finish()', 'unresolved.finish()')
            for name,source in sources.items():(root/name).write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            self.assertEqual([],self.callers(root,'Find actual caller of ModalBridge.finish.'))

    def test_real_log_request_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.setup_fixture(root)
            (root/'TraceLog.ets').write_text("export class TraceLog {\n report(): void {\n  console.info('modal trace complete')\n }\n}\n")
            self.run_memory(root,'learn-path','--path','.')
            query='Find the log text "modal trace complete".'
            self.assertEqual([],self.callers(root,query))
            out=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)['query_handoff']
            self.assertIn('TraceLog.ets',{a['file_path'] for a in out['code_anchors']})

    def test_multiple_relation_targets_and_non_target_qualified_context(self):
        targets=[{'id':1,'file_path':'A.ets','owner_name':'A','symbol':'finish'},
                 {'id':2,'file_path':'A.ets','owner_name':'A','symbol':'reset'},
                 {'id':3,'file_path':'B.ets','owner_name':'B','symbol':'reset'}]
        for q in ['Find actual caller of A.finish and B.reset.',
                  'Find actual caller of A.finish and actual caller of B.reset.']:
            self.assertEqual([1,3],explicit_caller_target_ids(targets,q))
        self.assertEqual([1],explicit_caller_target_ids(targets,'Context console.error, find actual caller of A.finish.'))
        self.assertEqual([3],explicit_caller_target_ids(targets,'Find declaration A.finish and actual caller of B.reset.'))
        self.assertIsNone(explicit_caller_target_ids(targets,'Find declaration A.finish.'))

    def test_unrecalled_duplicate_definition_is_not_unique(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.setup_fixture(root)
            (root/'other').mkdir()
            (root/'other/UnrelatedName.ets').write_text("export class ModalBridge {\n finish(): void { other() }\n}\n")
            self.run_memory(root,'learn-path','--path','.')
            # Only ModalBridge.ets is supplied as a seed, intentionally excluding
            # the other definition. Its identity still prevents certification.
            self.assertEqual([],self.callers(root,'Find actual caller of ModalBridge.finish.'))
            raw=json.loads(self.run_memory(root,'context','--query','Find actual caller of ModalBridge.finish.','--json').stdout)
            self.assertFalse(any('caller_owner' in w.get('match_reasons',[]) for w in raw['wiki_matches']))
