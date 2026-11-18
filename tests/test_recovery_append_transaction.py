# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Synthetic transaction/resource components only; no CLI or live authority claim."""
import copy
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.context_recovery_append import _candidate, append_transaction
from tools.agent_memory_runtime.query_validation_log_capture import bounded_metadata

D = Path(__file__).resolve().parents[1] / 'docs/evidence/recovery10-additive-contract'


class RecoveryAppendTransactionTests(unittest.TestCase):
    def setUp(self):
        fixture = json.loads((D / 'ORIGINAL-DEVELOPMENT-INPUT.json').read_text())['families'][0]
        self.sources = fixture['sources']
        self.roots = []
        for path, name, end in [('src/runtime/SessionRegistry.ets', 'SessionRegistry', 11),
                                ('src/stores/SessionSyncStore.ets', 'SessionSyncStore', 9)]:
            self.roots.append({'anchor': {'file_path': path, 'symbol': name, 'symbol_type': 'class',
                                         'start_line': 1, 'end_line': end, 'record_id': len(self.roots)+1,
                                         'record_type': 'code_symbol'},
                               'excerpt': {'symbol': name, 'start_line': 1, 'end_line': end,
                                           'content': '\n'.join(self.sources[path].splitlines()),
                                           'source': 'validated_request_snapshot',
                                           'selection_reason': 'existing_recovery_role_range',
                                           'focus_line': None, 'truncated': False}})
        store = self.roots[1]
        self.base = {'query_handoff': {'code_anchors': [{'file_path': store['anchor']['file_path'],
                         'symbol': 'SessionSyncStore', 'source_excerpts': [copy.deepcopy(store['excerpt'])]}],
                     'callable_evidence': {'primary': {'keep': 'ordinary'}, 'alternatives': [{'competitor': True}]},
                     'log_anchors': [], 'source_excerpt_policy': {'source': 'current_worktree',
                       'body_persisted': False, 'excerpt_count': 1, 'excerpt_chars': len(store['excerpt']['content'])}},
                     'evidence_gaps': ['conservative_gap'], 'sufficiency': {'status': 'ordinary'},
                     'output_budget': {'estimated_tokens': 300, 'target_tokens': 1500, 'truncated': True}}

    def test_append_and_only_truthful_counter_delta(self):
        before = copy.deepcopy(self.base)
        got = _candidate(self.base, self.roots)
        self.assertIsNotNone(got)
        self.assertEqual(self.base, before)
        self.assertEqual(got['query_handoff']['code_anchors'][0], before['query_handoff']['code_anchors'][0])
        self.assertEqual(got['query_handoff']['source_excerpt_policy']['excerpt_count'], 2)
        self.assertEqual(got['query_handoff']['source_excerpt_policy']['excerpt_chars'], 540)
        self.assertTrue(got['output_budget']['truncated'])
        got['query_handoff']['code_anchors'] = before['query_handoff']['code_anchors']
        got['query_handoff']['source_excerpt_policy'] = before['query_handoff']['source_excerpt_policy']
        got['output_budget']['estimated_tokens'] = before['output_budget']['estimated_tokens']
        self.assertEqual(got, before)

    def test_complete_registry_absent_store_can_append(self):
        registry = self.roots[0]
        self.base['query_handoff']['code_anchors'] = [{'file_path': registry['anchor']['file_path'],
                       'symbol': 'SessionRegistry', 'source_excerpts': [copy.deepcopy(registry['excerpt'])]}]
        self.base['query_handoff']['source_excerpt_policy']['excerpt_chars'] = 299
        result = _candidate(self.base, self.roots)
        self.assertIsNotNone(result)
        self.assertEqual(result['query_handoff']['code_anchors'][-1]['symbol'], 'SessionSyncStore')

    def test_partial_existing_path_never_upgraded(self):
        anchor = self.base['query_handoff']['code_anchors'][0]
        e = anchor['source_excerpts'][0];e['end_line'] = 5;e['content'] = '\n'.join(e['content'].splitlines()[:5])
        self.base['query_handoff']['source_excerpt_policy']['excerpt_chars'] = len(e['content'])
        self.assertIsNone(_candidate(self.base, self.roots))

    def test_unknown_policy_and_wrong_counts_refuse(self):
        for field, val in [('source', 'unknown'), ('excerpt_count', 0), ('excerpt_chars', 0), ('body_persisted', True)]:
            base = copy.deepcopy(self.base);base['query_handoff']['source_excerpt_policy'][field] = val
            self.assertIsNone(_candidate(base, self.roots))
        self.base['query_handoff']['source_excerpt_policy']['unknown'] = 1
        self.assertIsNone(_candidate(self.base, self.roots))

    def test_full_slots_and_token_refuse(self):
        base = copy.deepcopy(self.base)
        base['query_handoff']['code_anchors'] += [{'file_path': 'x.ets'}, {'file_path': 'y.ets'}]
        self.assertIsNone(_candidate(base, self.roots))
        self.base['output_budget']['target_tokens'] = 1
        self.assertIsNone(_candidate(self.base, self.roots))

    def test_direct_transaction_without_marker_has_no_authority(self):
        self.assertIs(append_transaction({}, {}, self.base, object()), self.base)

    def test_joint_bytes_not_individual_budgets(self):
        a = ['x' * 150 for _ in range(4000)];b = ['y' * 150 for _ in range(4000)]
        self.assertTrue(bounded_metadata(a));self.assertTrue(bounded_metadata(b))
        self.assertFalse(bounded_metadata([a, b]))

    def test_exact_scalar_utf8_boundary(self):
        for good, bad in [('x' * 16384, 'x' * 16385), ('é' * 8192, 'é' * 8193)]:
            self.assertTrue(bounded_metadata(good));self.assertFalse(bounded_metadata(bad))

    def test_exact_depth_nodes_and_invalid_values(self):
        v = None
        for _ in range(12):v = [v]
        self.assertTrue(bounded_metadata(v));self.assertFalse(bounded_metadata([v]))
        self.assertTrue(bounded_metadata([None] * 16383));self.assertFalse(bounded_metadata([None] * 16384))
        cycle=[];cycle.append(cycle)
        for v in [cycle, float('nan'), 1 << 64]:self.assertFalse(bounded_metadata(v))


if __name__ == '__main__':
    unittest.main()
