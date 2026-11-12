# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from pathlib import Path
import tempfile
import unittest
from tools.agent_memory_runtime.context_source_excerpt import read_binding_excerpt, binding_context_covers

SOURCE = """export class Actions {
  commands = [
    {
      caption: 'Close',
      run: () => {
        this.closeSession()
      }
    }
  ]
}
"""

class BindingExcerptIntegrationTests(unittest.TestCase):
    def test_label_and_own_call_read_together_with_exact_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'Actions.ets';path.write_text(SOURCE)
            r={'symbol':'run','start_line':5,'end_line':7,'selection_reason':'ecma_property_callback_window'}
            e=read_binding_excerpt(path,r,1500)
            self.assertEqual((3,8),(e['start_line'],e['end_line']))
            self.assertIn("caption: 'Close'",e['content']);self.assertIn('closeSession()',e['content'])
            self.assertEqual('\n'.join(SOURCE.splitlines()[2:8]),e['content'])
            self.assertFalse(e['truncated'])
    def test_budget_insufficient_for_object_keeps_callback(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'Actions.ets';path.write_text(SOURCE)
            r={'symbol':'run','start_line':5,'end_line':7,'selection_reason':'ecma_property_callback_window'}
            budget=len('\n'.join(SOURCE.splitlines()[4:7]))
            e=read_binding_excerpt(path,r,budget)
            self.assertEqual(5,e['start_line']);self.assertNotIn('caption',e['content'])
    def test_exact_callable_and_log_owner_are_not_extended(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'Actions.ets';path.write_text(SOURCE)
            for reason in ['bounded_callable_primary','selected_log_event_owner']:
                e=read_binding_excerpt(path,{'symbol':'run','start_line':5,'end_line':7,'selection_reason':reason},1500)
                self.assertEqual((5,7),(e['start_line'],e['end_line']))
    def test_context_contains_second_callback_without_double_charge(self):
        context={'start_line':3,'end_line':20,'truncated':False,'selection_reason':'callback_binding_context'}
        self.assertTrue(binding_context_covers([context],{'start_line':12,'end_line':15}))
        self.assertFalse(binding_context_covers([{**context,'truncated':True}],{'start_line':12,'end_line':15}))
        self.assertFalse(binding_context_covers([context],{'start_line':22,'end_line':25}))
