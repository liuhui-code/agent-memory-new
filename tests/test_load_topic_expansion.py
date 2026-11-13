# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
import unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.text import query_tokens

PROTOCOL = Path(__file__).resolve().parents[1] / 'docs/eval/load-topic-expansion-20261114/protocol.json'

class LoadTopicExpansionTests(AgentMemoryTestBase):
    def test_generic_loading_does_not_imply_network_or_user(self):
        tokens = set(query_tokens('加载'))
        self.assertIn('load', tokens)
        self.assertFalse(tokens & {'request', 'fetch', 'network', 'profile', 'account', 'user', 'data'})

    def test_explicit_other_triggers_preserve_prior_translation(self):
        for term in ('请求', '接口', '网络', '用户', '资料'):
            with self.subTest(term=term):
                self.assertTrue({'load', 'request', 'fetch', 'network', 'profile', 'account', 'user', 'data'} <= set(query_tokens(term)))
        self.assertIn('profile', query_tokens('加载用户资料'))
        self.assertIn('network', query_tokens('加载网络请求'))

    def test_public_local_loaders_keep_real_source(self):
        protocol = json.loads(PROTOCOL.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, source in protocol['sources'].items():
                (root / name).write_text(source)
            self.run_memory(root, 'init')
            self.run_memory(root, 'learn-path', '--path', '.', '--json')
            for case in protocol['queries']:
                # Generic network inference is independently red before this change;
                # it is recorded in observations, not silently redefined as a pass.
                if case['query'] in ('定位网络请求的方法。', '定位 NetworkClient 的网络请求方法。'):
                    continue
                with self.subTest(query=case['query']):
                    result = json.loads(self.run_memory(root, 'context', '--query', case['query'], '--compact', '--json').stdout)
                    anchors = result['query_handoff']['code_anchors']
                    self.assertEqual([case['expected']], [a['file_path'] for a in anchors])
                    source = '\n'.join(e['content'] for a in anchors for e in a.get('source_excerpts', []))
                    self.assertTrue(source.strip())
                    marker = {'TextureDecoder.ts': 'decodeTexture', 'SceneReader.ts': 'readScene',
                              'ProfileService.ts': 'fetchProfileData', 'NetworkClient.ts': 'network.fetch'}[case['expected']]
                    self.assertIn(marker, source)

    def _check_existing_network_case(self, index):
        protocol = json.loads(PROTOCOL.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, source in protocol['sources'].items():
                (root / name).write_text(source)
            self.run_memory(root, 'init')
            self.run_memory(root, 'learn-path', '--path', '.', '--json')
            case = protocol['queries'][index]
            out = json.loads(self.run_memory(root, 'context', '--query', case['query'], '--compact', '--json').stdout)
            self.assertEqual([case['expected']], [a['file_path'] for a in out['query_handoff']['code_anchors']])

    @unittest.expectedFailure
    def test_existing_generic_network_precision_red(self):
        self._check_existing_network_case(5)

    @unittest.expectedFailure
    def test_existing_named_network_precision_red(self):
        self._check_existing_network_case(6)
