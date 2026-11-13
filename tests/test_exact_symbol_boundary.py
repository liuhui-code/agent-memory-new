# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from tools.agent_memory_runtime.text import score_weighted_fields

class ExactSymbolBoundaryTests(unittest.TestCase):
    def match(self,query,symbol):
        return score_weighted_fields(query,[],set(),[],[('exact_symbol',symbol,12)])
    def test_exact_and_qualified_literal_keep_bonus(self):
        for query in ('build','Locate View.build source.','Find BUILD().','`build`'):
            self.assertEqual((12.0,['exact_symbol']),self.match(query,'build'))
    def test_role_noun_and_identifier_substrings_are_not_exact(self):
        for query in ('Locate the Builder method.','rebuild','buildMore','prebuild','x_build','$build','build$', 'build工具','工具build'):
            self.assertEqual((0.0,[]),self.match(query,'build'),query)
    def test_short_query_is_not_full_symbol(self):
        self.assertEqual((0.0,[]),self.match('load','loadRecords'))
    def test_literal_regex_metacharacters(self):
        self.assertEqual((12.0,['exact_symbol']),self.match('Find Owner.$run().','Owner.$run'))
        self.assertEqual((0.0,[]),self.match('Find OwnerX$run().','Owner.$run'))
    def test_other_exact_fields_unchanged(self):
        self.assertEqual((4.0,['exact_file_path']),score_weighted_fields('unit.ts',[],set(),[],[('exact_file_path','src/unit.ts',4)]))
    def test_multiword_mentions_and_symbol_punctuation(self):
        for query,symbol in [('Please find loadRecords and describe its behavior.','loadRecords'),('Locate Owner.load_records implementation.','load_records'),('Find $refresh in the controller.','$refresh'),('请定位 更新缓存 方法。','更新缓存')]:
            self.assertEqual((12.0,['exact_symbol']),self.match(query,symbol))
    def test_identifier_boundaries_preserve_underscore_dollar_and_unicode(self):
        for query,symbol in [('load_records_more','load_records'),('prefix$refresh','$refresh'),('$refreshMore','$refresh'),('重新更新缓存','更新缓存'),('更新缓存后','更新缓存')]:
            self.assertEqual((0.0,[]),self.match(query,symbol))
    def test_lexical_recall_remains_even_without_exact_bonus(self):
        score,reasons=score_weighted_fields('Builder',['build'],{'build'},[('symbol','build',4)],[('exact_symbol','build',12)])
        self.assertEqual(4.0,score)
        self.assertIn('expanded_query:symbol',reasons)
        self.assertNotIn('exact_symbol',reasons)
