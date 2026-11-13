# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.ecma_callable_ranges import member_callback_ranges


class MemberCallbackOpeningTests(AgentMemoryTestBase):
    def protocol(self):
        return json.loads(Path('docs/evidence/touch-callback-opening/protocol.json').read_text())

    def test_public_callback_range_and_method_evidence(self):
        p=self.protocol()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,source in p['sources'].items():(root/name).write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.', '--json')
            rows=json.loads(self.run_memory(root,'list','--type','code-symbol','--limit','100','--json').stdout)
            byname={r.get('qualified_name'):r for r in rows}
            touch=byname['InlineTouch.onTouch@5']
            self.assertEqual((5,7),(touch['start_line'],touch['end_line']))
            self.assertIn('touch',touch['method_evidence'].split())
            self.assertNotIn('onclick',touch['method_evidence'].split())
            self.assertNotIn('click',touch['method_evidence'].split())
            self.assertEqual((8,10),(byname['InlineTouch.onClick@8']['start_line'],byname['InlineTouch.onClick@8']['end_line']))
            self.assertEqual((6,8),(byname['SplitTouch.onTouch@6']['start_line'],byname['SplitTouch.onTouch@6']['end_line']))
            for q in p['queries']:
                out=json.loads(self.run_memory(root,'context','--query',q['query'],'--json').stdout)
                primary=out['query_handoff']['callable_evidence']['primary']
                self.assertEqual(q['file'],primary['file_path'])
                self.assertEqual(q['expected_range'],[primary['source_range']['start_line'],primary['source_range']['end_line']])

    def test_known_nested_body_string_comment_and_multiline_header(self):
        lines=["Row() { Button('({)').onTouch((event:","  TouchEvent) => {",'  // } .onClick(() => {',
               '  if (event) { consume(event) }','})','}']
        self.assertEqual((1,5),(member_callback_ranges(lines)[0]['start_line'],member_callback_ranges(lines)[0]['end_line']))
        lines=["Row() { Button('}').onTouch((event) => {",'  /* { */ consume(event)','})','}']
        self.assertEqual(3,member_callback_ranges(lines)[0]['end_line'])

    def test_earlier_arrow_and_object_parameter_header(self):
        lines=["const render = () => { Button().onTouch((event: {code: number}) => {",
               '  consume(event.code)', '})', '}']
        self.assertEqual(3,member_callback_ranges(lines)[0]['end_line'])

    def test_inner_function_type_arrow_keeps_legacy_range(self):
        p=json.loads(Path('docs/evidence/touch-callback-opening/function-type-review-protocol.json').read_text())
        for lines in p['controls']:
            self.assertEqual(len(lines),member_callback_ranges(lines)[0]['end_line'])

    def test_unknown_mask_keeps_legacy_range(self):
        lines=self.protocol()['sources']['InlineTouch.ets'].splitlines()
        for prefix in ['const ratio = a / b;', 'const s = `${event}`;', 'const pattern = /"/;']:
            result=member_callback_ranges([prefix,*lines])
            self.assertEqual(result,[
                {'symbol':'onTouch','start_line':6,'end_line':12,'selection_reason':'arkts_dsl_callback_window'},
                {'symbol':'onClick','start_line':9,'end_line':11,'selection_reason':'arkts_dsl_callback_window'}])
