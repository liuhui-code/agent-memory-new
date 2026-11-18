# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Pure recall lane controls; mocks record SQL-lane inputs, no DB/product calls."""
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime import query_candidate_recall as recall
from tools.agent_memory_runtime.query_behavior_concepts import behavior_marker_terms
from tools.agent_memory_runtime.query_language import positive_retrieval_query
from tools.agent_memory_runtime.query_rank_fusion import ReciprocalRankFusion

Q = 'Locate the record iteration and accumulator implementation.'

class AccumulatorRecallBridgeTests(unittest.TestCase):
    def lanes(self, table, original, query=None, existing=()):
        query = positive_retrieval_query(original) if query is None and isinstance(original,str) else query or Q
        with ExitStack() as stack:
            def stub(name, **kwargs):
                return stack.enter_context(patch.object(recall,name,**kwargs))
            structural = stub('fts_ids',return_value=[1])
            method = stub('fts_table_ids',return_value=[2])
            stub('recall_focus_terms',return_value=[])
            stub('projected_method_terms',return_value=[])
            stub('behavior_marker_terms',return_value=list(existing))
            stub('projected_behavior_terms',return_value=list(existing))
            stub('fielded_serving_candidates',return_value=SimpleNamespace(lanes={},audit={}))
            result = recall.recall_table_candidates(None,SimpleNamespace(project_id='p'),table,query,40,
                ReciprocalRankFusion(channel_weights=recall.CANDIDATE_CHANNEL_WEIGHTS),original_query=original)
            return structural.call_args_list,method.call_args_list,result

    def test_correct_existing_lanes_and_limits(self):
        for q in (Q,'Find item iteration and accumulator source','Return the batch iteration and accumulator owners.'):
            files,methods,out = self.lanes('code_files',q)
            self.assertEqual(2,len(files));self.assertEqual([],methods)
            self.assertEqual('"collectionfold"*',files[1].args[3]);self.assertEqual(10,files[1].args[4])
            files,methods,out = self.lanes('code_symbols',q)
            self.assertEqual(1,len(files));self.assertEqual(1,len(methods))
            self.assertEqual('code_method_fts',methods[0].args[2])
            self.assertEqual('"collectionfold"*',methods[0].args[3]);self.assertEqual(24,methods[0].args[4])
            self.assertIn('behavior_method_fts',out.audit['lane_counts'])

    def test_original_request_not_positive_projection_grants_permission(self):
        rejected = [None, 'Do not '+Q, '"'+Q+'"', Q+' Also find logs.',
            Q.replace('Locate','Compare'), Q.replace('record','bag'),
            Q.replace('accumulator','result'), Q.replace('Locate','Locate only'),
            'A collection of fragments is reduced to its last value; '+Q,
            Q+' except the display panel.']
        for original in rejected:
            for table in ('code_files','code_symbols'):
                with self.subTest(original=original,table=table):
                    files,methods,_ = self.lanes(table,original,query=Q)
                    self.assertEqual(1,len(files));self.assertEqual([],methods)
        for table in ('code_files','code_symbols'):
            files,methods,_=self.lanes(table,Q,query='different transformed query')
            self.assertEqual(1,len(files));self.assertEqual([],methods)

    def test_dedup_other_tables_and_shared_concept_unchanged(self):
        self.assertNotIn('collectionfold',behavior_marker_terms(Q))
        for table in ('code_files','code_symbols'):
            files,methods,_=self.lanes(table,Q,existing=['collectionfold'])
            expression=(files[1] if table=='code_files' else methods[0]).args[3]
            self.assertEqual('"collectionfold"*',expression)
        files,methods,_=self.lanes('code_log_statements',Q)
        self.assertEqual(1,len(files));self.assertEqual([],methods)

    def test_port_passes_exact_original_without_substitution(self):
        original=Q+' excluding store.'
        positive=positive_retrieval_query(original)
        self.assertEqual(Q, positive)
        for name in ('code_files', 'code_symbols'):
            files, methods, _ = self.lanes(name, original, query=positive)
            self.assertEqual(1, len(files)); self.assertEqual([], methods)
        fake=recall.TableCandidateRecall([],{}, {},{})
        with patch.object(recall,'recall_table_candidates',return_value=fake) as table, \
             patch.object(recall,'fetch_rows_by_ids',return_value=[]), \
             patch.object(recall,'filter_fresh_candidate_rows',side_effect=lambda c,p,r:(r,{})):
            recall.SQLiteCandidateRecall(original_query=original).recall(None,SimpleNamespace(),positive)
        self.assertTrue(table.call_count)
        for call in table.call_args_list:
            self.assertEqual(positive,call.args[3]);self.assertEqual(original,call.args[7])
