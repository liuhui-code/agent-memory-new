import unittest
from tools.agent_memory_runtime.ui_divider_source import parse_ui_divider_file

GLYPH = """@Component
export struct GlyphList {
 build() {
  List() {
   ListItem() { Text('glyph') }
  }.divider({ strokeWidth: 2 })
 }
}
"""
INVENTORY = """@Component
export struct InventoryList {
  @State rows: string[] = []

  build() {
    List() {
      ForEach(this.rows, (row: string) => {
        ListItem() {
          Text(row)
        }
      })
    }
    .divider({ strokeWidth: 1, color: Color.Gray })
  }
}
"""
NONMATCH = """@Component
export struct GlyphList {
 @State selectedCategory: number = 0
 build() {
  Column() {
   Grid() { GridItem() { Text('divider List strokeWidth') } }
   Row() { TextInput({ placeholder: 'glyph' }) }
   .shadow({ radius: 12 }).backgroundColor(Color.White)
  }
 }
}
"""


class UiDividerSourceTests(unittest.TestCase):
    def parse(self, source=GLYPH, names=('GlyphList',)):
        return parse_ui_divider_file(source, names)

    def reject(self, *sources):
        for source in sources:
            with self.subTest(source=source):
                self.assertIsNone(self.parse(source))

    def test_complete_source_ranges_and_static_sites(self):
        p = self.parse()['GlyphList']
        self.assertEqual((p['owner_start'], p['owner_end'], p['build_start'], p['build_end']), (2, 8, 3, 7))
        self.assertEqual(p['sites'], [dict(start_line=6, end_line=6, stroke_width='2')])
        p = self.parse(INVENTORY, ('InventoryList',))['InventoryList']
        self.assertEqual((p['owner_start'], p['owner_end'], p['build_start'], p['build_end']), (2, 15, 5, 14))
        self.assertTrue(p['positive'])

    def test_multiple_and_same_file_typed_frames(self):
        second = GLYPH.replace('GlyphList', 'GlyphRows')
        p = self.parse(GLYPH + second, ('GlyphList', 'GlyphRows'))
        self.assertEqual(set(p), {'GlyphList', 'GlyphRows'})
        self.assertEqual(p.declared_names, ('GlyphList', 'GlyphRows'))
        only_requested = self.parse(GLYPH + second)
        self.assertEqual(set(only_requested), {'GlyphList'})
        self.assertEqual(only_requested.declared_names, ('GlyphList', 'GlyphRows'))
        self.assertEqual(p['GlyphRows']['build_start'], 11)
        self.assertTrue(all(x['positive'] for x in p.values()))
        self.assertIsNone(self.parse(GLYPH, ('GlyphList', 'Missing')))
        self.assertIsNone(self.parse(GLYPH + GLYPH))

    def test_nonmatch_needs_lexical_not_positive_ui_grammar(self):
        p = self.parse(NONMATCH)['GlyphList']
        self.assertFalse(p['positive'])
        self.assertEqual(p['sites'], [])
        self.assertEqual((p['build_start'], p['build_end']), (4, 10))
        self.reject(NONMATCH.replace(' @State', ' \"ignored\"\n @State', 1),
                    NONMATCH.replace(' build() {', ' \"ignored\" build() {'),
                    NONMATCH.replace(' build() {', ' build() {}\n build() {'),
                    NONMATCH.replace(' build() {', ' extra() {}\n build() {'),
                    NONMATCH.replace('\n}\n', '\n \"ignored\"\n}\n'))
        self.assertFalse(self.parse(GLYPH.replace("List() {\n   ListItem() { Text('glyph') }\n  }.divider({ strokeWidth: 2 })", "Text('divider')"))['GlyphList']['positive'])

    def test_comments_and_strings_never_supply_structure(self):
        p = self.parse(GLYPH.replace("Text('glyph')", "Text('List divider strokeWidth') /* divider({ broken */"))
        self.assertTrue(p['GlyphList']['positive'])
        p = self.parse(NONMATCH.replace("Text('divider List strokeWidth')", "Text('ForEach \\\\u List') /* \\u0041 divider */"))
        self.assertFalse(p['GlyphList']['positive'])
        self.reject(GLYPH.replace('  }.divider', "  } 'ignored' .divider"),
                    GLYPH.replace(' build() {', " 'ignored' build() {"),
                    GLYPH.replace('strokeWidth: 2', "strokeWidth: 2, 'ignored'"))

    def test_shadow_and_import_in_any_component(self):
        self.reject('function List(): Object { return {} }\n' + GLYPH,
                    "import { List } from './custom'\n" + GLYPH,
                    "import { Custom as List } from './custom'\n" + GLYPH,
                    GLYPH + GLYPH.replace('GlyphList', 'List'),
                    GLYPH + GLYPH.replace('GlyphList', 'divider'),
                    GLYPH.replace(' build() {', ' @State List: number = 0\n build() {'),
                    GLYPH.replace(' build() {', ' List() {}\n build() {'))
        self.assertIsNone(self.parse(INVENTORY.replace('(row: string)', '(List: string)'), ('InventoryList',)))
        self.assertIsNone(self.parse(INVENTORY.replace('(row: string)', '(divider: string)'), ('InventoryList',)))

    def test_reserved_bindings(self):
        self.reject(GLYPH.replace('GlyphList', 'true'),
                    GLYPH.replace(' build() {', ' @State this: number = 0\n build() {'),
                    NONMATCH.replace('selectedCategory', 'this'),
                    NONMATCH.replace('  Column() {', '  ForEach(this.rows, (this: string) => { Text(this) })\n  Column() {'))
        self.assertIsNone(self.parse(INVENTORY.replace('(row: string)', '(this: string)'), ('InventoryList',)))

    def test_numeric_scope_is_closed(self):
        for value in ['01', '00.2', '1.', '.5', '-1', '+1', '1e2', '1_000', 'NaN', 'Infinity', '9' * 33]:
            self.reject(GLYPH.replace('strokeWidth: 2', 'strokeWidth: ' + value))
        for value in ['0', '0.25', '12', '2.50']:
            self.assertTrue(self.parse(GLYPH.replace('strokeWidth: 2', 'strokeWidth: ' + value))['GlyphList']['positive'])

    def test_object_members_are_all_enumerated(self):
        for text in ['strokeWidth: 2, strokeWidth: 3', 'color: Color.Gray', 'strokeWidth: 2, color: Color.Gray, color: Color.Red',
                     'strokeWidth: 2,,', ', strokeWidth: 2', 'strokeWidth: 2, "ignored"',
                     'strokeWidth: 2, ...other', '["strokeWidth"]: 2', 'strokeWidth', 'strokeWidth: value']:
            self.reject(GLYPH.replace('strokeWidth: 2', text))
        for text in ['strokeWidth: 2,', "color: 'gray', strokeWidth: 2", 'strokeWidth: 2, color: Color.Gray,']:
            self.assertTrue(self.parse(GLYPH.replace('strokeWidth: 2', text))['GlyphList']['positive'])

    def test_wrong_or_unclosed_receiver_is_unknown(self):
        self.reject(GLYPH.replace('List()', 'Text()'), GLYPH.replace('List()', 'List(1)'),
                    GLYPH.replace('}.divider', '}.backgroundColor(Color.Gray).divider'),
                    GLYPH.replace('}.divider', '}.divider({ strokeWidth: 1 }).divider'),
                    GLYPH.replace("ListItem() { Text('glyph') }", "ListItem() { Text('glyph').divider({ strokeWidth: 2 }) }"),
                    GLYPH.replace('strokeWidth: 2', 'strokeWidth: 2)'))

    def test_computed_and_optional_before_negative_classification(self):
        for body in ["obj['divider']({ strokeWidth: 1 })", 'obj["div\\u0069der"]({ strokeWidth: 1 })',
                     "obj?.divider({ strokeWidth: 1 })", "obj[name]({ strokeWidth: 1 })", "Text(['divider'])"]:
            self.reject(NONMATCH.replace('  Column() {', '  ' + body + '\n  Column() {'),
                        GLYPH.replace(' build() {', ' build() {\n  ' + body))

    def test_lexical_unknown_rejects_before_negative_certificate(self):
        for body in ["Text('unterminated)", "Text('line\nstring')", 'Text("line\nstring")',
                     "Text(`divider`)", "Text(`${value}`)", "Text(/divider/)", 'For\\u0045ach()', 'Text(?)', '/* open']:
            self.reject(NONMATCH.replace('  Column() {', body + '\n  Column() {'))
        self.reject(GLYPH[:-3], GLYPH + '"ignored"', GLYPH.replace('List()', 'List(,)'),
                    GLYPH.replace('\n', '\r'), GLYPH.replace('\n', '\u2028'))
        self.assertEqual(self.parse(GLYPH.replace('\n', '\r\n'))['GlyphList']['build_start'], 3)

    def test_all_member_and_body_syntax_closed_for_positive(self):
        self.reject(GLYPH.replace(' build() {', ' extra() {}\n build() {'),
                    GLYPH.replace(' build() {', ' build() {}\n build() {'),
                    GLYPH.replace("Text('glyph')", "helper()"),
                    GLYPH.replace("Text('glyph')", "Text(return)"),
                    GLYPH.replace('strokeWidth: 2', 'strokeWidth: 2, color: return.value'),
                    GLYPH.replace("Text('glyph')", "Text('glyph'),"),
                    GLYPH.replace(' build() {', ' @State rows: string[] = ["a",,]\n build() {'),
                    GLYPH.replace(' build() {', ' @State rows: string[] = []\n @State rows: string[] = []\n build() {'))
        valid = GLYPH.replace(' build() {', ' @State rows: string[] = ["a", "b",]\n build() {')
        self.assertTrue(self.parse(valid)['GlyphList']['positive'])
        self.reject(NONMATCH.replace(' @State selectedCategory: number = 0',
                    ' @State selectedCategory: number = 0\n @State selectedCategory: number = 1'))


if __name__ == '__main__':
    unittest.main()
