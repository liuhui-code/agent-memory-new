# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from copy import deepcopy
from tools.agent_memory_runtime.context_primary_budget import bounded_primary_prefix


def anchor(name, **extra):
    return dict(file_path=name, read_window={'start_line':1,'end_line':10}, **extra)


def handoff():
    return {'code_anchors':[anchor('a'), anchor('b'), anchor('graph',graph_relation='calls'), anchor('target',role='expansion')],
            'callable_evidence':{'certainty':'bounded','primary':{'file_path':'target','source_range':{'start_line':2,'end_line':8}}},
            'path_context':{'activated':False,'path_candidates':[]}}

class ContextPrimaryBudgetTests(unittest.TestCase):
    def test_retains_primary_and_existing_graph_without_growing_limit(self):
        h=handoff(); before=deepcopy(h); selected=bounded_primary_prefix(h,'Find shipment renderer',3)
        self.assertEqual(['a','target','graph'],[a['file_path'] for a in selected])
        self.assertEqual('primary',selected[1]['role']);self.assertEqual(before,h)
    def test_no_override_of_saturated_graph_or_identity_obligations(self):
        h=handoff();h['code_anchors'][0]['identity_match']=True;h['code_anchors'][1]['graph_relation']='renders'
        self.assertEqual(h['code_anchors'][:3],bounded_primary_prefix(h,'Find shipment renderer',3))
    def test_active_or_inactive_existing_paths_are_protected(self):
        for path in [{'activated':True},{'activated':False,'path_candidates':[{'complete':True}]}]:
            h=handoff();h['path_context']=path
            self.assertEqual(h['code_anchors'][:3],bounded_primary_prefix(h,'Find shipment renderer',3))
    def test_uncertain_or_missing_primary_cannot_reserve(self):
        for value in ['uncertain','unavailable']:
            h=handoff();h['callable_evidence']['certainty']=value
            self.assertEqual(h['code_anchors'][:3],bounded_primary_prefix(h,'Find shipment renderer',3))
    def test_missing_or_noncovering_source_range_cannot_reserve(self):
        for window in [None,{'start_line':True,'end_line':9},{'start_line':5,'end_line':9}]:
            h=handoff();h['code_anchors'][-1]['read_window']=window
            self.assertEqual(h['code_anchors'][:3],bounded_primary_prefix(h,'Find shipment renderer',3))
    def test_does_not_synthesize_absent_target(self):
        h=handoff();h['callable_evidence']['primary']['file_path']='absent'
        self.assertEqual(h['code_anchors'][:3],bounded_primary_prefix(h,'Find shipment renderer',3))
    def test_composite_query_keeps_existing_contract(self):
        h=handoff()
        self.assertEqual(h['code_anchors'][:3],bounded_primary_prefix(h,'Find both the caller and the callee',3))
    def test_already_retained_primary_and_zero_limit_are_noops(self):
        h=handoff();h['callable_evidence']['primary']['file_path']='a'
        self.assertEqual(h['code_anchors'][:3],bounded_primary_prefix(h,'Find shipment renderer',3))
        self.assertEqual([],bounded_primary_prefix(h,'Find shipment renderer',0))
    def test_raw_flags_and_merged_graph_survive_internal_guard_projection(self):
        from tools.agent_memory_runtime.context_compact import diverse_code_anchors
        from tools.agent_memory_runtime.context_primary_budget import projected_guards
        raw=[{'file_path':'a','identity_match':True,'start_line':1,'end_line':10},
             {'file_path':'b','log_identity_match':True,'start_line':1,'end_line':10},
             {'file_path':'graph','graph_neighbor':True,'start_line':1,'end_line':10},
             {'file_path':'target','start_line':1,'end_line':10}]
        h=handoff();h['code_anchors']=diverse_code_anchors(raw,True)
        self.assertFalse(any(x.get('identity_match') or x.get('graph_neighbor') or x.get('log_identity_match') for x in h['code_anchors']))
        guards=projected_guards({'code_anchors':raw})
        self.assertEqual(h['code_anchors'][:3],bounded_primary_prefix(h,'Find shipment renderer',3,guards))
        raw[2].pop('graph_neighbor');raw.append({'file_path':'graph','graph_relation':'calls','start_line':2,'end_line':3})
        self.assertIn('graph',projected_guards({'code_anchors':raw}))
    def test_compact_context_passes_guards_without_public_metadata(self):
        from tools.agent_memory_runtime.context_compact import compact_context
        raw=[{'file_path':'a','identity_match':True,'start_line':1,'end_line':10},
             {'file_path':'b','log_identity_match':True,'start_line':1,'end_line':10},
             {'file_path':'graph','graph_neighbor':True,'start_line':1,'end_line':10},
             {'file_path':'target','start_line':1,'end_line':10}]
        h=handoff();h['code_anchors']=raw
        h['log_keywords']=['padding'+str(i) for i in range(100)]
        h['callable_evidence']['primary']['reasons']=['source_evidence ' * 400]
        result=compact_context({'query_handoff':h,'query':'Find shipment renderer','semantic_patch_notes':[], 'conflict_notes':[]})
        self.assertNotIn('protected_paths',str(result))
        self.assertTrue(result['output_budget']['truncated'])
        self.assertEqual(3,len(result['query_handoff']['code_anchors']))
        self.assertTrue({'a','b','graph'}.issubset({x['file_path'] for x in result['query_handoff']['code_anchors']}))
