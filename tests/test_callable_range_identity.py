# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import unittest
from tools.agent_memory_runtime.query_callable_range_identity import resolve_candidate_range, ambiguous_portfolio_ranges
from tools.agent_memory_runtime.query_callable_evidence import callable_evidence
from tools.agent_memory_runtime.context_callable_focus import callable_anchor
from tools.agent_memory_runtime.query_callable_passage_portfolio import build_callable_passage_portfolio


def row(identifier=1, start=5, **extra):
    return dict(file_path='src/Handler.ets', symbol='execute', symbol_id=identifier,
                start_line=start, end_line=start+2, owner_name='Handler', owner_kind='class',
                score=50 if identifier==1 else 10, evidence_score=50 if identifier==1 else 10,
                reasons=['exact_symbol'], **extra)


class CallableRangeIdentityTests(unittest.TestCase):
    def test_same_name_callback_and_method_bind_their_own_id(self):
        for kind in ['callback', 'method']:
            candidates=[row(1,5),row(2,11)]
            ranges=[dict(item,selection_reason=kind) for item in candidates]
            result=callable_evidence(dict(callable_candidates=candidates,source_ranges=ranges))
            self.assertEqual(5,result['primary']['source_range']['start_line'])
            self.assertNotIn('symbol_id',result['primary'])
            self.assertEqual(11,resolve_candidate_range(candidates[1],ranges)['start_line'])

    def test_id_missing_or_wrong_pair_never_falls_back(self):
        for ranges in [[row(2)], [dict(row(),file_path='other')], [dict(row(),symbol='other')], []]:
            self.assertIsNone(resolve_candidate_range(row(),ranges))

    def test_invalid_id_bounds_and_outside_window_fail_closed(self):
        for c in [dict(row(),symbol_id=True),dict(row(),symbol_id=0),dict(row(),start_line=None)]:
            self.assertIsNone(resolve_candidate_range(c,[row()]))
        self.assertIsNone(resolve_candidate_range(row(),[row(1,11)]))
        self.assertIsNone(resolve_candidate_range(row(),[row(),row()]))

    def test_legacy_unique_pair_supported_duplicate_pair_rejected(self):
        candidate={'file_path':'src/Handler.ets','symbol':'execute'}
        self.assertIsNotNone(resolve_candidate_range(candidate,[row()]))
        self.assertIsNone(resolve_candidate_range(candidate,[row(),row(2,11)]))

    def test_portfolio_duplicate_names_fail_closed(self):
        candidates=[row(),row(2,11)]
        ranges=[dict(x,selection_reason='callable_symbol_range') for x in candidates]
        localization=dict(callable_candidates=candidates,source_ranges=ranges)
        evidence=callable_evidence(localization)
        result=build_callable_passage_portfolio('Find both execute and finish',localization,evidence)
        self.assertEqual('inactive',result['state'])
        self.assertIn('ambiguous_callable_identity',str(result))

    def test_unrelated_ineligible_pair_does_not_disable_portfolio_identity_check(self):
        extra=[dict(row(3),symbol='unrelated'),dict(row(4,20),symbol='unrelated')]
        self.assertFalse(ambiguous_portfolio_ranges([row()],[row(),*extra]))

    def test_disjoint_anchor_does_not_inherit_record_or_graph(self):
        primary=dict(row(2,11),source_range={'start_line':11,'end_line':13})
        existing=dict(row(),record_id=1,graph_relation='calls')
        result=callable_anchor(primary,existing)
        self.assertNotIn('record_id',result)
        self.assertNotIn('graph_relation',result)
        self.assertEqual(11,result['start_line'])

    def test_containing_class_anchor_remains_compatible(self):
        primary=dict(row(2,11),source_range={'start_line':11,'end_line':13})
        existing=dict(row(),start_line=1,end_line=30,record_id=1,symbol_type='class')
        self.assertEqual(1,callable_anchor(primary,existing)['record_id'])

    def test_same_pair_unselected_second_range_still_cannot_overwrite(self):
        self.assertTrue(ambiguous_portfolio_ranges([row()],[row(),row(2,11)]))


if __name__=='__main__':
    unittest.main()
