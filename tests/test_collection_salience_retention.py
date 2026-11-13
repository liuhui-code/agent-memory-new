# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest

class CollectionSalienceRetentionTests(unittest.TestCase):
    def test_partial_neighbor_cannot_reenter_complete_method_focus(self):
        from tools.agent_memory_runtime.query_code_selection import preserve_salient_evidence_candidates
        query = 'A click should update adjacent collection entries.'
        owner = {'file_path':'owner.ts','semantic_behavior_coverage':2,'match_reasons':['semantic_behavior']}
        noise = {'file_path':'scalar.ts','semantic_behavior_coverage':1,'match_reasons':['salient_query_evidence']}
        self.assertEqual([owner],preserve_salient_evidence_candidates([owner],[owner,noise],query=query))
    def test_no_behavior_contract_retains_salient_evidence(self):
        from tools.agent_memory_runtime.query_code_selection import preserve_salient_evidence_candidates
        owner = {'file_path':'owner.ts'}
        noise = {'file_path':'other.ts','match_reasons':['salient_query_evidence']}
        self.assertEqual([owner,noise],preserve_salient_evidence_candidates([owner],[owner,noise],query='Find relevant source'))
    def test_two_explicit_qualified_targets_are_not_dropped(self):
        from tools.agent_memory_runtime.query_code_selection import preserve_salient_evidence_candidates
        query = 'A tile click toggles only one item instead of neighboring entries; return the handler that writes the indexed collection. Also return LaneController.handleTap and TileWidget.handleTap.'
        from tools.agent_memory_runtime.query_behavior_concepts import behavior_marker_terms
        self.assertEqual(2, len(behavior_marker_terms(query)))
        owner = {'file_path':'LaneController.ts','owner_name':'LaneController','symbol':'handleTap','semantic_behavior_coverage':2,'match_reasons':['semantic_behavior']}
        other = {'file_path':'TileWidget.ts','owner_name':'TileWidget','symbol':'handleTap','semantic_behavior_coverage':1,'match_reasons':['salient_query_evidence']}
        self.assertEqual([owner,other],preserve_salient_evidence_candidates([owner],[owner,other],query=query))
