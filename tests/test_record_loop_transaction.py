import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.agent_memory_runtime.context_record_loop_transaction import apply_record_loop_transaction, restore_whitelist
from tools.agent_memory_runtime.context_sufficiency import diagnosis_sufficiency
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens

D = Path(__file__).resolve().parents[1] / 'docs/evidence/record-loop-contract'
PUBLIC = json.loads((D / 'stage-c-merge-public.json').read_text())
CAPACITY = json.loads((D / 'stage-e-capacity.json').read_text())


def inputs(index=0):
    receipt = CAPACITY[index]
    row = next(r for r in PUBLIC if (r['cohort'], r['case']['id']) == (receipt['cohort'], receipt['id']))
    return copy.deepcopy(row['compact']), copy.deepcopy(receipt['hypothetical_payload']['query_handoff']['code_anchors'])


class RecordLoopTransactionTests(unittest.TestCase):
    def test_four_saved_capacity_shapes_full_set_and_baseline_untouched(self):
        for i in range(4):
            baseline, anchors = inputs(i)
            saved, saved_anchors = copy.deepcopy(baseline), copy.deepcopy(anchors)
            result = apply_record_loop_transaction(baseline, anchors)
            self.assertIsNot(result, baseline)
            self.assertEqual(result['query_handoff']['code_anchors'], anchors)
            self.assertEqual(restore_whitelist(result, baseline), baseline)
            self.assertEqual(baseline, saved)
            self.assertEqual(anchors, saved_anchors)
            self.assertLessEqual(estimate_payload_tokens(result), 1500)
            self.assertEqual(result['output_budget']['estimated_tokens'], estimate_payload_tokens(result))
            self.assertTrue(all(a['symbol_type'] == 'function' for a in result['query_handoff']['code_anchors']))

    def test_helper_nonempty_log_path_relations_unknown_fields_preserved(self):
        baseline, anchors = inputs()
        h = baseline['query_handoff']
        h['log_anchors'] = [{'id': 42, 'message_template': '{value}', 'metadata': {'nested': ['untouched']}}]
        h['path_context'] = {'activated': False, 'path_candidates': [{'id': 3}], 'extra': {'a': [1]}}
        h['relation_hints'] = [{'relation': 'opaque', 'source': {'id': 1}}]
        h['unknown'] = {'content': ['preserve']}
        baseline['unknown'] = {'nested': {'a': 3}}
        baseline['evidence_gaps'] = ['custom-first', 'no_code_anchor', 'custom-last']
        baseline['sufficiency'] = diagnosis_sufficiency(h, baseline['evidence_gaps'], baseline['source_freshness'])
        baseline['sufficiency']['unknown'] = ['unchanged']
        result = apply_record_loop_transaction(baseline, anchors)
        self.assertIsNot(result, baseline)
        for key in ('log_anchors', 'path_context', 'relation_hints', 'unknown'):
            self.assertEqual(result['query_handoff'][key], h[key])
        self.assertEqual(result['evidence_gaps'], ['custom-first', 'custom-last', 'limited_code_anchor_diversity'])
        self.assertEqual(restore_whitelist(result, baseline), baseline)
        # This exercises only the helper invariant, not public request authority.

    def test_invalid_complete_source_and_identity_shape_returns_same_object(self):
        mutations = [
            lambda a: a[0].update(symbol_type='class'),
            lambda a: a[0].update(record_ids=[]),
            lambda a: a[0]['source_excerpts'][0].update(truncated=True),
            lambda a: a[0]['source_excerpts'][0].update(source='current_worktree'),
            lambda a: a[0]['source_excerpts'][0].update(end_line=99),
            lambda a: a[0]['source_excerpts'][0].update(content='incomplete'),
            lambda a: a[0]['source_excerpts'][0].update(symbol='wrong'),
            lambda a: a[0]['read_window'].update(start_line=1),
            lambda a: a.append(copy.deepcopy(a[0])),
            lambda a: a[0]['source_excerpts'].append(copy.deepcopy(a[0]['source_excerpts'][0])),
        ]
        for mutate in mutations:
            baseline, anchors = inputs()
            mutate(anchors)
            self.assertIs(apply_record_loop_transaction(baseline, anchors), baseline)

    def test_hard_character_line_count_and_token_caps(self):
        baseline, anchors = inputs()
        too_many = []
        for i in range(4):
            a = copy.deepcopy(anchors[0]); a['record_ids'] = [100 + i]; too_many.append(a)
        self.assertIs(apply_record_loop_transaction(baseline, too_many), baseline)
        for chars, lines in ((1501, 7), (300, 41)):
            b, a = inputs(); e = a[0]['source_excerpts'][0]
            e['content'] = 'x' * chars + '\n' * (lines - 1)
            e['end_line'] = e['start_line'] + lines - 1
            a[0]['source_ranges'][0]['end_line'] = e['end_line']; a[0]['read_window']['end_line'] = e['end_line']
            self.assertIs(apply_record_loop_transaction(b, a), b)
        b, a = inputs(1)
        for anchor in a:
            excerpt = anchor['source_excerpts'][0]
            excerpt['content'] = 'x' * 1394 + '\n' * 6
        self.assertIs(apply_record_loop_transaction(b, a), b)  # 2800 total > 2600
        baseline['unknown_payload'] = 'word ' * 4000
        self.assertIs(apply_record_loop_transaction(baseline, anchors), baseline)
        baseline, anchors = inputs(); baseline['output_budget']['target_tokens'] = 100
        self.assertIs(apply_record_loop_transaction(baseline, anchors), baseline)

    def test_nonwhitelist_fault_injection_rejected_without_mutation(self):
        baseline, anchors = inputs(); saved = copy.deepcopy(baseline)
        from tools.agent_memory_runtime.context_budget import synchronize_estimate
        def corrupt(candidate):
            candidate['query_handoff']['log_keywords'].append('forbidden-change')
            synchronize_estimate(candidate)
        with patch('tools.agent_memory_runtime.context_record_loop_transaction.synchronize_estimate', corrupt):
            self.assertIs(apply_record_loop_transaction(baseline, anchors), baseline)
        self.assertEqual(baseline, saved)

    def test_unknown_callable_data_and_inconsistent_sufficiency_fail_closed(self):
        baseline, anchors = inputs()
        baseline['query_handoff']['callable_evidence']['unknown_log_evidence'] = {'id': 3}
        self.assertIs(apply_record_loop_transaction(baseline, anchors), baseline)
        baseline, anchors = inputs(); baseline['sufficiency']['coverage']['log_anchor_count'] = 99
        self.assertIs(apply_record_loop_transaction(baseline, anchors), baseline)

    def test_existing_policy_metadata_and_three_file_gap(self):
        baseline, anchors = inputs()
        baseline['query_handoff']['source_excerpt_policy'] = {'source': 'current_worktree', 'body_persisted': False, 'limit': 7, 'extra': {'k': 'v'}}
        baseline['evidence_gaps'] = ['limited_code_anchor_diversity', 'unknown-gap']
        for i in range(2):
            a = copy.deepcopy(anchors[0]); a['file_path'] = f'Other{i}.ts'; a['record_ids'] = [50 + i]; anchors.append(a)
        result = apply_record_loop_transaction(baseline, anchors)
        self.assertIsNot(result, baseline)
        self.assertEqual(result['evidence_gaps'], ['unknown-gap'])
        policy = result['query_handoff']['source_excerpt_policy']
        self.assertEqual(policy['limit'], 7)
        self.assertEqual(policy['extra'], {'k': 'v'})
        self.assertEqual(policy['excerpt_count'], 3)


if __name__ == '__main__':
    unittest.main()
