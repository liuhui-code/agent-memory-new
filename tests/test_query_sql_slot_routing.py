"""Mechanical routing and single-accounting controls, no product query runs."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_query_sql_slot_selection as binding_tests
from tools.agent_memory_runtime import query_sql_slot_selection as sel
from tools.agent_memory_runtime.context_facade import ContextFacade
from tools.agent_memory_runtime.query_context_trials import bind_source_views
from tools.agent_memory_runtime.query_results import limited_context


class RoutingTests(unittest.TestCase):
    setUp=binding_tests.BindingTests.setUp
    bind=binding_tests.BindingTests.bind

    def test_source_view_dispatch_keeps_raw_fields(self):
        data=bind_source_views(self.project,self.query,self.base,self.pool)
        self.assertIsInstance(data,sel.SqlSlotContext)
        self.assertEqual(dict(data),self.base)

    def test_limited_context_defer_and_adopt_once(self):
        for defer in (True,False):
            data=self.bind()
            with patch('tools.agent_memory_runtime.query_results._context_pass',return_value=data) as contextpass, \
                 patch('tools.agent_memory_runtime.query_results.record_context_use') as used, \
                 patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as missed, \
                 patch('tools.agent_memory_runtime.context_compact._compact_context',return_value=self.base):
                result=limited_context(self.project,self.query,defer_sql_slot_accounting=defer)
                self.assertIsInstance(result,sel.SqlSlotContext);contextpass.assert_called_once()
                if defer:
                    self.assertTrue(result._pending_accounting);used.assert_not_called();missed.assert_not_called()
                else:
                    used.assert_called_once();missed.assert_called_once()
                    self.assertEqual(len(used.call_args.args[1]['query_handoff']['code_anchors']),3)

    def test_facade_failed_adoption_accounts_original_once(self):
        data=self.bind();data._pending_accounting=True
        path=dict(activated=True,path_candidates=[])
        facade=ContextFacade(self.project,lambda *a:data,SimpleNamespace(build=lambda q:copy.deepcopy(path)))
        with patch('tools.agent_memory_runtime.context_facade.filter_fresh_path_context',side_effect=lambda p,path,f:(path,f)), \
             patch('tools.agent_memory_runtime.query_results.record_context_use') as used, \
             patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as missed:
            result=facade.execute(self.query)
            self.assertNotIsInstance(result,sel.SqlSlotContext)
            self.assertEqual(result['query_handoff']['code_anchors'],self.base['query_handoff']['code_anchors'])
            self.assertEqual(used.call_args.args[1],result)
            used.assert_called_once();missed.assert_called_once()
            facade.execute(self.query)
            used.assert_called_once();missed.assert_called_once()

if __name__=='__main__':unittest.main()
