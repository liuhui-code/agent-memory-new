# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime import semantic_ecma_mechanisms as m


def block(symbol, start, end):
    return SimpleNamespace(start=start, end=end, entity=SimpleNamespace(
        key='control:' + symbol, file_path='src/Scope.ets', qualified_name='Scope.' + symbol))


TEMPLATE_LINES = [
    'export class Scope {', '  templated(): string {',
    "    const label = 'legacyPort.showValue()';",
    '    return `${this.sessionApi.readSessionStatus()}`;', '  }',
    '  plain(): void {', "    const label = 'decoyPort.showValue()';",
    '    realPort.loadValue();', '  }', '}',
]


class OperationSourceValidityTests(unittest.TestCase):
    def test_cross_line_comment_and_literal_do_not_emit_operations(self):
        lines = ['class Scope {', 'run() {', '/*', 'fakePort.readValue();', '*/',
                 'const label = "decoyPort.loadValue()";',
                 'realPort.loadValue("stringPort.callValue()");', '}', '}']
        values, gaps = m.extract_file_mechanisms(lines, [block('run', 1, 7)])
        operations = [x for x in values if x.kind == 'operation']
        self.assertEqual([('call:realport.loadvalue', 7)], [(x.detail, x.line) for x in operations])
        self.assertEqual([], gaps)

    def test_template_callable_is_legacy_but_neighbor_is_filtered(self):
        values, gaps = m.extract_file_mechanisms(TEMPLATE_LINES, [block('templated', 1, 4), block('plain', 5, 8)])
        template = [x for x in values if x.source_key == 'control:templated' and x.kind == 'operation']
        plain = [x for x in values if x.source_key == 'control:plain' and x.kind == 'operation']
        self.assertEqual([('call:legacyport.showvalue', 3), ('call:sessionapi.readsessionstatus', 4)],
                         [(x.detail, x.line) for x in template])
        self.assertTrue(all(x.terms == ['operation', 'call'] for x in template))
        self.assertEqual([('call:realport.loadvalue', 8)], [(x.detail, x.line) for x in plain])
        self.assertEqual(['operation_syntax_unverified_template'], [g['kind'] for g in gaps])
        self.assertEqual(('Scope.templated', '2', '5'), (gaps[0]['symbol'], gaps[0]['start_line'], gaps[0]['end_line']))

    def test_unbalanced_callable_retains_legacy_without_poisoning_neighbor(self):
        lines = ['class Scope {', 'broken() {', 'brokenPort.readValue(', '}',
                 'normal() {', "const label = 'decoyPort.readValue()';", 'realPort.loadValue();', '}', '}']
        values, gaps = m.extract_file_mechanisms(lines, [block('broken', 1, 3), block('normal', 4, 7)])
        self.assertEqual([('call:brokenport.readvalue', 3), ('call:realport.loadvalue', 7)],
                         [(x.detail, x.line) for x in values if x.kind == 'operation'])
        self.assertEqual(['operation_syntax_unverified_unbalanced_call'], [g['kind'] for g in gaps])

    def test_balancing_cannot_borrow_a_later_callable_closer(self):
        lines = ['class Scope {', 'broken() {', 'port.readValue(', '}', 'normal() {', ')', '}', '}']
        scan = m.scan_operation_source(lines)
        self.assertNotIn(3, scan.unbalanced_lines)
        values, gaps = m.extract_file_mechanisms(lines, [block('broken', 1, 3), block('normal', 4, 6)])
        self.assertEqual(['operation_syntax_unverified_unbalanced_call'], [g['kind'] for g in gaps])
        self.assertEqual([('call:port.readvalue', 3)], [(x.detail, x.line) for x in values if x.kind == 'operation'])

    def test_one_full_source_mask_is_reused_for_all_callables(self):
        original = m.code_mask
        with patch.object(m, 'code_mask', wraps=original) as mask:
            m.extract_file_mechanisms(TEMPLATE_LINES, [block('templated', 1, 4), block('plain', 5, 8)])
        self.assertEqual(1, mask.call_count)

    def test_standalone_operation_primitive_filters_literal_and_keeps_cap(self):
        self.assertEqual([], m.operation_mechanisms('key', 'const value = "api.callValue()";', 3))
        source = ' '.join(f'channel{i}.loadRecord();' for i in range(9))
        values = m.operation_mechanisms('key', source, 3)
        self.assertEqual([f'call:channel{i}.loadrecord' for i in range(8)], [x.detail for x in values])
        self.assertEqual([3] * 8, [x.line for x in values])

    def test_call_head_newline_remains_unsupported_but_arguments_may_span_lines(self):
        split = ['class Scope {', 'run() {', 'port.readValue', '()', '}', '}']
        values, _gaps = m.extract_file_mechanisms(split, [block('run', 1, 4)])
        self.assertEqual([], [x for x in values if x.kind == 'operation'])
        arguments = ['class Scope {', 'run() {', 'port.readValue(', 'value', ')', '}', '}']
        values, gaps = m.extract_file_mechanisms(arguments, [block('run', 1, 5)])
        self.assertEqual([('call:port.readvalue', 3)], [(x.detail, x.line) for x in values if x.kind == 'operation'])
        self.assertEqual([], gaps)
