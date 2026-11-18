# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime import context_preserve_source as planner
from tools.agent_memory_runtime import context_source_excerpt as source
from tools.agent_memory_runtime import context_request_policy as policy
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_budget import synchronize_estimate
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens


def excerpt(n, symbol='X'):
    return {'symbol':symbol,'start_line':1,'end_line':1,'content':'x'*n,
            'source':'current_worktree','selection_reason':'anchor_range',
            'focus_line':None,'truncated':False}


def payload():
    return {'query_handoff':{'code_anchors':[{'file_path':'first','role':'primary'},
                                            {'file_path':'second','role':'primary'}],
                             'log_anchors':[{'message_template':'keep'}],
                             'callable_evidence':{'unknown_roles':['unresolved']}},
            'sufficiency':{'scope':'retrieval_only'},
            'output_budget':{'target_tokens':2000,'estimated_tokens':0,'truncated':False}}


class PreserveSourcePlannerTests(unittest.TestCase):
    def test_ordered_fit_keeps_earlier_complete_and_all_evidence(self):
        for names in [('first','second'),('second','first')]:
            p=payload();p['query_handoff']['code_anchors']=[{'file_path':n,'role':'primary'} for n in names]
            anchors=p['query_handoff']['code_anchors']; protected=deepcopy(p['query_handoff'])
            self.assertTrue(planner.fit(p,anchors[0],excerpt(600,names[0]),2000))
            limit=estimate_payload_tokens(p)+100;p['output_budget']['target_tokens']=limit
            first=deepcopy(anchors[0]['source_excerpts'])
            planner.fit(p,anchors[1],excerpt(900,names[1]),limit)
            self.assertEqual(anchors[0]['source_excerpts'],first)
            self.assertFalse(first[0]['truncated'])
            self.assertLessEqual(estimate_payload_tokens(p),limit)
            self.assertTrue(p['output_budget']['truncated'])
            for a in anchors:a.pop('source_excerpts',None)
            p['query_handoff'].pop('source_excerpt_policy',None)
            self.assertEqual(p['query_handoff'],protected)

    def test_exact_total_estimate_accounts_for_policy_and_digit_changes(self):
        p=payload();a=p['query_handoff']['code_anchors'][0]
        self.assertTrue(planner.fit(p,a,excerpt(64),2000))
        limit=estimate_payload_tokens(p)
        # Fix target width before establishing exact boundary.
        p['output_budget']['target_tokens']=limit;synchronize_estimate(p)
        limit=estimate_payload_tokens(p);p['output_budget']['target_tokens']=limit;synchronize_estimate(p)
        self.assertEqual(estimate_payload_tokens(p),limit)
        self.assertEqual(p['output_budget']['estimated_tokens'],limit)
        self.assertEqual(p['query_handoff']['source_excerpt_policy']['excerpt_chars'],64)
        q=deepcopy(p);q['query_handoff']['code_anchors'][0].pop('source_excerpts');q['query_handoff'].pop('source_excerpt_policy')
        self.assertTrue(planner.fit(q,q['query_handoff']['code_anchors'][0],excerpt(64),limit))
        self.assertLessEqual(estimate_payload_tokens(q),limit)
        q=deepcopy(p);q['query_handoff']['code_anchors'][0].pop('source_excerpts');q['query_handoff'].pop('source_excerpt_policy')
        self.assertFalse(planner.fit(q,q['query_handoff']['code_anchors'][0],excerpt(64),limit-1))

    def test_acquisition_caps_per_anchor_total_no_refund_or_reread(self):
        p=payload();calls=[]
        def read(path,selected,cap):
            calls.append((str(path),cap));return excerpt(min(1000,cap))
        with patch.object(source,'resolved_root',return_value=Path('/pure')), patch.object(source,'safe_source_path',side_effect=lambda r,f:r/f), patch.object(source,'selected_ranges',return_value=[{'start_line':1,'end_line':1},{'start_line':2,'end_line':2}]), patch.object(source,'read_binding_excerpt',side_effect=read):
            planner.attach(p,'/pure',10000)
        self.assertEqual(calls,[('/pure/first',1500),('/pure/first',500),('/pure/second',1100),('/pure/second',100)])
        self.assertEqual(p['query_handoff']['source_excerpt_policy']['excerpt_chars'],2600)
        # Even omitted bodies spend the acquisition allowance; no retry or refund.
        p=payload();calls.clear()
        with patch.object(source,'resolved_root',return_value=Path('/pure')), patch.object(source,'safe_source_path',side_effect=lambda r,f:r/f), patch.object(source,'selected_ranges',return_value=[{},{}]), patch.object(source,'read_binding_excerpt',side_effect=read), patch.object(planner,'fit',return_value=False):
            self.assertEqual(planner.attach(p,'/pure',2000),0)
        self.assertEqual([c for _,c in calls],[1500,500,1100,100])
        # A full acquired callback body is not a retained coverage certificate.
        for kept, expected_fits in ((False,2),(True,1),('partial',2)):
            q=payload();q['query_handoff']['code_anchors']=q['query_handoff']['code_anchors'][:1]
            callback=excerpt(100);callback.update(start_line=1,end_line=10,selection_reason='callback_binding_context')
            nested=excerpt(80);nested.update(start_line=3,end_line=4)
            def retain(payload, anchor, item, budget):
                if kept:
                    actual=deepcopy(item)
                    if kept == 'partial': actual.update(truncated=True,end_line=2)
                    anchor['source_excerpts']=[actual]
                return kept
            with patch.object(source,'resolved_root',return_value=Path('/pure')), patch.object(source,'safe_source_path',return_value=Path('/pure/first')), patch.object(source,'selected_ranges',return_value=[{},{}]), patch.object(source,'read_binding_excerpt',side_effect=[callback,nested]) as reader, patch.object(planner,'fit',side_effect=retain) as fitting:
                planner.attach(q,'/pure',2000)
                self.assertEqual(fitting.call_count,expected_fits)
                self.assertEqual([c.args[2] for c in reader.call_args_list],[1500,1400])

    def test_metadata_overflow_before_read_and_missing_source_honest(self):
        raw={'query_handoff':{'callable_evidence':{'unresolved':'x'*12000}}}
        with patch.object(source,'read_binding_excerpt') as reader:
            with self.assertRaises(policy.CompactRequestIncomplete):
                compact_context(raw,token_budget=2000,preserve_selected_source_anchors=True)
            reader.assert_not_called()
        p=payload();old=deepcopy(p['query_handoff'])
        with patch.object(source,'resolved_root',return_value=Path('/pure')), patch.object(source,'safe_source_path',return_value=None), patch.object(source,'read_binding_excerpt') as reader:
            self.assertEqual(planner.attach(p,'/pure',2000),0);reader.assert_not_called()
        self.assertEqual(p['query_handoff'],old)
