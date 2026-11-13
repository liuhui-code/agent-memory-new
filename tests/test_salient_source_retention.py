# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from copy import deepcopy
from tools.agent_memory_runtime.query_code_selection import preserve_salient_evidence_candidates

QUERY='Locate production eviction ownership: size key delete.'

def candidate(path,method='',strings='',strong=False):
    return {'kind':'symbol','file_path':path,'symbol':'run','owner_name':'Worker',
            'start_line':2,'end_line':8,'method_evidence':method,'string_evidence':strings,
            'match_reasons':['salient_query_evidence']+(['multi_term_method_evidence'] if strong else [])}

class SalientSourceRetentionTests(unittest.TestCase):
    def setUp(self):
        self.owner=candidate('owner.ts','size key delete',strong=True)
        self.noise=candidate('noise.ts',strings='snapshot_key snapshot key')
    def retain(self,query=QUERY,focused=None,extra=None):
        focused=focused or [self.owner]
        return preserve_salient_evidence_candidates(focused,[*focused,extra or self.noise],query=query)
    def test_zero_method_redundant_literal_is_not_new_source_evidence(self):
        self.assertEqual([self.owner],self.retain())
    def test_novel_literal_is_retained_even_without_method_evidence(self):
        extra=candidate('literal.ts',strings='archive corrupted')
        self.assertEqual([self.owner,extra],self.retain('Locate eviction ownership size key delete archive corrupted.',extra=extra))
    def test_explicit_literal_retained_even_when_word_is_covered(self):
        self.noise['string_evidence']='key'
        self.assertEqual([self.owner,self.noise],self.retain(QUERY+' Include the literal `key`.'))
    def test_explicit_qualified_and_unqualified_targets_preserved(self):
        self.noise.update(owner_name='BackupStore',symbol='restore')
        for phrase in ('BackupStore.restore','BackupStore','restore'):
            self.assertEqual([self.owner,self.noise],self.retain(QUERY+' Locate '+phrase+'.'))
    def test_graph_evidence_is_not_changed(self):
        self.noise['match_reasons'].append('graph_neighbor')
        self.assertEqual([self.owner,self.noise],self.retain())
    def test_multi_entity_cues_do_not_deduplicate_entities(self):
        for suffix in ('Return both implementations.','返回两个来源。','Show two different owners.'):
            self.assertEqual([self.owner,self.noise],self.retain(QUERY+' '+suffix))
    def test_already_focused_entities_never_removed(self):
        second=candidate('second.ts','size key delete',strong=True)
        self.assertEqual([self.owner,second],self.retain(focused=[self.owner,second]))
    def test_missing_or_unproven_source_fails_open(self):
        for key in ('method_evidence','string_evidence','start_line','end_line'):
            other=deepcopy(self.noise);other.pop(key)
            self.assertEqual([self.owner,other],self.retain(extra=other))
        self.owner['match_reasons']=['salient_query_evidence']
        self.assertEqual([self.owner,self.noise],self.retain())
    def test_file_path_evidence_is_not_reclassified_as_method_source(self):
        self.noise['kind']='file'
        self.assertEqual([self.owner,self.noise],self.retain())

    def test_filtered_shortlist_is_not_refilled_from_lower_ranked_source(self):
        second=candidate('second-noise.ts',strings='cache_key cache key')
        lower=candidate('lower.ts','unexpected')
        query=QUERY+' unexpected.'
        actual=preserve_salient_evidence_candidates([self.owner],[self.owner,self.noise,second,lower],query=query)
        self.assertEqual([self.owner],actual)
    def test_missing_focus_never_silently_removes_all_candidates(self):
        actual=preserve_salient_evidence_candidates([], [self.noise], query=QUERY)
        self.assertEqual([self.noise],actual)
