# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_render_source import parse_render_source

D = Path(__file__).parents[1] / 'docs/evidence/render-expression-witness-design'
BASE = json.loads((D / 'protocol.json').read_text())['source_controls'][0]['source']


class RenderSourceTests(unittest.TestCase):
    def test_frozen_nineteen(self):
        for case in json.loads((D / 'protocol.json').read_text())['source_controls']:
            with self.subTest(case=case['id']):
                self.assertEqual(bool(parse_render_source(case['source'])), case['positive'])

    def test_frozen_ten_closed_files(self):
        for case in json.loads((D / 'combination-source-controls.json').read_text()):
            with self.subTest(case=case['id']):
                self.assertEqual(bool(parse_render_source(case['source'])), case['positive'])

    def test_ranges_and_crlf(self):
        expected = dict(owner='MessageSurface', build_start=4, build_end=6,
                        helper='plainBody', helper_start=7, helper_end=9)
        for source in (BASE, BASE.replace('\n', '\r\n'), BASE.replace('\n', '\r')):
            self.assertEqual(parse_render_source(source), expected)

    def test_asi_comment_and_identifier_boundaries(self):
        for replacement in ('return\nthis', 'return/*\n*/this', 'ret/*x*/urn this'):
            self.assertIsNone(parse_render_source(BASE.replace('return this', replacement)))
        self.assertTrue(parse_render_source(BASE.replace('return this', 'return /*same line*/ this')))
        self.assertIsNone(parse_render_source(BASE.replace('plainBody()', 'plain/*x*/Body()')))

    def test_text_statement_boundaries(self):
        for separator in ('\n', ';', '/*\n*/'):
            s = BASE.replace('Text(this.plainBody())', "Text('label')" + separator + 'Text(this.plainBody())')
            self.assertTrue(parse_render_source(s))
        for separator in (' ', '/*no newline*/', ''):
            s = BASE.replace('Text(this.plainBody())', "Text('label')" + separator + 'Text(this.plainBody())')
            self.assertIsNone(parse_render_source(s))
        s = BASE.replace('Text(this.plainBody())', 'Text(this.plainBody());Text(this.plainBody())')
        self.assertIsNone(parse_render_source(s))

    def test_limits(self):
        for n in (7, 8):
            s = BASE.replace('Text(this.plainBody())', "Text('label');" * n + 'Text(this.plainBody())')
            self.assertEqual(bool(parse_render_source(s)), n == 7)
        for n in (8, 9):
            s = BASE.replace(".replace('<p>', '').replace('</p>', '')", ".replace('<p>', '')" * n)
            self.assertEqual(bool(parse_render_source(s)), n == 8)
        self.assertIsNone(parse_render_source(BASE.replace('return this', ' ' * 32769 + 'return this')))
        self.assertIsNone(parse_render_source(' ' * (2 * 1024 * 1024) + BASE))

    def test_literals_and_patterns(self):
        for tag in ('<p>', '</P2>', '<br />'):
            self.assertTrue(parse_render_source(BASE.replace("'<p>'", repr(tag))))
        for tag in ('<p x>', '<3>', '<p/>', '< p>', '<p>junk'):
            self.assertIsNone(parse_render_source(BASE.replace("'<p>'", repr(tag))))
        for flags in ("", ", ''", ", 'g'"):
            s = BASE.replace("'<p>', ''", "new RegExp('<[^>]*>'" + flags + "), ''")
            self.assertTrue(parse_render_source(s))
        for expression in ("/<[^>]+>/g, ''", "new RegExp('<[^>]+>', 'gi'), ''", "new RegExp('<[^>]+>'), '\\n'"):
            self.assertIsNone(parse_render_source(BASE.replace("'<p>', ''", expression)))
        self.assertTrue(parse_render_source(BASE.replace("'<p>', ''", "'<p>', '\\n'")))
        self.assertIsNone(parse_render_source(BASE.replace("'<p>'", "'\\x3cp>'")))

    def test_closed_member_and_shadow(self):
        for field in ("  value: Model = new Model()\n", "  @State private flag: boolean = true\n", "  amount: number = -1.5\n"):
            self.assertTrue(parse_render_source(BASE.replace('  build()', field + '  build()')))
        for field in ("  value = new Model()\n", "  value: Model = new Other()\n", "  value: Text = new Text()\n", "  value: plainBody = new plainBody()\n", "  Text: string = ''\n"):
            self.assertIsNone(parse_render_source(BASE.replace('  build()', field + '  build()')))
        self.assertIsNone(parse_render_source("import { plainBody } from './x'\n" + BASE))
        self.assertIsNone(parse_render_source(BASE + BASE.replace('MessageSurface', 'OtherSurface')))

    def test_full_syntax_and_malformed_tokens(self):
        for changed in (BASE + "'tail'", BASE.replace('Column()', 'Row([)] )'), BASE.replace('Text(this.plainBody())', 'Text(this.plainBody()).width(1)'), BASE.replace("return this", "this.plainBody(); return this"), BASE.replace("return this.content", "return this.content + this.content")):
            self.assertIsNone(parse_render_source(changed))
        for value in (None, '\ud800', BASE.replace('return this', 'return\u2028this'), BASE.replace("''", '`label`', 1)):
            self.assertIsNone(parse_render_source(value))


if __name__ == '__main__':
    unittest.main()
