"""Finite lifecycle log context, using normally learned synthetic source only."""
from copy import copy, deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.agent_memory_runtime.context_compact import compact_context, _compact_context
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.query_context_trials import bind_context_trials
from tools.agent_memory_runtime.query_lifecycle_selection import (
    LifecycleTrial, qualify_lifecycle, bind_lifecycle_context, snapshot,
)
from tools.agent_memory_runtime.query_lifecycle_log_context import (
    LifecycleLogContext, bind_lifecycle_log_context, lifecycle_log_receipt,
    enrich_lifecycle_log_context, compact_lifecycle_log_context,
)
from tools.agent_memory_runtime.query_results import _context_pass, limited_context
from tools.agent_memory_runtime.storage import resolve_project

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/lifecycle_log_context.json'
CODE_FIELDS = ('code_anchors', 'callable_evidence', 'source_excerpt_policy')


class LifecycleLogContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name) / 'source'
        cls.root.mkdir()
        cls.home = Path(cls.directory.name) / 'memory'
        cls.family = next(f for f in json.loads(FIXTURE.read_text())['families']
                          if f['id'] == 'two-owner-cross-file-log')
        for name, source in cls.family['sources'].items():
            (cls.root / name).write_text(source)
        for arguments in [('init',), ('learn-path', '--path', '.', '--json')]:
            subprocess.run([sys.executable, str(ROOT / 'tools/agent_memory.py'),
                            *arguments, '--project', str(cls.root),
                            '--memory-home', str(cls.home)], cwd=ROOT,
                           capture_output=True, text=True, check=True)
        cls.project = resolve_project(str(cls.root), str(cls.home))
        cls.main_query = cls.family['queries'][0]['query']
        cls.saved_base = _context_pass(cls.project, cls.main_query)
        captured = []
        def capture(query, context, items, **kwargs):
            captured.append(deepcopy(items))
            return bind_context_trials(query, context, items, **kwargs)
        with patch('tools.agent_memory_runtime.query_context_trials.bind_context_trials', side_effect=capture):
            cls.saved_trial = dict(_context_pass(cls.project, cls.main_query, allow_lifecycle=True))
        cls.saved_pool = captured[0]
        cls.path = build_context_facade(cls.project).path_context.build(cls.main_query)

    def setUp(self):
        for name, source in self.family['sources'].items():
            (self.root / name).write_text(source)
        self.query = self.main_query
        self.base = deepcopy(self.saved_base)
        self.base['query_handoff']['path_context'] = deepcopy(self.path)
        self.pool = deepcopy(self.saved_pool)
        self.authority = qualify_lifecycle(self.project, self.query, self.pool)
        self.assertIsNotNone(self.authority)
        self.trial = LifecycleTrial(deepcopy(self.saved_trial))
        self.trial['query_handoff']['path_context'] = deepcopy(self.path)
        self.trial._lifecycle_authority = self.authority
        self.trial._lifecycle_pool = deepcopy(self.pool)
        self.trial._lifecycle_pool_binding = snapshot(self.pool)
        self.ordinary = _compact_context(self.base)

    def bind(self):
        return bind_lifecycle_log_context(self.query, self.base, self.trial)

    def require_context(self):
        result = self.bind()
        self.assertIsInstance(result, LifecycleLogContext)
        return result

    def assert_whitelist(self, after, before):
        restored = deepcopy(after)
        for key in CODE_FIELDS:
            if key in before['query_handoff']:
                restored['query_handoff'][key] = deepcopy(before['query_handoff'][key])
            else:
                restored['query_handoff'].pop(key, None)
        restored['output_budget']['estimated_tokens'] = before['output_budget']['estimated_tokens']
        self.assertEqual(restored, before)

    def test_complete_positive_classes_and_exact_noncode(self):
        self.assertIs(bind_lifecycle_context(self.query, self.base, self.trial), self.base)
        result = self.require_context()
        self.assertEqual(dict(result), self.base)
        after = compact_lifecycle_log_context(result, self.ordinary)
        self.assertIsNot(after, self.ordinary)
        anchors = after['query_handoff']['code_anchors']
        self.assertEqual({a['file_path'] for a in anchors}, {'BufferSession.ets', 'EditorSession.ets'})
        self.assertEqual(len(anchors), 2)
        for anchor in anchors:
            excerpts = anchor['source_excerpts']
            self.assertEqual(len(excerpts), 1)
            excerpt = excerpts[0]
            self.assertEqual((excerpt['start_line'], excerpt['end_line']), (1, 12))
            self.assertFalse(excerpt['truncated'])
            self.assertEqual(excerpt['content'], '\n'.join(self.family['sources'][anchor['file_path']].splitlines()))
        self.assertLessEqual(after['output_budget']['estimated_tokens'], 1500)
        self.assert_whitelist(after, self.ordinary)
        logs = self.ordinary['query_handoff']['log_anchors']
        self.assertEqual({x['evidence_class'] for x in logs}, {'direct', 'static_wrapped'})
        wrapped = next(x for x in logs if x['evidence_class'] == 'static_wrapped')
        self.assertTrue(wrapped.get('call_path_locations'))
        self.assertEqual(after['query_handoff']['log_anchors'], logs)
        self.assertEqual(dict(result), self.base)

    def test_copy_serialization_and_public_mapping_mutation(self):
        result = self.require_context()
        for clone in (dict(result), copy(result), deepcopy(result), json.loads(json.dumps(result))):
            self.assertIsNone(lifecycle_log_receipt(clone))
            self.assertIs(compact_lifecycle_log_context(clone, self.ordinary), self.ordinary)
        for key, value in [('query', self.query + 'extra'), ('project_id', 'wrong')]:
            result = self.require_context()
            result[key] = value
            self.assertIsNone(lifecycle_log_receipt(result))
        result = self.require_context()
        result['query_handoff']['log_anchors'].reverse()
        self.assertIsNone(lifecycle_log_receipt(result))

    def test_private_pool_authority_and_binding_mutation(self):
        result = self.require_context()
        result._pool[0]['score'] = -999
        self.assertIsNone(lifecycle_log_receipt(result))
        result = self.require_context()
        result._binding = ()
        self.assertIsNone(lifecycle_log_receipt(result))
        result = self.require_context()
        self.authority._receipts[0]['owner']['end_line'] += 1
        self.assertIsNone(lifecycle_log_receipt(result))

    def test_pool_identity_or_membership_change_fails_closed(self):
        for key, value in [('id', -1), ('kind', 'unknown'), ('source_digest', '0' * 64), ('index_generation', 999)]:
            original = deepcopy(self.trial._lifecycle_pool)
            self.trial._lifecycle_pool[0][key] = value
            self.assertIs(self.bind(), self.base, key)
            self.trial._lifecycle_pool = original
        self.trial._lifecycle_pool.pop()
        self.assertIs(self.bind(), self.base)

    def test_each_source_drift_is_atomic_fallback(self):
        for name in ('BufferSession.ets', 'EditorSession.ets'):
            result = self.require_context()
            (self.root / name).write_text(self.family['sources'][name] + '// changed\n')
            self.assertIsNone(lifecycle_log_receipt(result))
            self.assertIs(compact_lifecycle_log_context(result, self.ordinary), self.ordinary)
            (self.root / name).write_text(self.family['sources'][name])

    def test_baseline_trial_and_initial_pool_identity_graph_protection(self):
        for side in ('base', 'trial', 'pool'):
            for key in ('identity_match', 'log_identity_match', 'graph_neighbor', 'graph_relation'):
                with self.subTest(side=side, key=key):
                    self.setUp()
                    if side == 'pool':
                        self.trial._lifecycle_pool[0][key] = True
                    else:
                        data = self.base if side == 'base' else self.trial
                        data['query_handoff']['code_anchors'][0][key] = True
                    self.assertIs(self.bind(), self.base)

    def test_raw_log_identity_flags_are_protected(self):
        for key in ('identity_match', 'log_identity_match', 'graph_neighbor', 'graph_relation'):
            with self.subTest(key=key):
                self.setUp()
                self.base['query_handoff']['log_anchors'][0][key] = True
                self.assertIs(self.bind(), self.base)

    def test_path_activated_candidates_seeds_and_wrapped_obligations(self):
        for key, value in [('activated', True), ('path_candidates', [{}]), ('seeds', [{}]), ('wrapped_log_evidence', True)]:
            for side in ('base', 'trial'):
                with self.subTest(key=key, side=side):
                    self.setUp()
                    data = self.base if side == 'base' else self.trial
                    data['query_handoff']['path_context'][key] = value
                    self.assertIs(self.bind(), self.base)
            self.setUp()
            result = self.require_context()
            path = deepcopy(self.path)
            path[key] = value
            final = enrich_lifecycle_log_context(result, self.query, path, self.base['source_freshness'])
            self.assertNotIsInstance(final, LifecycleLogContext)

    def test_full_event_and_named_owner_in_grammatical_query(self):
        cases = [('event-in-grammatical-background', None),
                 (None, 'A saved CheckpointTelemetry resets after relaunch. ' + self.main_query),
                 (None, 'A saved buffer resets after relaunch. Locate CheckpointTelemetry.publish.')]
        for case_id, query in cases:
            self.setUp()
            query = query or next(c['query'] for c in self.family['queries'] if c['id'] == case_id)
            self.query = query
            self.base['query'] = query
            self.trial['query'] = query
            self.trial._lifecycle_authority = qualify_lifecycle(self.project, query, self.pool)
            self.assertIs(self.bind(), self.base)

    def test_empty_logs_and_chinese_do_not_acquire_new_capability(self):
        self.base['query_handoff']['log_anchors'] = []
        self.assertIs(self.bind(), self.base)
        self.setUp()
        query = next(c['query'] for c in self.family['queries'] if c['id'] == 'chinese-compatibility')
        self.query = query
        self.base['query'] = query
        self.trial['query'] = query
        self.trial._lifecycle_authority = qualify_lifecycle(self.project, query, self.pool)
        self.assertIs(self.bind(), self.base)

    def test_missing_wrong_authority_pool_and_malformed_containers(self):
        for value in (None, {}, [], 'authority', 1):
            self.setUp()
            self.trial._lifecycle_authority = value
            self.assertIs(self.bind(), self.base)
        for value in (None, {}, 'pool', 1, [None], [{}]):
            self.setUp()
            self.trial._lifecycle_pool = value
            self.assertIs(self.bind(), self.base)
        for key, value in [('log_anchors', None), ('log_anchors', [None]),
                           ('code_anchors', 'bad'), ('path_context', None)]:
            self.setUp()
            self.base['query_handoff'][key] = value
            self.assertIs(self.bind(), self.base)

    def test_unknown_callable_and_log_bearing_callable_fall_back(self):
        for change in ({'unknown': True}, {'log_anchors': []}, {'path_context': {}}, {'log_identity_match': True}):
            self.setUp()
            result = self.require_context()
            ordinary = deepcopy(self.ordinary)
            ordinary['query_handoff']['callable_evidence'].update(change)
            self.assertIs(compact_lifecycle_log_context(result, ordinary), ordinary)
        for value in (None, [], 'unknown', 7):
            result = self.require_context()
            ordinary = deepcopy(self.ordinary)
            ordinary['query_handoff']['callable_evidence'] = value
            self.assertIs(compact_lifecycle_log_context(result, ordinary), ordinary)

    def test_unknown_nested_callable_structures_are_not_disposable(self):
        changes = [
            ('primary', 'unknown'), ('primary', []), ('primary', 7),
            ('alternatives', {}), ('alternatives', 'unknown'),
            ('alternatives', [None]), ('alternatives', ['unknown']),
            ('primary', {'effect_id': 123}),
            ('primary', {'call_path': ['publish', 'console.info']}),
            ('alternatives', [{'file_path': 'CheckpointRelay.ets', 'effect_id': 1}]),
            ('alternatives', [{'file_path': 'CheckpointRelay.ets', 'call_path': []}]),
            ('primary', {'file_path': 'BufferSession.ets', 'unknown': {'logs': []}}),
        ]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                result = self.require_context()
                ordinary = deepcopy(self.ordinary)
                ordinary['query_handoff']['callable_evidence'][key] = value
                self.assertIs(compact_lifecycle_log_context(result, ordinary), ordinary)

    def test_unbound_pool_names_query_and_project_mismatch(self):
        for key in ('symbol', 'qualified_name', 'owner_name', 'file_path'):
            self.setUp()
            self.trial._lifecycle_pool[0][key] = 'changed-before-binding'
            self.assertIs(self.bind(), self.base, key)
        self.setUp()
        self.trial._lifecycle_pool_binding = 'wrong'
        self.assertIs(self.bind(), self.base)
        self.setUp()
        self.trial['query'] = self.query + 'extra'
        self.assertIs(self.bind(), self.base)
        self.setUp()
        self.base['project_id'] = 'different-project'
        self.assertIs(self.bind(), self.base)
        self.setUp()
        self.trial['project_id'] = 'different-project'
        self.assertIs(self.bind(), self.base)

    def test_budget_overflow_preserves_whole_ordinary_payload(self):
        result = self.require_context()
        ordinary = deepcopy(self.ordinary)
        ordinary['output_budget']['target_tokens'] = 100
        self.assertIs(compact_lifecycle_log_context(result, ordinary), ordinary)
        for key, value in [('target_tokens', '1500'), ('target_tokens', -1), ('estimated_tokens', None)]:
            ordinary = deepcopy(self.ordinary)
            ordinary['output_budget'][key] = value
            self.assertIs(compact_lifecycle_log_context(result, ordinary), ordinary)

    def test_stale_freshness_or_changed_enrichment_falls_back(self):
        result = self.require_context()
        fresh = dict(self.base['source_freshness'], status='stale')
        self.assertNotIsInstance(enrich_lifecycle_log_context(result, self.query, self.path, fresh), LifecycleLogContext)
        self.assertNotIsInstance(enrich_lifecycle_log_context(result, self.query + 'x', self.path, self.base['source_freshness']), LifecycleLogContext)
        result['source_freshness']['generation'] += 1
        self.assertIs(compact_lifecycle_log_context(result, self.ordinary), self.ordinary)

    def test_ordinary_accounting_once_direct_and_facade(self):
        with patch('tools.agent_memory_runtime.query_results._context_pass', side_effect=[self.base, self.trial]), \
             patch('tools.agent_memory_runtime.query_results.record_context_use') as use, \
             patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
            result = limited_context(self.project, self.query)
            self.assertIsInstance(result, LifecycleLogContext)
            use.assert_called_once()
            miss.assert_called_once()
            self.assertEqual(dict(use.call_args.args[1]), self.base)
        with patch('tools.agent_memory_runtime.query_results._context_pass', side_effect=[self.base, self.trial]), \
             patch('tools.agent_memory_runtime.query_results.record_context_use') as use, \
             patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
            result = limited_context(self.project, self.query, defer_lifecycle_accounting=True)
            use.assert_not_called()
            from tools.agent_memory_runtime.context_facade import ContextFacade
            facade = ContextFacade(self.project, lambda *args: result, SimpleNamespace(build=lambda q: deepcopy(self.path)))
            final = facade.execute(self.query)
            self.assertIsInstance(final, LifecycleLogContext)
            use.assert_called_once()
            miss.assert_called_once()
            self.assertEqual(dict(use.call_args.args[1]), dict(final))
            self.assertEqual(dict(final), self.base)

    def test_runtime_dispatch_matches_private_transaction(self):
        result = self.require_context()
        self.assertEqual(compact_context(result), compact_lifecycle_log_context(result, self.ordinary))


if __name__ == '__main__':
    unittest.main()
