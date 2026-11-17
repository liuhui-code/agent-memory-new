"""Ordinary accounting is exactly once; compact trials conservatively uncounted."""
from copy import deepcopy
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.command_table_test_support import prepare
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context,_compact_context
from tools.agent_memory_runtime.query_touch_index_selection import TouchIndexContext,compact_touch_index

Q='请定位触摸回调和索引读取所在源码。'

class TouchAccountingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        fixture=json.loads((Path(__file__).parent/'fixtures/touch_index_source.json').read_text())
        cls.projects={}
        for world in ('original-two-positive','supplement-four-positive'):
            folder=Path(cls.tmp.name)/world;folder.mkdir()
            cls.projects[world]=prepare(folder,sources=fixture['sources'][world])

    def test_raw_accept_repeated_compact_and_tiny_do_not_recount(self):
        with patch('tools.agent_memory_runtime.query_results.record_context_use')as use,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
            data=build_context_facade(self.projects['original-two-positive']).execute(Q)
            self.assertIsInstance(data,TouchIndexContext)
            self.assertEqual(data['wiki_matches'],[])
            self.assertEqual(use.call_count,1);self.assertEqual(miss.call_count,1)
            self.assertEqual(use.call_args.args[1]['wiki_matches'],[])
            first=compact_context(data);second=compact_context(data)
            self.assertEqual(first,second)
            self.assertEqual(len(first['query_handoff']['code_anchors']),2)
            tiny=_compact_context(dict(data));tiny['output_budget']['target_tokens']=100
            self.assertIs(compact_touch_index(data,tiny),tiny)
            self.assertEqual(use.call_count,1);self.assertEqual(miss.call_count,1)

    def test_overflow_rejection_only_accounts_baseline(self):
        with patch('tools.agent_memory_runtime.query_results.record_context_use')as use,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
            data=build_context_facade(self.projects['supplement-four-positive']).execute(Q)
            self.assertNotIsInstance(data,TouchIndexContext)
            self.assertEqual(data['wiki_matches'],[])
            compact_context(data)
            self.assertEqual(use.call_count,1);self.assertEqual(miss.call_count,1)
            self.assertEqual(use.call_args.args[1]['wiki_matches'],[])
