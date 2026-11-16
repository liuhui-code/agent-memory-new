"""Self-contained finite grammar and exact negative-name projection tests."""
from dataclasses import FrozenInstanceError, replace
import unittest
from tools.agent_memory_runtime.query_ui_divider_multilingual_request import (
    MultilingualDividerRequest, parse_multilingual_divider_request, project_negative_names,
)


def request(domain='字形', names=(), wrong='错误', stop='。'):
    return domain + '列表分隔线粗细' + wrong + '，请定位 divider 的源码' + (
        '，不要返回 ' + ' 或 '.join(names) if names else '') + stop


class MultilingualDividerRequestTests(unittest.TestCase):
    def test_all_finite_combinations(self):
        for domain, expected in [('字形', ('glyph',)), ('账户', ('account',)),
                                 ('库存', ('inventory', 'stock'))]:
            for wrong in ('错误', '不正确'):
                for stop in ('', '。'):
                    for names in ((), ('GlyphModel',), ('GlyphModel', 'GlyphRows'),
                                  ('GlyphModel', 'GlyphRows', '$Label_2')):
                        query = request(domain, names, wrong, stop)
                        with self.subTest(query=query):
                            parsed = parse_multilingual_divider_request(query)
                            self.assertEqual(parsed.qualifiers, expected)
                            self.assertEqual(parsed.excluded_names, names)
                            self.assertIs(type(parsed), MultilingualDividerRequest)
                            self.assertEqual(tuple(query[a:b] for a, b in parsed.negative_spans), names)

    def test_projection_changes_only_exact_identifier_spans(self):
        query = request('库存', ('InventoryRecord', 'InventoryItem', '$Node_7'))
        parsed = parse_multilingual_divider_request(query)
        projected = project_negative_names(query, parsed)
        self.assertEqual(len(projected), len(query))
        covered = {i for lo, hi in parsed.negative_spans for i in range(lo, hi)}
        for i, char in enumerate(query):
            self.assertEqual(projected[i], ' ' if i in covered else char)
        self.assertIn('库存列表', projected)
        self.assertIn('不要返回 ', projected)
        self.assertEqual(projected.count(' 或 '), 2)
        self.assertEqual(parsed.excluded_names, ('InventoryRecord', 'InventoryItem', '$Node_7'))

    def test_absent_negative_is_noop_projection(self):
        query = request()
        parsed = parse_multilingual_divider_request(query)
        self.assertEqual(parsed.excluded_names, ())
        self.assertEqual(parsed.negative_spans, ())
        self.assertEqual(project_negative_names(query, parsed), query)

    def test_240_character_boundary(self):
        prefix = request(names=('X',))
        exact = request(names=('X' * (240 - len(prefix) + 1),))
        self.assertEqual(len(exact), 240)
        self.assertIsNotNone(parse_multilingual_divider_request(exact))
        self.assertIsNone(parse_multilingual_divider_request(exact.replace('X', 'XX', 1)))

    def test_unknown_domain_and_no_language_normalization(self):
        for domain in ('订单', '图形', '帐户', 'Inventory', 'inventory', 'glyph', '字形或账户', '字形（glyph）'):
            self.assertIsNone(parse_multilingual_divider_request(request(domain)))
        for query in [request().replace('divider', 'Divider'), request().replace('divider', 'DIVIDER'),
                      request().replace('字形', '字 形'), request().replace('，', ','),
                      request().replace('。', '.'), request().replace('源码', 'SDK实现')]:
            self.assertIsNone(parse_multilingual_divider_request(query))

    def test_invalid_names_no_partial_match(self):
        for names in [('GlyphRows', 'GlyphRows'), ('A', 'B', 'C', 'D'), ('class',), ('RETURN',),
                      ('sdk',), ('build',), ('GlyphRows.build',), ('src/GlyphRows.ets',),
                      ('Glyph-Rows',), ('"GlyphRows"',), ('`GlyphRows`',), ('字形组件',),
                      ('ＧlyphRows',), ('GlyphRows\u200b',), ('7GlyphRows',), ('GlyphRows log',)]:
            self.assertIsNone(parse_multilingual_divider_request(request(names=names)), names)
        # JavaScript declaration identity remains case-sensitive, not normalized.
        self.assertEqual(parse_multilingual_divider_request(request(names=('GlyphRows', 'glyphRows')))
                         .excluded_names, ('GlyphRows', 'glyphRows'))

    def test_no_extra_text_quotes_or_tasks(self):
        query = request(names=('GlyphRows',))
        for invalid in [query+'\n', '\n'+query, ' '+query, query+' ', '"'+query+'"', '`'+query+'`',
                        '不要'+query, query+'也返回日志。', query+'定位 GlyphList。',
                        query.replace('不要返回', '请返回'), query.replace(' 或 ', '或'),
                        query.replace('返回 ', '返回  '), query.replace(' divider ', '  divider '),
                        query.replace('错误', '不错误'), query.replace('源码', '根本原因'),
                        query.replace('GlyphRows', 'GlyphRows 和 Other')]:
            # The single-name query has no separator to replace.
            if invalid == query:
                continue
            self.assertIsNone(parse_multilingual_divider_request(invalid), invalid)
        self.assertIsNone(parse_multilingual_divider_request(request(names=('A', 'B')).replace(' 或 ', '或')))

    def test_english_routes_are_not_claimed(self):
        for query in ['Locate the ArkTS glyph divider stroke width implementation.',
                      'Find the glyph divider stroke width implementation.',
                      'The glyph list separator has the wrong thickness. Return the ArkTS behavior owner and current source window.']:
            self.assertIsNone(parse_multilingual_divider_request(query))

    def test_descriptor_is_frozen_and_revalidated(self):
        query = request(names=('GlyphRows',))
        parsed = parse_multilingual_divider_request(query)
        with self.assertRaises(FrozenInstanceError):
            parsed.excluded_names = ()
        for forged in [None, {}, tuple(parsed.negative_spans),
                       replace(parsed, qualifiers=('inventory',)),
                       replace(parsed, excluded_names=('GlyphList',)),
                       replace(parsed, negative_spans=((0, len(query)),)),
                       replace(parsed, negative_spans=()),
                       replace(parsed, negative_spans=parsed.negative_spans*2)]:
            self.assertEqual(project_negative_names(query, forged), query)
        other = request('账户', ('GlyphRows',))
        self.assertEqual(project_negative_names(other, parsed), other)
        invalid = query+' extra'
        self.assertEqual(project_negative_names(invalid, parsed), invalid)

    def test_nonstring_values_fail_closed(self):
        parsed = parse_multilingual_divider_request(request(names=('GlyphRows',)))
        for value in (None, 12, [], {}, b'query'):
            self.assertIsNone(parse_multilingual_divider_request(value))
            self.assertEqual(project_negative_names(value, parsed), value)


if __name__ == '__main__':
    unittest.main()
