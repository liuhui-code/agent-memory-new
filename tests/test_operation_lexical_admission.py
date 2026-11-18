# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite producer controls, not a public query acceptance campaign."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime import arkts_ui_behavior as op
from tools.agent_memory_runtime.code_wiki_extractors import summarize_file
from tools.agent_memory_runtime.source_range_focus import arkts_source_mechanisms

ROOT = Path(__file__).resolve().parents[1]

class OperationLexicalTests(unittest.TestCase):
    def legacy(self, text):
        with patch.object(op, 'callback_mask_lines', return_value=None):
            return op.extract_arkts_operation_names(text)

    def test_existing_sources_and_both_consumers(self):
        sources = json.loads((ROOT/'docs/evidence/disclosure-lexical/controls.json').read_text())['sources']
        with tempfile.TemporaryDirectory() as directory:
            for name, text in sources.items():
                with self.subTest(name=name):
                    expected = name not in ('OnlyText.ets', 'Quoted.ets')
                    self.assertEqual(expected, 'rotate' in op.extract_arkts_operation_names(text))
                    self.assertEqual(expected, 'rotate' in arkts_source_mechanisms(text))
                    path = Path(directory)/name
                    path.write_text(text)
                    self.assertEqual(expected, 'rotate' in op.summary_operation_names(summarize_file(path,'ArkTS')))

    def test_quotes_comments_plain_templates_and_crlf(self):
        for literal in ["'fake ).rotate('", '"fake \\" ).rotate("', '`fake ).rotate(`', '/* ).rotate( */']:
            text = 'const note = '+literal+';\r\nButton().height(1).rotate(2);\r\nrouter.pushUrl({});'
            with self.subTest(literal=literal):
                self.assertEqual(['height','rotate','pushUrl'],op.extract_arkts_operation_names(text))

    def test_unknown_preserves_complete_legacy_including_interpolation(self):
        for text in ['const s=`${router.pushUrl({})}`;', 'const s=`fake ).rotate( ${value}`;',
                     'const regex=/x/; Button().rotate(1);', 'const ratio=a/b; Button().rotate(1);',
                     'const s="unterminated ).rotate(', '/* unclosed ).rotate(',
                     'const s=`'+'x'*65537+'`; Button().rotate(1);']:
            with self.subTest(text=text[:65]):
                self.assertEqual(self.legacy(text),op.extract_arkts_operation_names(text))
        self.assertEqual(['pushUrl'],op.extract_arkts_operation_names('const s=`${router.pushUrl({})}`;'))

    def test_no_new_mask_adjacency_or_unicode_line_relocation(self):
        text = 'Button() "literal" .rotate(1);'
        self.assertEqual([],self.legacy(text))
        self.assertEqual([],op.extract_arkts_operation_names(text))
        text = 'const x="prefix\u2028 ).rotate(";\nButton().height(1);'
        self.assertEqual(['height'],op.extract_arkts_operation_names(text))

    def test_filter_before_dedup_and_twelve_cap(self):
        text = 'const note="fake ).rotate(";\nButton().height(1).rotate(2).height(3);'
        self.assertEqual(['height','rotate'],op.extract_arkts_operation_names(text))
        text = 'const note="'+' '.join(').fake'+str(i)+'(' for i in range(14))+'";\n'
        text += '\n'.join('Button().op'+str(i)+'();' for i in range(14))
        self.assertEqual(['op'+str(i) for i in range(12)],op.extract_arkts_operation_names(text))
        self.assertEqual(['pushUrl'],op.extract_arkts_operation_names('router.pushUrl({}); router.PUSHURL({});'))

    def test_untrusted_mask_coordinates_preserve_legacy(self):
        text='const note="fake ).rotate(";\nButton().height(1);'
        for mask in [[], [''], ['x'*len(line) for line in text.split('\n')]]:
            with patch.object(op, 'callback_mask_lines', return_value=mask):
                actual=op.extract_arkts_operation_names(text)
            self.assertEqual(self.legacy(text), actual)
