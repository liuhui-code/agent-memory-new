"""Independent declaration/binding keyword negatives; no CLI or source edits."""
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.sql_slot_source import inventory_source, classify_sql_owner

CORPUS = Path(__file__).resolve().parents[1] / 'docs/evidence/sql-method-container/SOURCE-CONTROLS.json'


class ReservedIdentifierReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(CORPUS.read_text())['source_cases'][0]['sources']['src/services/IndexGateway.ets']

    def classification(self, source):
        inv = inventory_source(source)
        if inv['status'] == 'unknown':
            return inv
        return classify_sql_owner(source, inv['declarations'][0], 'findRows', 'LIKE')

    def test_reserved_parameter_binding_return(self):
        source = self.source.replace('findRows(term: string)', 'findRows(return: string)').replace('[term]', '[return]')
        self.assertEqual(self.classification(source)['status'], 'unknown')

    def test_reserved_const_binding_class(self):
        source = self.source.replace('const statement =', 'const class =').replace('execute(statement, [term])', 'execute(class, [term])')
        self.assertEqual(self.classification(source)['status'], 'unknown')

    def test_numeric_const_binding(self):
        source = self.source.replace('const statement =', 'const 123 =').replace('execute(statement, [term])', 'execute(123, [term])')
        self.assertEqual(self.classification(source)['status'], 'unknown')

    def test_return_await_requires_async_method(self):
        source = self.source.replace('async findRows(', 'findRows(').replace('return this.execute', 'return await this.execute')
        self.assertEqual(self.classification(source)['status'], 'unknown')

    def test_const_and_return_need_statement_boundary(self):
        source = self.source.replace("LIKE ?'\n    return", "LIKE ?' return")
        self.assertNotEqual(source, self.source)
        self.assertEqual(self.classification(source)['status'], 'unknown')

    def test_reserved_owner_binding_return(self):
        source = self.source.replace('class IndexGateway', 'class return')
        self.assertEqual(inventory_source(source)['status'], 'unknown')

    def test_reserved_import_local_binding_return(self):
        source = "import { External as return } from './External'\n" + self.source
        self.assertEqual(inventory_source(source)['status'], 'unknown')

    def test_constructor_is_not_an_ordinary_class_field(self):
        source = self.source.replace('export class IndexGateway {', "export class IndexGateway {\n  constructor: string = ''")
        self.assertEqual(inventory_source(source)['status'], 'unknown')


if __name__ == '__main__':
    unittest.main()
