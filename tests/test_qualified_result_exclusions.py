# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from tools.agent_memory_runtime.query_language import excluded_code_candidate, excluded_result_identifiers, positive_retrieval_query
from tools.agent_memory_runtime.query_callable_evidence_set import excluded_member
from tools.agent_memory_runtime.query_qualified_exclusions import qualified_exclusions


class QualifiedResultExclusionTests(unittest.TestCase):
    query = 'Locate AlphaService.start; exclude AlphaService.stop.'

    def check(self, item, expected):
        for check in (excluded_code_candidate, excluded_member):
            self.assertEqual(check(self.query, item), expected, (check.__name__, item))

    def test_same_owner_other_method_remains(self):
        self.check({'owner_name':'AlphaService','symbol':'start'},False)
        self.check({'owner_name':'AlphaService','symbol':'stop'},True)

    def test_other_owner_same_method_remains(self):
        self.check({'owner_name':'OtherService','symbol':'stop'},False)

    def test_directory_and_file_cannot_supply_owner(self):
        for path in ('src/AlphaService/OtherService.ts','src/AlphaService.ts'):
            self.check({'file_path':path,'symbol':'stop'},False)

    def test_qualified_identity_exact(self):
        self.check({'qualified_name':'AlphaService.stop'},True)
        for name in ('AlphaService.stopLater','Other.AlphaService.stop','alphaservice.stop'):
            self.check({'qualified_name':name},False)

    def test_owner_and_missing_fields_remain(self):
        for item in ({},{'owner_name':'AlphaService'},{'symbol':'AlphaService'},{'symbol':'stop'}):
            self.check(item,False)

    def test_legacy_name_roles_and_comparison(self):
        row={'owner_name':'AlphaService','symbol':'start'}
        self.assertTrue(excluded_code_candidate('Locate OtherService; exclude AlphaService.',row))
        self.assertTrue(excluded_code_candidate('Locate OtherService; exclude service.',row))
        self.assertFalse(excluded_code_candidate('Locate AlphaService.start compared with AlphaService.stop.',row))

    def test_no_owner_leak_to_secondary_exclusion(self):
        self.assertEqual(excluded_result_identifiers(self.query),set())
        self.assertEqual(positive_retrieval_query(self.query),'Locate AlphaService.start;')

    def test_mixed_and_multiple_clauses(self):
        query = self.query + '; exclude OtherService.stop; exclude LegacyService.'
        self.assertTrue(excluded_code_candidate(query, {'owner_name':'OtherService','symbol':'stop'}))
        self.assertTrue(excluded_code_candidate(query, {'owner_name':'LegacyService','symbol':'start'}))
        self.assertFalse(excluded_code_candidate(query, {'owner_name':'AlphaService','symbol':'start'}))
        self.assertEqual(excluded_result_identifiers(query), {'legacyservice'})

    def test_conflicting_fields_fail_open(self):
        self.check({'qualified_name':'AlphaService.stop','owner_name':'OtherService','symbol':'stop'},False)
        self.check({'qualified_name':'OtherService.stop','owner_name':'AlphaService','symbol':'stop'},False)
        self.check({'qualified_name':'AlphaService.stop','owner_name':'AlphaService','symbol':'start'},False)

    def test_mixed_file_projection_and_graph_protection(self):
        from tools.agent_memory_runtime.context_code_exclusions import project_code_exclusions
        start={'file_path':'src/AlphaService.ts','owner_name':'AlphaService','symbol':'start'}
        stop={**start,'symbol':'stop'}
        anchors=[start,stop]
        self.assertEqual(project_code_exclusions(anchors,self.query,anchors,[],{}),anchors)
        graph=[{**stop,'graph_neighbor':True}]
        self.assertEqual(project_code_exclusions(anchors,self.query,graph,[],{}),anchors)

    def test_complete_clause_scope(self):
        for suffix in ('AlphaService.stop and OtherService.stop.','AlphaService.stop.extra.', '`AlphaService.stop`.'):
            self.assertEqual(qualified_exclusions('Locate AlphaService.start; exclude '+suffix)[0],set())
        self.assertEqual(qualified_exclusions(self.query)[0],{('AlphaService','stop')})


if __name__ == '__main__': unittest.main()
