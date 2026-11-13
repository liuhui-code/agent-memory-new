# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
import unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.ecma_callable_ranges import property_callback_ranges, member_callback_ranges

class CallbackLexicalTests(unittest.TestCase):
    def test_strings_comments_and_templates_do_not_create_callbacks(self):
        for source in [
            "const sample = '.onClick(() => { fake() })'",
            '// .onTouch(() => { fake() })',
            '/*\n.onChange(() => {\n fake()\n})\n*/',
            'const sample = `\n.onSubmit(() => { fake() })\n`',
        ]:
            with self.subTest(source=source):
                self.assertEqual([],member_callback_ranges(source.splitlines()))
    def test_real_callbacks_after_multiline_non_code_keep_lines(self):
        prefixes=['/*\n.onClick(() => { fake() })\n*/', 'const s = `plain .onTouch(() => {})`;']
        callback="Button('Run').onClick(\n () => {\n  launch('.onTouch(() => { fake() })')\n }\n)"
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                offset=len(prefix.splitlines()); found=member_callback_ranges((prefix+'\n'+callback).splitlines())
                self.assertEqual([('onClick',offset+1,offset+4)],[(r['symbol'],r['start_line'],r['end_line']) for r in found])

    def test_real_property_callback_and_string_parameters(self):
        source="const actions = [{\n caption: '.onClick(() => { text })',\n execute: (value: string = 'x') => {\n  use(value)\n }\n}]"
        found=property_callback_ranges(source.splitlines())
        self.assertEqual([('execute',3,5)],[(r['symbol'],r['start_line'],r['end_line']) for r in found])

    def test_uncertain_lexical_input_preserves_original_member_ranges(self):
        from tools.agent_memory_runtime.ecma_callback_mask import callback_mask_lines
        original = (Path(__file__).resolve().parents[1] / 'docs/evidence/binding-recovery-preview/legacy-ecma-callable-ranges.py.txt').read_text()
        namespace = {'__package__': 'tools.agent_memory_runtime'}
        exec(compile(original, '<baseline>', 'exec'), namespace)
        nested = 'value'
        for _ in range(40): nested = '`outer ${' + nested + '}`'
        for prefix in ['const s = `${button.onClick(() => { run() })}`;',
                       'const s = `${"`"}`;', 'const s = `${/* ` */ 1}`;',
                       'const s = `${flag ? `.onClick(() => { fake() })` : ""}`;',
                       'const pattern = /"/;', 'const pattern = /`/;',
                       'const quotient = a / b;', 'const s = `${a / b}`;',
                       'const s = `unterminated', 'const s = `' + 'x'*65537 + '`;',
                       'const s = ' + nested + ';']:
            with self.subTest(prefix=prefix[:80]):
                lines=(prefix + '\nButton().onClick(() => {\n real()\n})').splitlines()
                self.assertIsNone(callback_mask_lines(lines))
                self.assertEqual(namespace['member_callback_ranges'](lines), member_callback_ranges(lines))



class CallbackLexicalPublicTests(AgentMemoryTestBase):
    def test_public_literal_and_comment_are_not_function_owners(self):
        protocol=json.loads((Path(__file__).resolve().parents[1]/'docs/evidence/binding-recovery-preview/callback-lexical-protocol.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,source in protocol['sources'].items():(root/name).write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            symbols=self.list_records(root,'code-symbol')
            self.assertFalse(any(s['file_path']=='GuidePanel.ets' and s['symbol']=='onClick' for s in symbols))
            real=[s for s in symbols if s['file_path']=='LivePanel.ets' and s['symbol']=='onClick']
            self.assertEqual([(4,6)],[(s['start_line'],s['end_line']) for s in real])
            out=json.loads(self.run_memory(root,'context','--query',protocol['query'],'--json').stdout)
            primary=out['query_handoff']['callable_evidence'].get('primary',{})
            self.assertNotEqual(('GuidePanel.ets','onClick'),(primary.get('file_path'),primary.get('symbol')))
