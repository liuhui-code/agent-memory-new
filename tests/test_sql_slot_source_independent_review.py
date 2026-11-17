"""Independent source-proof counterexamples, not original-case or CLI runs."""
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.sql_slot_source import inventory_source, classify_sql_owner, classify_ui_owner

CORPUS = Path(__file__).resolve().parents[1] / 'docs/evidence/sql-method-container/SOURCE-CONTROLS.json'

class SourceProofReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads(CORPUS.read_text())['source_cases'][0]
        cls.service = cls.case['sources']['src/services/IndexGateway.ets']
        cls.ui = cls.case['sources']['src/pages/IndexView.ets']

    def classify(self, source, role):
        inventory = inventory_source(source)
        if inventory['status'] == 'unknown':
            return inventory
        owner = inventory['declarations'][0]
        return (classify_sql_owner(source, owner, 'findRows', 'LIKE') if role == 'sql'
                else classify_ui_owner(source, owner, 'findRows', 'rows'))

    def test_sql_awaitthis_is_different_receiver_not_await_this(self):
        source = self.service.replace('return this.execute', 'return awaitthis.execute')
        self.assertEqual(self.classify(source, 'sql')['status'], 'unknown')

    def test_ui_awaitthis_is_different_receiver_not_await_this(self):
        source = self.ui.replace('= await this.gateway', '= awaitthis.gateway')
        self.assertEqual(self.classify(source, 'ui')['status'], 'unknown')

    def test_return_linebreak_has_automatic_semicolon(self):
        source = self.service.replace('return this.execute', 'return\n    this.execute')
        self.assertEqual(self.classify(source, 'sql')['status'], 'unknown')

    def test_receiver_factory_name_is_not_new_expression(self):
        source = self.ui.replace('new IndexGateway()', 'newIndexGateway()')
        self.assertEqual(self.classify(source, 'ui')['status'], 'unknown')

    def test_computed_receiver_write_in_other_method(self):
        source = self.ui.replace('  build() {', '  change() { this["gateway"] = new IndexGateway() }\n\n  build() {')
        self.assertEqual(self.classify(source, 'ui')['status'], 'unknown')

    def test_owner_alias_can_write_receiver(self):
        source = self.ui.replace('  build() {', '  change() { const self = this; self.gateway = new IndexGateway() }\n\n  build() {')
        self.assertEqual(self.classify(source, 'ui')['status'], 'unknown')

    def test_owner_escape_can_write_receiver(self):
        source = self.ui.replace('  build() {', '  change() { Object.assign(this, { gateway: new IndexGateway() }) }\n\n  build() {')
        self.assertEqual(self.classify(source, 'ui')['status'], 'unknown')

    def test_unicode_line_separator_cannot_hide_same_slot_declaration(self):
        source = '@Component\nexport struct Other {\n  // comment\u2028 @State rows: string[] = []\n  build() {}\n}\n'
        inventory = inventory_source(source)
        if inventory['status'] == 'known':
            result = classify_ui_owner(source, inventory['declarations'][0], 'findRows', 'rows')
            self.assertEqual(result['status'], 'unknown')

    def test_receiver_alias_in_other_field_initializer(self):
        source = self.ui.replace('  async submit()', '  private alias: IndexGateway = this.gateway\n\n  async submit()')
        self.assertEqual(self.classify(source, 'ui')['status'], 'unknown')

if __name__ == '__main__':
    unittest.main()
