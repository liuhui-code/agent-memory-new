# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Pure Development controls: no CLI, database, or original32 acceptance."""
import copy
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.context_budget import trim_excerpt

ROOT = Path(__file__).resolve().parents[1]

class ExcerptTrimFocusTests(unittest.TestCase):
    def trim(self, lines, focus, start=7):
        content = '\n'.join(lines)
        item = dict(content=content, start_line=start,
                    end_line=start + len(lines) - 1, focus_line=focus,
                    source='current_worktree', selection_reason='event_owner',
                    symbol='callback', truncated=False)
        before = copy.deepcopy(item)
        self.assertTrue(trim_excerpt(item))
        self.assertLess(len(item['content']), len(content))
        self.assertLessEqual(len(item['content']), max(64, len(content) - 240))
        self.assertEqual(item['end_line'] - item['start_line'] + 1,
                         len(item['content'].split('\n')))
        for key in ('focus_line', 'source', 'selection_reason', 'symbol'):
            self.assertEqual(before[key], item[key])
        self.assertTrue(item['truncated'])
        return item

    def test_existing_natural_source_focus_is_not_evicted_by_long_left(self):
        controls = json.loads((ROOT/'docs/evidence/disclosure-lexical/controls.json').read_text())
        lines = controls['sources']['Actual.ets'].splitlines()[6:8]
        self.assertEqual([70, 21], list(map(len, lines)))
        item = self.trim(lines, 8)
        self.assertEqual(lines[1], item['content'])
        self.assertEqual((8, 8), (item['start_line'], item['end_line']))

    def test_fitting_contiguous_context_keeps_focus(self):
        lines = ['a'*20, 'b'*20, 'c'*20, 'd'*20]
        item = self.trim(lines, 8)
        self.assertEqual('\n'.join(lines[:3]), item['content'])
        self.assertEqual((7, 9), (item['start_line'], item['end_line']))

    def test_blocked_left_does_not_block_fitting_right_or_skip_lines(self):
        lines = ['a'*70, 'focus'*4, 'r'*10, 'x'*70, 'y']
        item = self.trim(lines, 8)
        self.assertEqual('\n'.join(lines[1:3]), item['content'])
        self.assertEqual((8, 9), (item['start_line'], item['end_line']))

    def test_long_focus_is_one_truthful_partial_source_line(self):
        item = self.trim(['left', 'f'*100, 'right'], 8)
        self.assertEqual('f'*64, item['content'])
        self.assertEqual((8, 8), (item['start_line'], item['end_line']))

    def test_missing_invalid_or_outside_focus_keeps_legacy_index_fallback(self):
        for focus, expected_line, expected in [(None,7,'a'*64),('8',7,'a'*64),
                                                (1,7,'a'*64),(99,8,'b'*64)]:
            with self.subTest(focus=focus):
                item = self.trim(['a'*80, 'b'*80], focus)
                self.assertEqual(expected, item['content'])
                self.assertEqual((expected_line,expected_line),
                                 (item['start_line'],item['end_line']))
        ordinary = self.trim(['short', 'x'*100], None)
        self.assertEqual('short\n'+'x'*58, ordinary['content'])
        self.assertEqual((7,8),(ordinary['start_line'],ordinary['end_line']))
        for following, expected_end, expected in [
                ('b'*80, 7, 'a'*63), ('', 8, 'a'*63+'\n')]:
            with self.subTest(separator_following=following):
                edge = self.trim(['a'*63, following, 'c'*80], None)
                self.assertEqual(expected, edge['content'])
                self.assertEqual(expected_end, edge['end_line'])
        short = dict(content='short',start_line=7,end_line=7,focus_line=None)
        before = copy.deepcopy(short)
        self.assertFalse(trim_excerpt(short))
        self.assertEqual(before,short)

    def test_unicode_separator_is_not_an_extra_source_line(self):
        item = self.trim(['a'*40+'\u2028'+'b'*40], 7)
        self.assertEqual('a'*40+'\u2028'+'b'*23,item['content'])
        self.assertEqual((7,7),(item['start_line'],item['end_line']))
