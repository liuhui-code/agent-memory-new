from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tests.archive_create_write_test_support import cli
from tools.agent_memory_runtime.context_budget import synchronize_estimate
from tools.agent_memory_runtime.context_web_body_budget import prioritize_web_body
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens
from tools.agent_memory_runtime.storage import connect, resolve_project


FIXTURE = Path(__file__).resolve().parents[1] / 'docs/evidence/web-body-budget'
TARGET = 'src/view/OfflineManual.ets'
SUPPORT = 'src/tasks/ManualIndexJob.ets'


class WebBodyBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workspace = Path(cls.enterClassContext(tempfile.TemporaryDirectory()))
        root = workspace / 'source'
        shutil.copytree(FIXTURE / 'source', root)
        cls.project = resolve_project(str(root), str(workspace / 'memory'))
        cls.root = root
        cls.query = (FIXTURE / 'query.txt').read_text().strip()
        cli(cls.project, 'init')
        cli(cls.project, 'learn-path', '--path', '.', '--json')
        with connect(cls.project) as db:
            cls.target = dict(db.execute('SELECT * FROM code_symbols WHERE file_path=? AND symbol=?',
                                         (TARGET, 'build')).fetchone())
            cls.effect = dict(db.execute('SELECT * FROM code_log_effects WHERE file_path=?',
                                         (SUPPORT,)).fetchone())
        cls.log = {
            'effect_id': cls.effect['id'],
            'log_id': cls.effect['sink_log_id'],
            'file_path': SUPPORT,
            'function': cls.effect['function'],
            'line': cls.effect['line'],
            'wrapper_symbol': cls.effect['wrapper_symbol'],
            'evidence_class': cls.effect['evidence_class'],
            'message_template': cls.effect['message_template'],
        }

    def body(self, path, lo, hi):
        return '\n'.join((self.root / path).read_text().splitlines()[lo - 1:hi])

    def excerpt(self, path, symbol, lo, hi, reason, truncated):
        return dict(symbol=symbol, start_line=lo, end_line=hi, content=self.body(path, lo, hi),
                    source='current_worktree', selection_reason=reason, focus_line=None,
                    truncated=truncated)

    def sample(self):
        # Controlled adapter input: public retrieval of these four files is intentionally
        # not alleged to produce this complete two-anchor shape.
        raw_target = dict(source='wiki', record_type='code_symbol', record_id=self.target['id'],
                          file_path=TARGET, symbol='build', start_line=8, end_line=19)
        raw_support = dict(source='wrapped_log_caller', record_type='code_log_effect',
                           record_id=self.effect['id'], file_path=SUPPORT, symbol='refresh',
                           start_line=10, end_line=12)
        target_ex = self.excerpt(TARGET, 'Column', 9, 13, 'callable_mechanism_window', True)
        support_ex = self.excerpt(SUPPORT, 'refresh', 3, 13, 'query_term_window_within_anchor', False)
        def compact(row, excerpt):
            result = {k: row[k] for k in ('record_type', 'file_path', 'symbol')}
            bounds = {k: row[k] for k in ('start_line', 'end_line')}
            return dict(result, record_ids=[row['record_id']], source=row['source'],
                        source_ranges=[dict(bounds, symbol=row['symbol'])], read_window=bounds,
                        role='primary', source_excerpts=[excerpt])
        fresh = dict(status='current', generation=self.target['index_generation'])
        original = dict(query=self.query, project_id=self.project.project_id,
                        project_path=str(self.root), source_freshness=dict(fresh),
                        query_handoff=dict(code_anchors=[raw_target, raw_support],
                                           path_context={'activated': False}))
        before = dict(query=self.query, project_id=self.project.project_id, source_freshness=dict(fresh),
                      output_budget=dict(target_tokens=1500, estimated_tokens=0, truncated=True),
                      query_handoff=dict(
                          code_anchors=[compact(raw_target, target_ex), compact(raw_support, support_ex)],
                          log_anchors=[deepcopy(self.log)], relation_hints=[], path_context={'activated': False},
                          callable_evidence={'primary': {'evidence': 'unchanged'}},
                          source_excerpt_policy=dict(excerpt_count=2,
                                                     excerpt_chars=len(target_ex['content'])+len(support_ex['content']))))
        synchronize_estimate(before)
        return original, before

    def test_source_and_log_effect_authenticated_without_ranking_changes(self):
        original, before = self.sample()
        baseline = deepcopy(before)
        after = prioritize_web_body(self.project, original, before)
        self.assertIsNot(after, before)
        self.assertEqual(before, baseline)
        target, support = after['query_handoff']['code_anchors']
        complete, = target['source_excerpts']
        self.assertEqual(complete['content'], self.body(TARGET, 8, 19))
        self.assertEqual((complete['symbol'], complete['start_line'], complete['end_line'], complete['truncated']),
                         ('build', 8, 19, False))
        narrow, = support['source_excerpts']
        self.assertEqual(narrow['content'], self.body(SUPPORT, 10, 12))
        self.assertTrue(narrow['truncated'])
        self.assertEqual(support['read_window'], dict(start_line=3, end_line=13))
        self.assertEqual(self.body(SUPPORT, 3, 13),
                         before['query_handoff']['code_anchors'][1]['source_excerpts'][0]['content'])
        self.assertEqual(estimate_payload_tokens(after), after['output_budget']['estimated_tokens'])
        self.assertLessEqual(estimate_payload_tokens(after), 1500)
        restored = deepcopy(after)
        for old, new in zip(before['query_handoff']['code_anchors'], restored['query_handoff']['code_anchors']):
            new['read_window'] = old['read_window']
            new['source_excerpts'] = old['source_excerpts']
        restored['query_handoff']['source_excerpt_policy'] = before['query_handoff']['source_excerpt_policy']
        restored['output_budget'] = before['output_budget']
        self.assertEqual(restored, before)

    def test_fails_closed_for_unsupported_requests_and_evidence(self):
        for kind in ('explicit_log', 'wrong_effect', 'wrong_generation', 'ambiguous_caller',
                     'edited_excerpt', 'relation_hints', 'unknown_schema', 'explicit_identity'):
            with self.subTest(kind=kind):
                original, before = self.sample()
                oh, h = original['query_handoff'], before['query_handoff']
                if kind == 'explicit_log':
                    original['query'] = before['query'] = 'Locate WebView logs and the logging call graph.'
                if kind == 'wrong_effect':
                    h['log_anchors'][0]['effect_id'] += 100
                if kind == 'wrong_generation':
                    original['source_freshness']['generation'] += 1
                if kind == 'ambiguous_caller':
                    h['code_anchors'].append(deepcopy(h['code_anchors'][1]))
                if kind == 'edited_excerpt':
                    h['code_anchors'][0]['source_excerpts'][0]['content'] += 'X'
                if kind == 'relation_hints':
                    h['relation_hints'].append({'relation': 'calls'})
                if kind == 'unknown_schema':
                    h['code_anchors'][1]['source_excerpts'][0]['unclassified'] = True
                if kind == 'explicit_identity':
                    oh['code_anchors'][1]['identity_match'] = True
                self.assertIs(prioritize_web_body(self.project, original, before), before)

    def test_valid_projection_declines_when_actual_estimator_exceeds_budget(self):
        original, before = self.sample()
        with patch('tools.agent_memory_runtime.context_web_body_budget.estimate_payload_tokens',
                   return_value=1501):
            self.assertIs(prioritize_web_body(self.project, original, before), before)

    def test_reread_and_staleness_fail_closed(self):
        original, before = self.sample()
        path = self.root / TARGET
        source = path.read_bytes()
        try:
            path.write_bytes(source+b'\n')
            self.assertIs(prioritize_web_body(self.project, original, before), before)
        finally:
            path.write_bytes(source)
        from tools.agent_memory_runtime import context_web_body_budget as module
        reads = {}
        unpatched = module._read_regular
        def change_on_reread(file):
            reads[file] = reads.get(file, 0) + 1
            return unpatched(file) + (b'\n' if reads[file] == 2 else b'')
        with patch.object(module, '_read_regular', side_effect=change_on_reread):
            self.assertIs(prioritize_web_body(self.project, original, before), before)
        self.assertIn(2, reads.values())

    def test_ambiguous_source_inventory_fails_closed(self):
        from tools.agent_memory_runtime import context_web_body_budget as module

        original, before = self.sample()
        parse = module.web_policy_inventory
        def repeated_chain(text):
            inventory = parse(text)
            if inventory and inventory['chains']:
                inventory['chains'] *= 2
            return inventory
        with patch.object(module, 'web_policy_inventory', side_effect=repeated_chain):
            self.assertIs(prioritize_web_body(self.project, original, before), before)

    def test_independent_public_input_still_does_not_claim_the_web_body(self):
        actual = json.loads(cli(self.project, 'context', '--query', self.query, '--compact', '--json'))
        self.assertFalse(any(a['file_path'] == TARGET for a in actual['query_handoff']['code_anchors']))
        baseline = json.loads((FIXTURE / 'baseline.json').read_text())
        self.assertEqual(baseline.pop('project_id') is not None, True)
        self.assertEqual(actual.pop('project_id'), self.project.project_id)
        self.assertEqual(actual, baseline)
