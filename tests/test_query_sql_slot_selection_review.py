"""Independent consumer regression; no query, DB or source-parser execution."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime import query_sql_slot_selection as selection
from test_query_sql_slot_guard import context, QUERY


class ConsumerReviewTests(unittest.TestCase):
    def test_actual_compact_active_path_cannot_bypass_raw_guard(self):
        data=selection.SqlSlotContext(context())
        data['source_freshness']={'status':'current','generation':1}
        data._qualified={'members':[{'index_generation':1}]}
        data._pool=[];data._descriptor=selection.sql_slot_request(QUERY)
        baseline=deepcopy(dict(data))
        baseline['query_handoff']['path_context']['activated']=True
        anchors=[{'placeholder':'already authenticated by mocked receipt'}]
        with patch.object(selection,'sql_slot_receipt',return_value=anchors), patch(
                'tools.agent_memory_runtime.context_record_loop_transaction.apply_record_loop_transaction',
                return_value={'unexpected':'presentation called'}) as apply:
            self.assertIs(selection.compact_sql_slot(data,baseline),baseline)
            apply.assert_not_called()

    def test_existing_field_cannot_escape_with_type_and_qname_tamper(self):
        import test_query_sql_slot_selection as fixtures
        from tools.agent_memory_runtime.sql_slot_source import inventory_source
        fixture = fixtures.BindingTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        path = next(r['file_path'] for r in fixture.files if '/pages/' in r['file_path'])
        owner = inventory_source((fixture.root / path).read_text())['declarations'][0]
        field = next(f for f in owner['fields'] if f['name'] == 'rows')
        template = next(r for r in fixture.rows if r['file_path'] == path)
        row = dict(template, id=100, symbol='rows', symbol_key='state-key',
                   qualified_name='Wrong.rows', symbol_type='function', owner_name='',
                   owner_kind='', start_line=field['span']['start_line'],
                   end_line=field['span']['end_line'])
        fixture.rows.append(row)
        fixture.pool.append(dict(row, kind='symbol'))
        self.assertIs(fixture.bind(), fixture.base)


if __name__=='__main__':unittest.main()
