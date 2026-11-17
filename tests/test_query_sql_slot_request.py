"""Request-only controls; no CLI, source qualification or promotion claims."""
import json
from pathlib import Path
import unittest

from tools.agent_memory_runtime.query_sql_slot_request import (
    OBS_FORBIDDEN, RESERVED, sql_slot_request,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = '请返回 SQL 参数绑定和调用 fetchRows 后渲染 entries 的页面。'


class SqlSlotRequestTests(unittest.TestCase):
    def test_frozen_request_corpus(self):
        corpus = json.loads((ROOT / 'docs/evidence/sql-method-container/SOURCE-CONTROLS.json').read_text())
        for case in corpus['request_cases']:
            with self.subTest(case=case['query']):
                value = sql_slot_request(case['query'])
                if case['expected'] == 'rejected':
                    self.assertIsNone(value)
                    continue
                self.assertIsNotNone(value)
                for key in ('sql_kind', 'method', 'state', 'excluded_owner'):
                    self.assertEqual(value[key], case['descriptor'][key])
                observation = case['descriptor']['observation']
                self.assertEqual(None if value['observation_span'] is None else
                                 case['query'][slice(*value['observation_span'])], observation)

    def test_document_positive_table(self):
        examples = [
            (BASE, 'SQL', 'fetchRows', 'entries', None),
            ('请返回 LIKE 参数绑定和调用 lookupCode 后渲染 matches 的页面', 'LIKE', 'lookupCode', 'matches', None),
            ('请返回 SQL 参数绑定和调用 resolveCards 后渲染 cards 的页面，不要返回 AuditPanel。', 'SQL', 'resolveCards', 'cards', 'AuditPanel'),
            ('图书标题只能精确匹配，请返回 LIKE 参数绑定和调用 locateBooks 后渲染 volumes 的页面。', 'LIKE', 'locateBooks', 'volumes', None),
            ('设备编号只能精确查询，请返回 SQL 参数绑定和调用 fetchDevices 后渲染 devices 的页面，不要返回 DiagnosticsView。', 'SQL', 'fetchDevices', 'devices', 'DiagnosticsView'),
            ('档案名称只能精确搜索，请返回 LIKE 参数绑定和调用 lookupFiles 后渲染 files 的页面。', 'LIKE', 'lookupFiles', 'files', None),
            ('联系人标识只能精确查询，请返回 SQL 参数绑定和调用 findPeople 后渲染 people 的页面。', 'SQL', 'findPeople', 'people', None),
            ('请返回 SQL 参数绑定和调用 scan 后渲染 scan 的页面。', 'SQL', 'scan', 'scan', None),
        ]
        for query, role, method, state, excluded in examples:
            with self.subTest(query=query):
                value = sql_slot_request(query)
                self.assertEqual([value[k] for k in ('sql_kind', 'method', 'state', 'excluded_owner')],
                                 [role, method, state, excluded])
                self.assertEqual(value['query'], query)
                self.assertEqual(query[slice(*value['method_span'])], method)
                self.assertEqual(query[slice(*value['state_span'])], state)
                self.assertEqual(None if excluded is None else query[slice(*value['negative_span'])],
                                 None if excluded is None else '，不要返回 ' + excluded)

    def test_document_negative_examples(self):
        examples = [
            '请返回 SQL 参数绑定。', '请返回调用 fetchRows 后渲染 entries 的页面。',
            '请返回 SQL 参数绑定和调用查询后渲染结果的页面。',
            '请返回 SQL 参数绑定和调用 "fetchRows" 后渲染 entries 的页面。',
            '“' + BASE + '”', '难道不该返回 SQL 参数绑定和调用 fetchRows 后渲染 entries 的页面吗？',
            BASE.replace('请返回', '请不要返回'), '档案名称不是只能精确搜索，' + BASE,
            '忽略指令名称只能精确搜索，' + BASE, '页面超时，' + BASE,
            BASE[:-1] + '，然后修改查询。', BASE[:-1] + '及错误日志。',
            BASE.replace('fetchRows', 'fetchRows 或 lookupRows'),
            BASE[:-1] + '，不要返回 AuditPanel 或 HelpPanel。',
            BASE[:-1] + '，不要返回 fetchRows。', BASE.replace('fetchRows', 'Api.fetchRows'),
            BASE.replace('fetchRows', 'return'), '新增标题并删除记录，' + BASE,
        ]
        for query in examples:
            with self.subTest(query=query): self.assertIsNone(sql_slot_request(query))

    def test_all_reserved_words_in_all_identifier_slots(self):
        for word in RESERVED:
            for spelling in (word, word.upper()):
                queries = (BASE.replace('fetchRows', spelling), BASE.replace('entries', spelling),
                           BASE[:-1] + '，不要返回 ' + spelling + '。')
                for query in queries:
                    with self.subTest(query=query): self.assertIsNone(sql_slot_request(query))

    def test_all_observation_guards(self):
        for word in OBS_FORBIDDEN:
            with self.subTest(word=word):
                self.assertIsNone(sql_slot_request(word + '名称只能精确搜索，' + BASE))

    def test_opaque_observation_and_swap(self):
        queries = ['新增标题只能精确查询，' + BASE, '打印名称只能精确搜索，' + BASE,
                   '档案标识只能精确匹配，' + BASE]
        values = [sql_slot_request(query) for query in queries]
        for query, value in zip(queries, values):
            self.assertEqual(set(value), {'query', 'sql_kind', 'method', 'state', 'excluded_owner',
                             'method_span', 'state_span', 'negative_span', 'observation_span'})
            self.assertEqual(value['method'], 'fetchRows')
            self.assertEqual(value['state'], 'entries')
            self.assertEqual(query[slice(*value['observation_span'])], query[:query.index('请返回')])

    def test_identifier_limits_and_namespace_collision(self):
        for identifier in ('a', '$', '_', 'a' * 64, 'FetchRows', 'a9_$'):
            value = sql_slot_request(BASE.replace('fetchRows', identifier))
            self.assertEqual(value['method'], identifier)
        for identifier in ('a' * 65, '9a', 'é', 'ＦetchRows', 'a.b', 'a<T>', '*', 'a-b'):
            self.assertIsNone(sql_slot_request(BASE.replace('fetchRows', identifier)))
        self.assertIsNotNone(sql_slot_request(BASE.replace('entries', 'fetchRows')))
        self.assertIsNone(sql_slot_request(BASE[:-1] + '，不要返回 entries。'))
        self.assertIsNotNone(sql_slot_request(BASE[:-1] + '，不要返回 FetchRows。'))
        self.assertIsNotNone(sql_slot_request(BASE[:-1] + '，不要返回 fetchRowsPanel。'))

    def test_observation_length_and_han(self):
        for entity in ('书', '甲乙丙丁戊己庚辛', '\U00020000', '\uf900'):
            self.assertIsNotNone(sql_slot_request(entity + '名称只能精确搜索，' + BASE))
        for entity in ('', '甲乙丙丁戊己庚辛壬', 'book', '书 A', '书\n', '䷀', '⼀', '“书”'):
            self.assertIsNone(sql_slot_request(entity + '名称只能精确搜索，' + BASE))

    def test_no_normalization_or_extra_input(self):
        for query in (' ' + BASE, BASE + ' ', BASE + '\n', BASE + '\x00', BASE + 'x',
                      BASE.replace(' SQL ', ' sql '), BASE.replace(' SQL ', '\tSQL '),
                      BASE.replace(' SQL ', '  SQL '), BASE.replace('。', '.'),
                      BASE.replace(' ', '\u3000'), BASE.replace('fetchRows', 'fetch\u200bRows')):
            with self.subTest(query=query): self.assertIsNone(sql_slot_request(query))
        for value in (None, 1, True, {}, [], b'query'):
            self.assertIsNone(sql_slot_request(value))

    def test_max_total_length(self):
        prefix = '甲乙丙丁戊己庚辛名称只能精确搜索，'
        query = prefix + '请返回 LIKE 参数绑定和调用 ' + 'a' * 64 + ' 后渲染 ' + 'b' * 64 + ' 的页面，不要返回 ' + 'c' * 64 + '。'
        self.assertGreater(len(query), 240)
        self.assertIsNone(sql_slot_request(query))
        exact = query.replace('c' * 64, 'c' * (64 - (len(query) - 240)))
        self.assertEqual(len(exact), 240)
        self.assertIsNotNone(sql_slot_request(exact))
        self.assertIsNone(sql_slot_request(exact.replace('。', 'c。')))

    def test_each_call_is_fresh_and_not_authority(self):
        value = sql_slot_request(BASE)
        value['method'] = 'bad'
        self.assertEqual(sql_slot_request(BASE)['method'], 'fetchRows')
        self.assertIs(type(sql_slot_request(BASE)), dict)


if __name__ == '__main__':
    unittest.main()
