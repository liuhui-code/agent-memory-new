# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Pure finite-relevance controls; no product or DB invocation."""
import ast
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.agent_memory_runtime.query_record_loop_request import accumulator_markers
from tools.agent_memory_runtime.query_language import positive_retrieval_query
from tools.agent_memory_runtime.query_code_focus import score_file_behavior_match
from tools.agent_memory_runtime.query_collect import score_symbol_behavior_match
Q='Locate the record iteration and accumulator implementation.'

class AccumulatorRelevanceTests(unittest.TestCase):
    def test_original_projection_and_closed_request(self):
        self.assertEqual(('collectionfold',),accumulator_markers(Q,Q))
        self.assertEqual((),accumulator_markers(Q,'different projection'))
        for original in (None,'"'+Q+'"','Do not '+Q,Q+' Also find logs.',
                         Q.replace('Locate','Locate only'),Q.replace('Locate','Compare'),
                         Q.replace('accumulator','result'),Q+' excluding store.'):
            with self.subTest(original=original):
                self.assertEqual((),accumulator_markers(original,Q))
        original=Q+' excluding store.'
        self.assertEqual(Q,positive_retrieval_query(original))
        self.assertEqual((),accumulator_markers(original,positive_retrieval_query(original)))

    def test_file_exact_presence_default_and_dedup(self):
        for evidence in ('collectionfold','no marker','collectionfolding'):
            base=score_file_behavior_match(evidence,set(),Q,0,[])
            self.assertEqual(base,score_file_behavior_match(evidence,set(),Q,0,[],extra_markers=()))
            actual=score_file_behavior_match(evidence,set(),Q,0,[],extra_markers=('collectionfold','collectionfold'))
            self.assertEqual((4.0,['structural_behavior']) if evidence=='collectionfold' else base,actual)
        query='Find the shared records implementation.'
        base=score_file_behavior_match('collectionfold',set(),query,2,[])
        self.assertEqual(base,score_file_behavior_match('collectionfold',set(),query,2,[],extra_markers=('collectionfold',)))

    def test_symbol_uses_existing_formula_without_negative_delta(self):
        self.assertEqual((7.0,['semantic_behavior'],1),score_symbol_behavior_match('collectionfold',accumulator_markers(Q,Q),0,[]))
        for evidence in ('missing','collectionfolding'):
            self.assertEqual((2,[],0),score_symbol_behavior_match(evidence,accumulator_markers(Q,Q),2,[]))
        self.assertEqual((2,[],0),score_symbol_behavior_match('collectionfold',accumulator_markers(Q+' excluding store.',Q),2,[]))

    def test_collector_and_recall_actual_argument_wiring(self):
        root=Path(__file__).resolve().parents[1]/'tools/agent_memory_runtime'
        for filename,expected in [('query_collect.py',['query','candidate_query']),('query_candidate_recall.py',['original_query','query'])]:
            tree=ast.parse((root/filename).read_text())
            calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='accumulator_markers']
            self.assertEqual(1,len(calls));self.assertEqual(expected,[n.id for n in calls[0].args])
        tree=ast.parse((root/'query_collect.py').read_text())
        filecall=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='score_file_behavior_match')
        self.assertEqual('accumulator',next(k.value.id for k in filecall.keywords if k.arg=='extra_markers'))

        # Execute the real pre-DB collector boundary, stopping at the helper.
        from tools.agent_memory_runtime import query_collect
        class BoundaryReached(Exception): pass
        original=Q+' excluding store.'
        observed=[]
        def boundary(raw,candidate):
            observed.append((raw,candidate))
            raise BoundaryReached()
        with patch.object(query_collect,'recall_projection',return_value=None), \
             patch.object(query_collect,'accumulator_markers',side_effect=boundary), \
             patch.object(query_collect,'connect') as db:
            with self.assertRaises(BoundaryReached):
                query_collect.collect_matches_with_audit(None,original)
            db.assert_not_called()
        self.assertEqual([(original,Q)],observed)
