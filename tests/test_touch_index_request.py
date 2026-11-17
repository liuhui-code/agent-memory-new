import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_touch_index_request import touch_index_request


class TouchIndexRequestTests(unittest.TestCase):
    def test_frozen_requests(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/touch_index_source.json').read_text())
        for case in fixture['requests']:
            with self.subTest(case=case['id']):self.assertEqual(touch_index_request(case['query']),True if case['permission']else None)
    def test_all_finite_combinations(self):
        for context in ('','触摸事件为空时第一个手指缺失并导致交互异常，','触摸输入没有首个触点时界面操作异常，'):
            for head in ('请定位','请查找','请只返回'):
                for operation in ('触摸回调和索引读取所在源码','触摸回调中按字面量索引读取触点的源码'):
                    for period in ('','。'):self.assertTrue(touch_index_request(context+head+operation+period))
    def test_no_normalization_or_extra_authority(self):
        base='请定位触摸回调和索引读取所在源码。'
        for value in (None,False,123,' '+base,base+' ',base+'\n','“'+base+'”',base+'同时找日志。',base.replace('索引读取','第一个触点读取'),base.replace('请定位','请定位 MyView 的'),base+'x'*120):
            with self.subTest(value=value):self.assertIsNone(touch_index_request(value))
