"""Exact source-window adjective role and original-query protection, no saved outputs."""
from copy import copy, deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.command_table_test_support import prepare
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.log_event_identity import event_match
from tools.agent_memory_runtime.query_record_loop_selection import protected_record_loop
from tools.agent_memory_runtime.query_ui_divider_request import divider_request, divider_identity_query
from tools.agent_memory_runtime.query_ui_divider_guard import protected_divider
from tools.agent_memory_runtime.query_ui_divider_selection import (
    DividerContext, bind_divider_context, divider_receipt, compact_divider, enrich_divider,
)
from tools.agent_memory_runtime.storage import connect

P = json.loads((Path(__file__).parent / 'fixtures/ui_divider_context.json').read_text())
Q = next(c['query'] for c in P['cases'] if c['id'] == 'current-qualified')
OLD = 'Locate the ArkTS glyph divider stroke width implementation.'


class DividerContextRequestGrammar(unittest.TestCase):
    def test_complete_finite_forms(self):
        for thickness in ('the wrong', 'an incorrect'):
            for verb in ('Return', 'Locate'):
                for qualifier in ('', 'ArkTS '):
                    for punctuation in ('', '.'):
                        query = f'The glyph list separator has {thickness} thickness. {verb} the {qualifier}behavior owner and current source window{punctuation}'
                        self.assertEqual(divider_request(query), 'glyph')
        self.assertEqual(divider_request(Q.replace('glyph', 'inventory')), 'inventory')

    def test_only_exact_adjective_span_is_projected(self):
        projected = divider_identity_query(Q)
        lo = Q.index('current source window')
        self.assertEqual(len(projected), len(Q))
        self.assertEqual(projected[:lo], Q[:lo])
        self.assertEqual(projected[lo:lo+7], ' '*7)
        self.assertEqual(projected[lo+7:], Q[lo+7:])
        query = Q.replace('glyph', 'current')
        self.assertEqual(divider_request(query), 'current')
        projected = divider_identity_query(query)
        self.assertTrue(projected.startswith('The current list separator'))
        self.assertEqual(projected.count('current'), 1)

    def test_unsupported_and_old_queries_remain_exact(self):
        negatives = [Q+' Include ClockState.current.', 'Do not '+Q, Q+' Also return logs.',
                     Q.replace('glyph', 'GlyphList'), Q.replace('glyph', 'glyph and inventory'),
                     Q.replace('glyph', 'not'), Q.replace('glyph', 'SDK'),
                     Q.replace('current', '"current"'), Q.replace('current', '`current`'),
                     '"'+Q+'"', Q.replace('behavior owner', 'SDK implementation'),
                     Q.replace('current source window', 'current source window and another owner'),
                     Q.lower(), Q.replace('The ', 'The  ', 1), Q+'\n', Q+'x'*240,
                     '请返回列表分隔线的行为源码和当前源码窗口。',
                     'Find ClockState.current source.']
        for query in negatives:
            with self.subTest(query=query):
                self.assertIsNone(divider_request(query))
                self.assertEqual(divider_identity_query(query), query)
        self.assertEqual(divider_request(OLD), 'glyph')
        self.assertEqual(divider_identity_query(OLD), OLD)
        for value in (None, 1, [], {}):
            self.assertIsNone(divider_request(value))
            self.assertEqual(divider_identity_query(value), value)


class DividerContextProtection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.samples = {}
        for cohort, sources in P['sources'].items():
            folder = Path(cls.tmp.name)/cohort
            folder.mkdir()
            project = prepare(folder, sources=sources)
            query = next(c['query'] for c in P['cases'] if c['cohort'] == cohort)
            captures = []
            def capture(_project, _query, baseline, pool):
                captures.append((deepcopy(baseline), deepcopy(pool)))
                return baseline
            with patch('tools.agent_memory_runtime.query_ui_divider_selection.bind_divider_context', side_effect=capture):
                raw = build_context_facade(project).execute(query)
                compact = compact_context(raw)
            assert len(captures) == 1
            pre, pool = captures[0]
            cls.samples[cohort] = (project, query, pre, deepcopy(raw), compact, pool)

    def sample(self, cohort='current_collision'):
        project, query, pre, raw, compact, pool = self.samples[cohort]
        return project, query, deepcopy(pre), deepcopy(raw), deepcopy(compact), deepcopy(pool)

    def test_real_current_state_is_in_pool_but_adjective_is_not_name(self):
        project, query, pre, raw, compact, pool = self.sample()
        with connect(project) as db:
            states = [dict(row) for row in db.execute("SELECT * FROM code_symbols WHERE symbol='current'")]
        self.assertTrue(states)
        self.assertTrue(any(row.get('symbol') == 'current' and row.get('kind') == 'symbol'
                            and row.get('id') in {s['id'] for s in states} for row in pool))
        self.assertTrue(protected_record_loop(pre, query, pool, pending=True))
        self.assertFalse(protected_record_loop(pre, divider_identity_query(query), pool, pending=True))
        self.assertFalse(protected_divider(pre, query, pool, pending=True))
        self.assertFalse(protected_divider(raw, query, pool))

    def test_actual_positive_source_set_preserves_original_raw(self):
        for cohort, owners in [('current_collision', {'GlyphList.ets'}),
                               ('current_collision_two', {'GlyphList.ets', 'GlyphRows.ets'})]:
            with self.subTest(cohort=cohort):
                project, query, pre, raw, compact, pool = self.sample(cohort)
                result = bind_divider_context(project, query, raw, pool)
                self.assertIsInstance(result, DividerContext)
                self.assertEqual(dict(result), raw)
                self.assertEqual(result['query'], query)
                after = compact_divider(result, compact)
                self.assertEqual({a['file_path'] for a in after['query_handoff']['code_anchors']}, owners)
                self.assertEqual(restore_whitelist(after, compact), compact)
                for anchor in after['query_handoff']['code_anchors']:
                    excerpt = anchor['source_excerpts'][0]
                    self.assertFalse(excerpt['truncated'])
                    source = P['sources'][cohort][anchor['file_path']]
                    self.assertEqual(excerpt['content'], '\n'.join(source.splitlines()[excerpt['start_line']-1:excerpt['end_line']]))
                self.assertLessEqual(after['output_budget']['estimated_tokens'], 1500)
                self.assertIsNone(after['query_handoff']['callable_evidence']['primary'])

    def test_domain_current_and_other_window_name_remain_protected(self):
        for cohort, symbol in [('domain_current', 'current'), ('other_name_collision', 'window')]:
            project, query, pre, raw, compact, pool = self.sample(cohort)
            self.assertTrue(any(row.get('symbol') == symbol for row in pool))
            self.assertTrue(protected_record_loop(pre, divider_identity_query(query), pool, pending=True))
            self.assertTrue(protected_divider(pre, query, pool, pending=True))
            self.assertIs(bind_divider_context(project, query, raw, pool), raw)

    def test_real_event_restored_before_facade_path_guard(self):
        project, query, pre, raw, compact, pool = self.sample('domain_event')
        logs = pre['query_handoff']['log_anchors']
        self.assertTrue(logs)
        self.assertTrue(any(log['file_path'] == 'GlyphNotes.ts' for log in logs))
        self.assertEqual([event_match(log, query)['priority'] for log in logs], [2])
        projected = divider_identity_query(query)
        self.assertEqual([event_match(log, projected)['priority'] for log in logs], [0])
        self.assertFalse(protected_record_loop(pre, projected, pool, pending=True))
        self.assertTrue(protected_divider(pre, query, pool, pending=True))
        self.assertIs(bind_divider_context(project, query, pre, pool), pre)
        self.assertTrue(raw['query_handoff']['path_context']['activated'])
        self.assertTrue(protected_divider(raw, query, pool))
        self.assertIs(bind_divider_context(project, query, raw, pool), raw)

    def test_full_query_used_for_both_log_event_and_named_owner(self):
        _, query, pre, _, _, pool = self.sample('domain_event')
        with patch('tools.agent_memory_runtime.query_ui_divider_guard.protected_record_loop', return_value=False), \
             patch('tools.agent_memory_runtime.query_ui_divider_guard.event_match', return_value={'priority': 0}) as events, \
             patch('tools.agent_memory_runtime.query_ui_divider_guard.independently_named_log_owner', return_value=True) as names:
            self.assertTrue(protected_divider(pre, query, pool, pending=True))
            events.assert_called_once_with(pre['query_handoff']['log_anchors'][0], query)
            names.assert_called_once_with(pre['query_handoff']['log_anchors'][0], query)

    def test_initial_pool_code_and_log_flags_are_never_projected(self):
        for location in ('pool', 'code', 'log'):
            for flag in ('identity_match', 'log_identity_match', 'graph_neighbor', 'graph_relation'):
                project, query, pre, raw, _, pool = self.sample()
                if location == 'pool':
                    pool[0][flag] = True
                elif location == 'code':
                    pre['query_handoff']['code_anchors'][0][flag] = True
                else:
                    pre['query_handoff']['log_anchors'] = [{flag: True}]
                self.assertTrue(protected_divider(pre, query, pool, pending=True), (location, flag))

    def test_path_obligations_unknown_shapes_and_nonstring_requests(self):
        for key, value in [('activated', True), ('seeds', [{}]), ('path_candidates', [{}]),
                           ('wrapped_log_evidence', True), ('activated', 'false')]:
            _, query, _, raw, _, pool = self.sample()
            raw['query_handoff']['path_context'][key] = value
            self.assertTrue(protected_divider(raw, query, pool), key)
        for value in (None, [], 'handoff', 1):
            _, query, _, raw, _, pool = self.sample()
            raw['query_handoff'] = value
            self.assertTrue(protected_divider(raw, query, pool))
        for value in (None, 'pool', [None], [1]):
            _, query, pre, _, _, _ = self.sample()
            self.assertTrue(protected_divider(pre, query, value, pending=True))
        for value in (None, [], {}, 1):
            _, _, pre, _, _, pool = self.sample()
            self.assertTrue(protected_divider(pre, value, pool, pending=True))

    def test_unknown_source_is_not_authorized_by_new_request(self):
        project, query, pre, raw, _, pool = self.sample('current_collision_unknown')
        self.assertIs(bind_divider_context(project, query, raw, pool), raw)

    def test_receipt_binding_keeps_full_original_query_not_projection(self):
        project, query, _, raw, compact, pool = self.sample()
        result = bind_divider_context(project, query, raw, pool)
        self.assertIsInstance(result, DividerContext)
        self.assertIsNotNone(divider_receipt(result))
        self.assertEqual(result['query'], query)
        for cloned in (copy(result), deepcopy(result), json.loads(json.dumps(result))):
            self.assertIsNone(divider_receipt(cloned))
        result['query'] = divider_identity_query(query)
        self.assertIsNone(divider_receipt(result))
        self.assertIs(compact_divider(result, compact), compact)
        result = bind_divider_context(project, query, raw, pool)
        changed = deepcopy(raw['query_handoff']['path_context']); changed['activated'] = True
        self.assertNotIsInstance(enrich_divider(result, query, changed, raw['source_freshness']), DividerContext)


if __name__ == '__main__': unittest.main()
