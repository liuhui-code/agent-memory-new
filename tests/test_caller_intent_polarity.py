import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_caller_ownership import caller_owner_query

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/eval/indirect-caller-current/protocol.json'

class CallerIntentPolarityTests(AgentMemoryTestBase):
    def test_explicit_negative_and_background_are_not_caller_permission(self):
        for q in (
            'Find ModalBridge implementation. Do not return actual caller context.',
            'Find ModalBridge implementation, not the actual caller context.',
            'Show controller implementation; exclude onClick.',
            'Do not return actual caller context.',
            '返回控制器实现，不要返回调用方。',
            'Find controller implementation compared with actual caller context.',
            'Show controller implementation; exclude Panel.onClick.',
        ):
            with self.subTest(q=q): self.assertFalse(caller_owner_query(q))

    def test_positive_and_unknown_contrast_preserve_permission(self):
        for q in (
            'Find the actual caller of ModalBridge.finish.',
            'Find actual caller context, not the controller implementation.',
            'Return implementation, not only actual caller context but also metadata.',
            'Return implementation, not only actual caller context.',
            'Do not return only actual caller context.',
            'Return implementation, not just actual caller context.',
            'Do not return merely actual caller context.',
            "Don't return only actual caller context.",
            "Don't return just actual caller context.",
            "Don't return merely actual caller context.",
            'Return implementation, not implementation and also actual caller context.',
            'Do not return implementation but return actual caller context.',
            'Do not return implementation. Find actual caller context.',
            'Find actual caller context. Do not return implementation.',
            'Compare actual caller context with controller implementation.',
            'unlikeName actual caller context',
            'excludingRole actual caller context',
            '定位 onClick 调用方',
            'Find actual caller context with literal "do not return onClick".',
            'Find actual caller context; note \'do not return implementation\'.',
        ):
            with self.subTest(q=q): self.assertTrue(caller_owner_query(q))

    def test_public_negative_role_does_not_override_implementation_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,source in json.loads(FIXTURE.read_text())['sources'].items():
                (root/name).write_text(source)
            self.run_memory(root,'init'); self.run_memory(root,'learn-path','--path','.')
            for suffix in ('', '. Do not return actual caller context.', ', not the actual caller context.'):
                for mode in ([],['--compact']):
                    query='Find ModalBridge implementation'+suffix
                    data=json.loads(self.run_memory(root,'context','--query',query,'--json',*mode).stdout)
                    self.assertEqual('ModalBridge.ets',data['query_handoff']['code_anchors'][0]['file_path'])
            data=json.loads(self.run_memory(root,'context','--query','Find the actual caller of ModalBridge.finish.','--json').stdout)
            self.assertEqual('ConfirmPanel.ets',data['query_handoff']['code_anchors'][0]['file_path'])
