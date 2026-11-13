# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
import unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.text import query_tokens

FILES = {'src/ErrorConsoleSink.ets': 'export class ErrorConsoleSink {\n'
                             '  writeWarning(message: string): void {\n'
                             '    console.error(message)\n'
                             '  }\n'
                             '}\n',
 'src/InvoiceExporter.ets': 'export class InvoiceExporter {\n'
                            '  writeFile(context: UIContext): string {\n'
                            '    const directory = context.filesDir\n'
                            "    return directory + '/invoice.json'\n"
                            '  }\n'
                            '}\n',
 'src/PaletteParser.ets': 'export class PaletteParser {\n'
                          '  convertValue(value: string): number {\n'
                          "    const digits = value.replace('#', '')\n"
                          '    return Number.parseInt(digits, 16)\n'
                          '  }\n'
                          '}\n'}
QUERIES = ['请定位 invoice export 的 ArkTS 实现。', '请查找 invoice export 的 ArkTS 实现。', '请定位 palette 颜色转换的源码实现。', '请查找 palette 颜色转换的源码实现。', '请定位错误日志的输出入口。', '请定位 ErrorConsoleSink.writeWarning。', '请查找错误日志的输出入口。', '请定位异常打印的 console 源码。']

class LocateIntentExpansionTests(unittest.TestCase):
    def test_locator_is_retained_without_inventing_log_topic(self):
        tokens=set(query_tokens('请定位 invoice export 的源码'))
        self.assertIn('定位',tokens)
        self.assertFalse(tokens & {'log','logger','console','hilog','error','warning','exception','failed','failure','debug'})
    def test_all_existing_explicit_diagnostic_triggers_remain(self):
        expected={'log','logger','console','hilog','error','warning','exception','failed','failure','debug'}
        for trigger in ['日志','报错','错误','异常','失败','崩溃','打印']:
            self.assertTrue(expected <= set(query_tokens('请定位'+trigger)),trigger)
    def test_explicit_logger_identifier_is_still_recalled_literally(self):
        self.assertIn('error',query_tokens('请定位 ErrorConsoleSink.writeWarning'))

class LocateIntentPublicTests(AgentMemoryTestBase):
    def test_nonlog_domains_and_real_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name,text in FILES.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            observed=[]
            for index,query in enumerate(QUERIES):
                h=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)['query_handoff']
                paths={a['file_path'] for a in h['code_anchors']};observed.append(paths)
                expected='src/InvoiceExporter.ets' if index<2 else 'src/PaletteParser.ets' if index<4 else 'src/ErrorConsoleSink.ets'
                self.assertEqual({expected},paths,query)
                body=' '.join(e['content'] for a in h['code_anchors'] for e in a.get('source_excerpts',[]))
                self.assertIn('context.filesDir' if index<2 else 'Number.parseInt' if index<4 else 'console.error',body)
            self.assertEqual(observed[0],observed[1]);self.assertEqual(observed[2],observed[3])
