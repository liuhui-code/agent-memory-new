# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import random
import unittest
from unittest.mock import patch

from tools.agent_memory_runtime.ecma_callable_headers import closing_parenthesis, method_header
from tools.agent_memory_runtime.source_call_scanner import code_mask


def masked_parenthesis_reference(value: str, opening: int) -> int | None:
    mask = code_mask(value)
    depth = 0
    for index in range(opening, len(mask)):
        if mask[index] == '(':
            depth += 1
        elif mask[index] == ')':
            depth -= 1
            if depth == 0:
                return index
    return None


class CallableScanCostTests(unittest.TestCase):
    def test_closed_parameters_do_not_mask_the_unrelated_tail(self):
        source = "method(value)" + " unrelated body text" * 1000
        with patch('tools.agent_memory_runtime.ecma_callable_headers.code_mask', wraps=code_mask) as mask:
            self.assertEqual(closing_parenthesis(source, 6), 12)
        self.assertEqual(mask.call_count, 0)

    def test_rejected_candidate_without_semicolon_does_not_remask_each_prefix(self):
        lines = ['dispatch(value)'] + ['  unrelated(value)'] * 11
        with patch('tools.agent_memory_runtime.ecma_callable_headers.code_mask', wraps=code_mask) as mask:
            self.assertIsNone(method_header(lines, 0))
        self.assertEqual(mask.call_count, 0)

    def test_lexical_result_matches_mask_reference(self):
        tokens = ['(', ')', 'text', '\n', '\r\n', "'quoted )'", '"quoted ("',
                  '`template ) ${nested(}`', '/* ( ) */', '// ) comment\n',
                  "'escape \\' )'", '/* unfinished', "'unfinished", '\\', ' ', ';']
        randomizer = random.Random(40281)
        for _ in range(1000):
            prefix = randomizer.choice(['method', '@Trace("(ignored)") method', '/* prefix */ method'])
            opening = len(prefix)
            value = prefix + '(' + ''.join(randomizer.choices(tokens, k=12)) + ') trailing()'
            self.assertEqual(closing_parenthesis(value, opening), masked_parenthesis_reference(value, opening), value)


if __name__ == '__main__':
    unittest.main()
