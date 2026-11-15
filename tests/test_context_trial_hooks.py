# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime.query_context_trials import qualify_context_trials,bind_context_trials
from tools.agent_memory_runtime.query_lifecycle_selection import LifecycleTrial
from tools.agent_memory_runtime.query_output_loop_selection import OutputLoopTrial

class ContextTrialHookTests(unittest.TestCase):
 def test_disabled_is_identity_and_no_qualification(self):
  gated={'matches':{'wiki_matches':[{'id':1}]}};context={'query':'q'}
  with patch('tools.agent_memory_runtime.query_lifecycle_selection.qualify_lifecycle')as lifecycle,patch('tools.agent_memory_runtime.query_output_loop_selection.qualify_output_loop')as output,patch('tools.agent_memory_runtime.query_render_selection.retain_background_candidates')as background:
   got,a,b=qualify_context_trials(None,'q',gated)
   self.assertIs(got,gated);self.assertIsNone(a);self.assertIsNone(b)
   self.assertIs(bind_context_trials('q',context,[]),context)
   lifecycle.assert_not_called();output.assert_not_called();background.assert_not_called()
 def test_qualification_order_and_shallow_copy_preserve_unrelated_lanes(self):
  items=[{'id':1}];logs=[{'id':2}];gated={'matches':{'wiki_matches':items,'code_log_matches':logs},'other':'value'}
  a=object();b=object();focused=[{'id':3}];order=[]
  with patch('tools.agent_memory_runtime.query_lifecycle_selection.qualify_lifecycle',side_effect=lambda *args:order.append(('lifecycle',args))or a),patch('tools.agent_memory_runtime.query_output_loop_selection.qualify_output_loop',side_effect=lambda *args:order.append(('output',args))or b),patch('tools.agent_memory_runtime.query_output_loop_selection.output_loop_focus',return_value=focused)as focus:
   got,aa,bb=qualify_context_trials('p','q',gated,allow_lifecycle=True,allow_output_loop=True)
  self.assertEqual(order,[('lifecycle',('p','q',items)),('output',('p','q',items))]);focus.assert_called_once_with(b,'q',items)
  self.assertIs(aa,a);self.assertIs(bb,b);self.assertIs(got['matches']['wiki_matches'],focused);self.assertIs(gated['matches']['wiki_matches'],items);self.assertIs(got['matches']['code_log_matches'],logs);self.assertEqual(got['other'],'value')
 def test_unknown_output_focus_leaves_original_object(self):
  gated={'matches':{'wiki_matches':[{}]}}
  with patch('tools.agent_memory_runtime.query_output_loop_selection.qualify_output_loop',return_value=None),patch('tools.agent_memory_runtime.query_output_loop_selection.output_loop_focus',return_value=None):
   got,a,b=qualify_context_trials(None,'q',gated,allow_output_loop=True)
  self.assertIs(got,gated);self.assertIsNone(a);self.assertIsNone(b)
 def test_wrapping_preserves_existing_order_and_authorities(self):
  context={'query':'q'};items=[{}];retained={'query':'q','retained':True};a=object();b=object()
  with patch('tools.agent_memory_runtime.query_render_selection.retain_background_candidates',return_value=retained)as retain:
   result=bind_context_trials('q',context,items,allow_render_recall=True,authority=a)
  retain.assert_called_once_with('q',context,items);self.assertIsInstance(result,LifecycleTrial);self.assertIs(result._lifecycle_authority,a);self.assertTrue(result['retained'])
  result=bind_context_trials('q',context,items,output_authority=b)
  self.assertIsInstance(result,OutputLoopTrial);self.assertIs(result._output_loop_authority,b)
