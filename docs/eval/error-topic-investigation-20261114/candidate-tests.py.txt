# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
import unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.text import query_tokens
from tools.agent_memory_runtime.query_intent_contract import infer_memory_intent_v2

PROTOCOL = Path(__file__).resolve().parents[1] / 'docs/eval/error-topic-investigation-20261114/protocol.json'

class ErrorTopicExpansionTests(AgentMemoryTestBase):
    def test_generic_error_word_does_not_invent_logging_apis(self):
        tokens = set(query_tokens('错误'))
        self.assertIn('error', tokens)
        self.assertFalse(tokens & {'log', 'logger', 'console', 'hilog', 'warning', 'exception', 'failed', 'failure', 'debug'})

    def test_legacy_intent_and_explicit_diagnostic_words_stay(self):
        for query in ('错误', 'badge error feedback', '查找 packet 错误返回的实现。'):
            self.assertEqual('runtime_log_diagnosis', infer_memory_intent_v2(query))
        expected = {'log', 'logger', 'console', 'hilog', 'error', 'warning', 'exception', 'failed', 'failure', 'debug'}
        for trigger in ('日志', '报错', '异常', '失败', '崩溃', '打印'):
            self.assertTrue(expected <= set(query_tokens(trigger)), trigger)
        self.assertTrue(expected <= set(query_tokens('错误日志')))
        self.assertIn('hilog', query_tokens('错误 hilog'))

    def _check_cases(self, cases, intent=None):
        protocol = json.loads(PROTOCOL.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, source in protocol['sources'].items():
                (root / name).write_text(source)
            self.run_memory(root, 'init')
            self.run_memory(root, 'learn-path', '--path', '.', '--json')
            for index in cases:
                case = protocol['queries'][index]
                args = ['context', '--query', case['query'], '--compact', '--json']
                if intent: args += ['--intent', intent]
                with self.subTest(query=case['query'], intent=intent):
                    out = json.loads(self.run_memory(root, *args).stdout)
                    anchors = out['query_handoff']['code_anchors']
                    self.assertEqual([case['expected']], [a['file_path'] for a in anchors])
                    body = '\n'.join(e['content'] for a in anchors for e in a.get('source_excerpts', []))
                    self.assertIn(case['body'], body)

    def test_public_ui_and_value_errors_and_genuine_log_controls(self):
        self._check_cases([0, 1, 2, 3, 4, 6, 7, 8, 9])

    def test_explicit_code_lane_does_not_override_token_semantics(self):
        self._check_cases([0, 2], 'code_location')

    @unittest.expectedFailure
    def test_existing_hilog_precision_red_is_not_claimed_fixed(self):
        self._check_cases([5])
