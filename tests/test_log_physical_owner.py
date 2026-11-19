# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.code_wiki_extractors import extract_log_statements

class LogPhysicalOwnerTests(AgentMemoryTestBase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'source';self.root.mkdir()

    def test_inline_log_after_literal_separator_has_physical_owner(self):
        for language,ext in [('TypeScript','ts'),('JavaScript','js'),('ArkTS','ets')]:
            for sep in [' ', '\u2028', '\u2029']:
                for nl in ['\n','\r\n','\r']:
                    source="export class JobWorker {\n  label = 'Display%slabel'\n  run() { console.error('request failed') }\n}\n" % sep
                    p=self.root/('Source.'+ext);p.write_bytes(source.replace('\n',nl).encode())
                    logs=extract_log_statements(p,language)
                    self.assertEqual([(l['line'],l['function'],l['message_template'])for l in logs],[(3,'run','request failed')])
                    p.write_bytes(source.rstrip('\n').replace('\n',nl).encode())
                    self.assertEqual(extract_log_statements(p,language), logs)

    def test_two_methods_and_noncode_cannot_steal_owner(self):
        source="""export class JobWorker {
  first() { const text = 'Display\u2028label' }
  second() { console.error('second failed') }
  fake() { const text = `console.error('fake failed')` }
  // console.error('comment failed')
}
console.error('top level failed')
"""
        p=self.root/'Source.ts';p.write_text(source)
        logs=extract_log_statements(p,'TypeScript')
        self.assertEqual([(l['line'],l['function'],l['message_template'])for l in logs],
                         [(3,'second','second failed'),(7,None,'top level failed')])

    def test_public_list_reports_physical_function(self):
        for name,ext,owner,method,sep in [('worker','ts','JobWorker','run','\u2028'),('bridge','js','FetchBridge','connect','\u2029')]:
            root=self.root/name;root.mkdir()
            (root/('Source.'+ext)).write_text(f"export class {owner} {{\n  label = 'Display{sep}label'\n  {method}() {{ console.error('{name} request failed') }}\n}}\n")
            self.run_memory(root,'learn-path','--path','.')
            logs=json.loads(self.run_memory(root,'list','--type','code-log','--json').stdout)
            self.assertEqual([(l['line'],l['function'])for l in logs],[(3,method)])

    def test_code_separator_cannot_certify_same_line_callable(self):
        for sep in ('\u2028','\u2029'):
            p=self.root/'Source.js'
            p.write_text("function first() {}"+sep+"function second() { console.error('second failed') }\n")
            logs=extract_log_statements(p,'JavaScript')
            self.assertEqual([(l['line'],l['function'],l['message_template'])for l in logs],[(1,None,'second failed')])

    def test_callback_and_non_ecma_owner_controls(self):
        source="""export class Task {
  label = 'Display\u2028label'
  run() {
    const callback = () => { console.error('nested failed') }
    console.error('outer failed')
  }
}
"""
        p=self.root/'Source.ts';p.write_text(source)
        unicode_logs=extract_log_statements(p,'TypeScript')
        p.write_text(source.replace('\u2028',' '))
        self.assertEqual(unicode_logs,extract_log_statements(p,'TypeScript'))
        p=self.root/'Source.py';p.write_text("def run():\n    print('hello')\n    logging.error('python failed')")
        logs=extract_log_statements(p,'Python')
        self.assertEqual([(l['line'],l['function'])for l in logs],[(2,'run'),(3,'run')])
