# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime.context_snapshot_dispatch import snapshot_attachment
from tools.agent_memory_runtime.query_results import diverse_log_matches,limited_context
from tools.agent_memory_runtime.query_render_recall import parse_render_request
from tools.agent_memory_runtime.query_lifecycle_selection import lifecycle_request
from tools.agent_memory_runtime.query_output_loop_selection import output_loop_request
from tools.agent_memory_runtime.query_command_source import command_request

class SnapshotDispatchIntegrationTests(unittest.TestCase):
 def test_dispatch_selects_one_attachment_without_merging_receipts(self):
  modules=['query_render_selection.attach_render_excerpts','query_lifecycle_selection.attach_lifecycle_excerpts','query_output_loop_selection.attach_output_loop_excerpts','query_command_selection.attach_command_excerpts']
  receipts=[[object()]for _ in modules]
  for selected in range(4):
   args=[receipts[i]if i<=selected else None for i in range(4)]
   with patch('tools.agent_memory_runtime.'+modules[selected])as attach:
    value,fn=snapshot_attachment(*args)
    self.assertIs(value,receipts[selected]);self.assertIs(fn,attach)
  value,fn=snapshot_attachment();self.assertIsNone(value);self.assertTrue(callable(fn))
 def test_actual_request_lanes_do_not_overlap(self):
  requests=['Return the UI rendering cleanup owner.','请定位同时负责生命周期恢复、状态更新和持久化的源码。','Locate output iteration and accumulation ownership.','Locate the menu command binding owner for Stop sync.']
  recognizers=[parse_render_request,lifecycle_request,output_loop_request,command_request]
  for selected,q in enumerate(requests):
   self.assertEqual([bool(f(q))for f in recognizers],[i==selected for i in range(4)])
 def test_disabled_lanes_keep_single_pass_and_usage_once(self):
  baseline={'query':'unrelated ordinary request'}
  with patch('tools.agent_memory_runtime.query_results._context_pass',return_value=baseline)as call,patch('tools.agent_memory_runtime.query_results.record_context_use')as use,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
   self.assertIs(limited_context(None,baseline['query']),baseline)
  call.assert_called_once();use.assert_called_once_with(None,baseline);miss.assert_called_once_with(None,'context',baseline['query'],baseline)
 def test_extracted_log_selection_identity_and_order(self):
  ordinary=[{'kind':'log_event','id':i}for i in range(3)];wrapped=[{'kind':'log_effect','id':i}for i in range(3,6)]
  rows=ordinary+wrapped;chosen=diverse_log_matches(rows,3)
  self.assertEqual(chosen,[ordinary[0],wrapped[0],wrapped[1]])
  self.assertTrue(all(any(item is row for row in rows)for item in chosen))
  self.assertEqual(diverse_log_matches(rows,0),[])
 def test_command_hook_preserves_other_private_objects_and_failed_result(self):
  from tools.agent_memory_runtime.query_render_selection import RenderContext
  from tools.agent_memory_runtime.query_lifecycle_selection import LifecycleContext
  from tools.agent_memory_runtime.query_output_loop_selection import OutputLoopContext
  from tools.agent_memory_runtime.query_command_selection import bind_command_context
  baseline={'query':'base','wiki_matches':[]}
  for cls in (RenderContext,LifecycleContext,OutputLoopContext):
   result=cls(query='retained');result._sentinel=object();marker=result._sentinel
   self.assertIs(bind_command_context(None,'not a command request',result,baseline),result)
   self.assertIs(bind_command_context(None,'Locate the menu command binding owner for Stop sync.',result,baseline),result)
   self.assertIs(result._sentinel,marker)
 def test_combined_requests_grant_no_new_mixed_authority(self):
  recognizers=[parse_render_request,lifecycle_request,output_loop_request,command_request]
  for q in ['Return the UI rendering cleanup owner. Locate the menu command binding owner for Stop sync.','Locate output iteration and accumulation ownership. Locate the menu command binding owner for Stop sync.']:
   self.assertEqual([bool(f(q))for f in recognizers],[False]*4)
