# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from collections import Counter
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.agent_memory_runtime.code_wiki_extractors import extract_symbols
from tools.agent_memory_runtime.ecma_callable_ranges import (
    MAX_CALLBACK_RANGES, callable_ranges_for_language, dedupe_ranges,
)


class CallbackSymbolMultiplicityTests(unittest.TestCase):
    def extract(self, text, language='ArkTS'):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.ets'
            path.write_text(text)
            return extract_symbols(path, language)

    def test_same_owner_two_callbacks_in_all_ecma_languages(self):
        source = '''export class Handlers {
  configure() {
    const first = {
      execute: () => {
        this.first()
      }
    }
    const second = {
      execute: () => {
        this.second()
      }
    }
  }
}
'''
        for language in ['ArkTS', 'TypeScript', 'JavaScript']:
            with self.subTest(language=language):
                symbols = Counter(self.extract(source, language))
                self.assertEqual(2, symbols['execute', 'function'])
                self.assertEqual(1, symbols['configure', 'function'])

    def test_single_callback_unchanged(self):
        source = 'export class Handler {\n  execute = () => {\n    this.run()\n  }\n}\n'
        for language in ['ArkTS', 'TypeScript', 'JavaScript']:
            self.assertEqual(1, Counter(self.extract(source, language))['execute', 'function'])

    def test_ordinary_same_name_methods_remain_two(self):
        source = 'class First {\n  execute() {\n  }\n}\nclass Second {\n  execute() {\n  }\n}\n'
        for language in ['ArkTS', 'TypeScript', 'JavaScript']:
            symbols = Counter(self.extract(source, language))
            self.assertEqual(2, symbols['execute', 'function'])
            self.assertEqual(1, symbols['First', 'class'])
            self.assertEqual(1, symbols['Second', 'class'])

    def test_mixed_method_and_property_callbacks_add_only_deficit(self):
        source = '''class Handlers {
  execute() {
  }
  configure() {
    const first = {
      execute: () => {
      }
    }
    const second = {
      execute: () => {
      }
    }
  }
}
'''
        for language in ['ArkTS', 'TypeScript', 'JavaScript']:
            self.assertEqual(3, Counter(self.extract(source, language))['execute', 'function'])

    def test_duplicate_range_from_two_recognizers_counts_once(self):
        ranges = [dict(symbol='execute', start_line=2, end_line=4, selection_reason=reason)
                  for reason in ['callable_mechanism_window', 'ecma_property_callback_window']]
        self.assertEqual(1, len(dedupe_ranges(ranges)))
        with patch('tools.agent_memory_runtime.code_wiki_extractors.callable_ranges_for_language', return_value=ranges):
            self.assertEqual([('execute', 'function')], self.extract(''))

    def test_distinct_range_same_symbol_not_collapsed(self):
        source = 'execute: () => {\n}\nexecute: () => {\n}\n'
        ranges = callable_ranges_for_language(source.splitlines(), 'TypeScript')
        self.assertEqual(2, len({(r['symbol'], r['start_line'], r['end_line']) for r in ranges}))
        self.assertEqual(2, Counter(self.extract(source, 'TypeScript'))['execute', 'function'])

    def test_no_callback_does_not_add_functions(self):
        self.assertEqual([('Empty', 'class')], self.extract('export class Empty {\n}\n'))
        self.assertEqual([], self.extract('// nothing callable\n'))

    def test_callback_range_limit_is_not_expanded(self):
        source = ''.join('execute: () => {\n}\n' for _ in range(MAX_CALLBACK_RANGES + 1))
        self.assertEqual(MAX_CALLBACK_RANGES, Counter(self.extract(source, 'TypeScript'))['execute', 'function'])

    def test_arkts_builder_filter_still_applies(self):
        self.assertNotIn(('Text', 'function'), self.extract('Text: () => {\n}\nText: () => {\n}\n'))

    def test_contaminated_same_name_keeps_old_behavior(self):
        real = 'execute: () => {\n}\n'
        fake = 'execute: () => {\n}\n'
        for language in ['ArkTS', 'TypeScript', 'JavaScript']:
            for wrapper in ['/*\n%s*/\n', 'const message = `\n%s`;\n']:
                for source in [wrapper % fake + real, real + wrapper % fake,
                               real + wrapper % fake + real]:
                    with self.subTest(language=language, source=source):
                        self.assertEqual(1, Counter(self.extract(source, language))['execute', 'function'])

    def test_unrelated_contaminated_name_does_not_block_real_multiplicity(self):
        source = 'execute: () => {\n}\n/*\nother: () => {\n}\n*/\nexecute: () => {\n}\n'
        counts = Counter(self.extract(source))
        self.assertEqual(2, counts['execute', 'function'])
        self.assertEqual(1, counts['other', 'function'])  # unchanged legacy behavior

    def test_comment_newlines_do_not_shift_callback_identities(self):
        source = '/*\nordinary comment\n*/\nexecute: () => {\n}\n/*\nsecond comment\n*/\nexecute: () => {\n}\n'
        for newline in ['\n', '\r\n']:
            self.assertEqual(2, Counter(self.extract(source.replace('\n', newline)))['execute', 'function'])

    def test_contamination_does_not_delete_existing_ordinary_rows(self):
        source = 'class A {\n execute() {\n }\n}\nclass B {\n execute() {\n }\n}\n/*\nexecute: () => {\n}\n*/\n'
        self.assertEqual(2, Counter(self.extract(source))['execute', 'function'])

    def test_no_expansion_avoids_mask_rescan(self):
        with patch('tools.agent_memory_runtime.code_wiki_extractors.code_mask', side_effect=AssertionError('unneeded rescan')):
            self.assertEqual(1, Counter(self.extract('execute: () => {\n}\n'))['execute', 'function'])
            self.assertEqual([], self.extract('// empty\n'))
            self.assertEqual(2, Counter(self.extract('class A {\n execute() {\n }\n}\nclass B {\n execute() {\n }\n}\n'))['execute', 'function'])

    def test_non_ecma_extraction_unchanged(self):
        self.assertEqual([('execute', 'function'), ('execute', 'function')],
                         self.extract('def execute():\n    pass\ndef execute():\n    pass\n', 'Python'))


if __name__ == '__main__':
    unittest.main()
