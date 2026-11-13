# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
import unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.text import query_tokens

FILES = {'src/ClipboardReader.ets': 'export class ClipboardReader {\n'
                            '  readContent(): string {\n'
                            '    return '
                            'pasteboard.getSystemPasteboard().getData().getPrimaryText()\n'
                            '  }\n'
                            '}\n',
 'src/PaletteConverter.ets': 'export class PaletteConverter {\n'
                             '  convertValue(value: string): number {\n'
                             '    return Number.parseInt(value, 16)\n'
                             '  }\n'
                             '}\n',
 'src/ProfileService.ets': 'export class ProfileService {\n'
                           '  fetchUser(): string {\n'
                           "    console.info('load request network profile "
                           "account user data')\n"
                           "    return network.fetch('/user/profile')\n"
                           '  }\n'
                           '}\n'}
QUERIES = ['请返回读取 clipboard 剪贴板数据的实现。', '请返回读取 clipboard 剪贴板内容的实现。', '请返回 palette 数据转换实现。', '请返回 palette 内容转换实现。', '请返回加载用户资料的网络实现。', '请返回 ProfileService.fetchUser。']

class DataTopicExpansionTests(unittest.TestCase):
    def test_data_translation_does_not_imply_network_or_profile(self):
        tokens=set(query_tokens('请返回 palette 数据转换实现'))
        self.assertIn('data',tokens)
        self.assertIn('数据',tokens)
        self.assertFalse(tokens & {'load','request','fetch','network','profile','account','user'})
    def test_existing_specific_triggers_remain(self):
        # Generic loading has its separate load-only translation contract.
        expected={'load','request','fetch','network','profile','account','user','data'}
        for trigger in ['请求','接口','网络','用户','资料']:
            self.assertTrue(expected <= set(query_tokens(trigger)),trigger)

class DataTopicPublicTests(AgentMemoryTestBase):
    def test_nonnetwork_data_and_explicit_profile_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name,text in FILES.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            observed=[]
            for index,query in enumerate(QUERIES):
                h=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)['query_handoff']
                paths={a['file_path'] for a in h['code_anchors']};observed.append(paths)
                expected='src/ClipboardReader.ets' if index<2 else 'src/PaletteConverter.ets' if index<4 else 'src/ProfileService.ets'
                self.assertEqual({expected},paths,query)
                body=' '.join(e['content'] for a in h['code_anchors'] for e in a.get('source_excerpts',[]))
                self.assertIn('getSystemPasteboard' if index<2 else 'Number.parseInt' if index<4 else 'network.fetch',body)
            self.assertEqual(observed[0],observed[1]);self.assertEqual(observed[2],observed[3])
