# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import dataclasses
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime.query_builder_request import (
    parse_builder_request, recall_projection, projected_method_terms,
    score_projected_code, filter_projected_method_ids,
)
from tools.agent_memory_runtime.query_method_evidence import qualifying_method_evidence_ids
from tools.agent_memory_runtime.text import score_weighted_fields

QUERY='请返回设置内边距和背景颜色的 Builder 源码。'

class BuilderPropertyRecallTests(unittest.TestCase):
    def test_frozen_full_request_controls(self):
        path=Path(__file__).parents[1]/'docs/evidence/builder-chinese-consumer/protocol.json'
        controls=json.loads(path.read_text())['request_controls']
        for control in controls:
            with self.subTest(query=control['query']):
                self.assertEqual(control['eligible'],parse_builder_request(control['query']) is not None)

    def test_full_original_ast_retains_observation_negatives(self):
        query='横向作品列表中的卡片被裁剪，请返回设置列表方向和高度的 Builder 源码，不要返回卡片或数据模型。'
        request=parse_builder_request(query)
        self.assertEqual(request.requirements,('listDirection','height'))
        self.assertEqual(request.exclusions,('card','model'))
        self.assertIn('作品',request.observation)
        self.assertEqual(request.original,query)

    def test_one_attribute_and_custom_port_unchanged(self):
        self.assertIsNone(recall_projection('请返回设置高度的 Builder 源码。'))
        self.assertIsNone(recall_projection(QUERY,object()))
        self.assertIsNone(recall_projection('Locate the reusable Builder that sets row height and alignment.'))

    def test_query_and_descriptor_binding(self):
        projection=recall_projection(QUERY)
        self.assertTrue(projection.valid_for(QUERY,QUERY))
        self.assertFalse(projection.valid_for(QUERY+' extra',QUERY))
        self.assertFalse(dataclasses.replace(projection,terms=('width','height')).valid_for(QUERY,QUERY))
        self.assertFalse(dataclasses.replace(projection,issuer=object()).valid_for(QUERY,QUERY))
        self.assertFalse(dataclasses.replace(projection,request=dataclasses.replace(projection.request,exclusions=('card',))).valid_for(QUERY,QUERY))
        self.assertEqual(projected_method_terms(QUERY,dict()),['builder'])

    def test_distinct_negative_ast_cannot_reuse_clean_query(self):
        one=QUERY[:-1]+'，不要返回卡片。'
        two=QUERY[:-1]+'，不要返回数据模型。'
        projection=recall_projection(one)
        self.assertFalse(projection.valid_for(projection.retrieval,two))
        self.assertFalse(projection.valid_for(projection.retrieval))
        self.assertFalse(projection.excludes({'file_path':'Plain.ets','owner_name':'Plain','qualified_name':'Plain.card'}))
        self.assertFalse(projection.excludes({'file_path':'Plain.ets','qualified_name':'Plain.card'}))
        self.assertFalse(projection.excludes({'file_path':'Plain.ets','qualified_name':'Plain.card.inner'}))

    def test_capacity_is_whole_projection_fallback(self):
        with patch('tools.agent_memory_runtime.query_builder_request.method_evidence_focus_terms',return_value=[str(i) for i in range(16)]):
            self.assertIsNone(recall_projection(QUERY))

    def test_old_field_weights_and_actual_expansion_reason(self):
        projection=recall_projection(QUERY)
        fields=[('method_evidence','padding backgroundcolor',.75)]
        score,reasons=score_projected_code(projection,{},QUERY,QUERY,['builder'],set(),fields,[])
        self.assertEqual(score,1.5)
        self.assertIn('expanded_builder_property:padding',reasons)
        self.assertIn('expanded_builder_property:backgroundcolor',reasons)
        self.assertFalse(any('exact' in x or 'source_operation' in x for x in reasons))
        empty=score_projected_code(projection,{},QUERY,QUERY,['builder'],set(),[('method_evidence','width',.75)],[])
        self.assertEqual(empty,(0.0,[]))
        self.assertEqual(score_projected_code(None,{},QUERY,QUERY,['builder'],set(),fields,[]),score_weighted_fields(QUERY,['builder'],set(),fields,[]))

    def test_no_query_rewrite_or_exact_identity_credit(self):
        projection=recall_projection(QUERY)
        score,reasons=score_projected_code(projection,{},QUERY,QUERY,[],set(),[('method_evidence','padding',.75)],[('exact_symbol','padding',12)])
        self.assertEqual(score,.75)
        self.assertNotIn('exact_symbol',reasons)

    def test_local_exclusions_no_global_alias(self):
        query=QUERY[:-1]+'，不要返回卡片或数据模型。'
        projection=recall_projection(query)
        for file,excluded in [('Card.ets',True),('CardView.ets',True),('Postcard.ets',False),('DataModel.ets',True),('SurfacePalette.ets',False)]:
            self.assertEqual(projection.excludes({'file_path':file}),excluded)
            score,_=score_projected_code(projection,{'file_path':file},query,projection.retrieval,[],set(),[('method_evidence','padding backgroundcolor',.75)],[])
            self.assertEqual(score,0 if excluded else 1.5)
        from tools.agent_memory_runtime.query_language import excluded_code_candidate
        self.assertFalse(excluded_code_candidate('不要返回卡片',{'file_path':'CardView.ets'}))

    def test_existing_two_term_coverage_gate(self):
        conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
        conn.execute('CREATE TABLE code_symbols(id INTEGER,project_id TEXT,file_path TEXT,owner_name TEXT,method_evidence TEXT)')
        conn.executemany('INSERT INTO code_symbols VALUES(?,?,?,?,?)',[(1,'p','CardView.ets','CardView','padding backgroundcolor'),(2,'p','Surface.ets','Surface','padding'),(3,'p','Palette.ets','Palette','padding backgroundcolor')])
        project=SimpleNamespace(project_id='p')
        query=QUERY[:-1]+'，不要返回卡片。';projection=recall_projection(query)
        terms=projected_method_terms(projection.retrieval,projection,query)
        ids=qualifying_method_evidence_ids(conn,project,[1,2,3],terms)
        self.assertEqual(ids,[1,3])
        self.assertEqual(filter_projected_method_ids(conn,project,ids,projection.retrieval,projection,query),[3])
        conn.close()

    def test_excluded_existing_row_gets_no_new_coverage(self):
        from tools.agent_memory_runtime.query_method_evidence import method_evidence_term_coverage
        query='请返回设置 width 和 内边距 的 Builder 源码，不要返回卡片。'
        projection=recall_projection(query)
        terms=projected_method_terms(projection.retrieval,projection,query,{'file_path':'Card.ets','owner_name':'Card'})
        self.assertEqual(terms,['width','builder'])
        self.assertEqual(method_evidence_term_coverage('width builder padding',terms),2)

    def test_whitespace_bounds(self):
        self.assertIsNotNone(parse_builder_request(' '*16+QUERY+' '*16))
        self.assertIsNone(parse_builder_request(' '*17+QUERY))
        self.assertIsNone(parse_builder_request(QUERY+' '*17))
        self.assertIsNone(parse_builder_request(QUERY.replace(' Builder','\u3000Builder')))


class BuilderLocalizationTransportTests(unittest.TestCase):
    def test_original_bound_matches_reused_without_mutation(self):
        from copy import deepcopy
        from tools.agent_memory_runtime.query_results import localization_input
        query=QUERY[:-1]+'，不要返回卡片或数据模型。'
        matches={'wiki_matches':[{'file_path':'Palette.ets','owner_name':'Palette'},
                  {'file_path':'Card.ets','owner_name':'Card'},
                  {'file_path':'DataModel.ets','owner_name':'DataModel'}],
                 'code_log_matches':[{'message':'retained'}]}
        original=deepcopy(matches)
        with patch('tools.agent_memory_runtime.query_results.collect_matches_with_audit') as collect, patch('tools.agent_memory_runtime.query_results.gate_matches_by_intent',side_effect=lambda p,q,m:{'matches':m}):
            result,safe=localization_input(object(),query,matches)
        collect.assert_not_called();self.assertTrue(safe)
        self.assertEqual(result['wiki_matches'],[matches['wiki_matches'][0]])
        self.assertEqual(result['code_log_matches'],matches['code_log_matches'])
        self.assertEqual(matches,original)

    def test_unknown_negative_request_keeps_old_recollection(self):
        from tools.agent_memory_runtime.query_results import localization_input
        from tools.agent_memory_runtime.query_language import positive_retrieval_query
        query=QUERY[:-1]+'，不要返回其他内容。'
        with patch('tools.agent_memory_runtime.query_results.collect_matches_with_audit',return_value=SimpleNamespace(matches={'wiki_matches':[]})) as collect, patch('tools.agent_memory_runtime.query_results.gate_matches_by_intent',side_effect=lambda p,q,m:{'matches':m}):
            project=object();result,safe=localization_input(project,query,{'wiki_matches':[{'file_path':'unused.ets'}]})
        collect.assert_called_once_with(project,positive_retrieval_query(query))
        self.assertEqual(result,{'wiki_matches':[]});self.assertTrue(safe)
