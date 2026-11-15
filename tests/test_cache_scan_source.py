# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import re
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_cache_scan_source import cache_scan_request, parse_cache_scan_source

P = json.loads((Path(__file__).parents[1] / 'docs/evidence/cache-eviction-current/protocol.json').read_text())
SOURCE = P['sources']['ExpiryStore.ts']
QUERY = P['queries'][0]['query']


class CacheScanSourceTests(unittest.TestCase):
    def test_original_positive_and_exact_ranges(self):
        self.assertEqual(parse_cache_scan_source(SOURCE), dict(owner='ExpiryStore', class_start=1,
            class_end=15, method='trim', start_line=3, end_line=14))
        self.assertTrue(cache_scan_request(QUERY))

    def test_independent_names_comments_semicolons_and_newlines(self):
        renamed = SOURCE
        for old, new in [('ExpiryStore', 'Bucket'), ('records', 'items'), ('Entry', 'Cell'),
                         ('trim', 'prune'), ('limit', 'capacity'), ('chosen', 'candidate'),
                         ('earliest', 'minimum'), ('name', 'index'), ('record', 'element'),
                         ('updatedAt', 'metric')]:
            renamed = re.sub(r'\b' + old + r'\b', new, renamed)
        for source in [renamed, SOURCE.replace('\n', '\r\n'), SOURCE.replace('\n', '\r'),
                       SOURCE.replace('this.records', 'this /* note */ . records'),
                       SOURCE.replace('return }', 'return; }').replace('= undefined\n', '= undefined;\n'),
                       SOURCE.replace('export ', ''), SOURCE + '// ordinary trailing comment']:
            with self.subTest(source=source):
                self.assertIsNotNone(parse_cache_scan_source(source))

    def test_wrong_chains_and_added_executable_syntax_unknown(self):
        replacements = [
            ('record.updatedAt < earliest', 'record.updatedAt > earliest'),
            ('earliest = record.updatedAt', 'chosen = record.updatedAt'),
            ('earliest = record.updatedAt', 'earliest = record.other'),
            ('chosen = name', 'chosen = limit'),
            ('of this.records', 'of this.other'),
            ('this.records.delete(chosen)', 'this.other.delete(chosen)'),
            ('this.records.delete(chosen)', 'this.records.delete(name)'),
            ('    if (chosen !== undefined)', '    chosen = limit\n    if (chosen !== undefined)'),
            ('if (chosen !== undefined) { this.records.delete(chosen) }', 'this.records.delete(chosen)'),
            ('    let chosen', '    run()\n    let chosen'),
            ('trim(limit: number): void {', 'trim(limit: number): void { queueMicrotask(() => {'),
            ('  private records', '  other(): void {}\n  private records'),
            ('export class', 'import { Number } from "x"; export class'),
            ('= new Map()', '= new Other()'),
            ('chosen = name', 'chosen = name()'),
            ('let earliest =', 'let earliest: number ='),
        ]
        for old, new in replacements:
            with self.subTest(new=new):
                self.assertIsNone(parse_cache_scan_source(SOURCE.replace(old, new)))
        for source in [SOURCE + '\nrun()', SOURCE + '\nclass Extra {}',
                       '/*' + SOURCE + '*/', repr(SOURCE), '`' + SOURCE + '`', SOURCE[:-3]]:
            with self.subTest(source=source):
                self.assertIsNone(parse_cache_scan_source(source))

    def test_fifo_split_text_nested_unknown(self):
        for name, source in P['sources'].items():
            if name != 'ExpiryStore.ts':
                with self.subTest(name=name):
                    self.assertIsNone(parse_cache_scan_source(source))

    def test_lexical_asi_and_binding_controls(self):
        self.assertIsNotNone(parse_cache_scan_source(SOURCE.replace('chosen = name\n', 'chosen = name ')))
        for source in [SOURCE.replace('= undefined\n', '= undefined '),
                       SOURCE.replace('return }', 'return value }'),
                       SOURCE.replace('records', 'Map'), SOURCE.replace('Entry', 'ExpiryStore'),
                       SOURCE.replace('trim', 'records'), SOURCE.replace('chosen', 'limit'),
                       SOURCE.replace('chosen', 'undefined'), SOURCE.replace('earliest', 'arguments'),
                       SOURCE.replace('record', 'eval'), SOURCE.replace('name', 'yield'),
                       SOURCE.replace('updatedAt', '`updatedAt`'), SOURCE + '/* unclosed',
                       SOURCE.replace('private records', 'private reco/* x */rds'),
                       SOURCE.replace('<=', '< /* x */ ='), SOURCE.replace('!==', '! ==')]:
            with self.subTest(source=source):
                self.assertIsNone(parse_cache_scan_source(source))
        for separator in '\v\f\x1c\x1d\x1e\x85\u2028\u2029':
            self.assertIsNone(parse_cache_scan_source(SOURCE + '//' + separator))
        for source in [None, '', SOURCE + '\ud800', SOURCE + ' ' * (2 * 1024 * 1024)]:
            self.assertIsNone(parse_cache_scan_source(source))

    def test_request_complete_positive_only(self):
        for query in [QUERY, QUERY[:-1], QUERY.lower(), QUERY.upper(),
                      QUERY.replace('Locate', 'Find'), QUERY.replace('Locate', 'Return')]:
            self.assertTrue(cache_scan_request(query))
        for query in [P['queries'][1]['query'], P['queries'][2]['query'], P['queries'][3]['query'],
                      'Previously: ' + QUERY, 'Generate code: ' + QUERY, QUERY + ' and show the text',
                      QUERY + '\n', ' ' + QUERY, QUERY + ' ', QUERY.replace(' ', '\t', 1),
                      QUERY.replace('ownership', 'ownership or literal text'), QUERY.replace('scan ', ''),
                      '"' + QUERY + '"', QUERY.replace('Locate', 'Loſate'), QUERY * 3, None]:
            with self.subTest(query=query):
                self.assertFalse(cache_scan_request(query))


if __name__ == '__main__':
    unittest.main()
