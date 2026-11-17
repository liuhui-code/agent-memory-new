"""Frozen extension source controls only, not original/CLI/DB acceptance."""
import copy
import json
from pathlib import Path
import unittest

from tools.agent_memory_runtime.sql_slot_source import (
    inventory_source, classify_sql_owner, classify_ui_owner,
)
from tools.agent_memory_runtime.sql_slot_entity_join import entity_join

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = json.loads((ROOT / 'docs/evidence/sql-method-container/SOURCE-EXTENSION-CONTROLS.json').read_text())


def source_qualification(sources):
    inventories = {path: inventory_source(source) for path, source in sources.items()}
    if any(i['status'] != 'known' for i in inventories.values()):
        return {'status': 'unknown'}, None
    sql, ui = [], []
    request = CONTROLS['descriptor']
    for path, inventory in inventories.items():
        for owner in inventory['declarations']:
            a = classify_sql_owner(sources[path], owner, request['method'], request['sql_kind'])
            b = classify_ui_owner(sources[path], owner, request['method'], request['state'])
            if a['status'] != 'known' or b['status'] != 'known':
                return {'status': 'unknown'}, None
            sql.extend((path, m) for m in a['matches'])
            ui.extend((path, c) for c in b['chains'])
    # Frozen cases have one service and one page, never a ranking decision.
    if len(sql) != 1 or len(ui) != 1:
        return {'status': 'unknown'}, None
    args = (sql[0][0], sql[0][1], ui[0][0], ui[0][1], inventories, sources)
    return entity_join(*args), args


class SourceExtensionControls(unittest.TestCase):
    pass


def make_case_test(case):
    def test(self):
        result, _ = source_qualification(case['sources'])
        expected = 'known' if case['expected']['status'] == 'positive' else 'unknown'
        self.assertEqual(result['status'], expected, (case['purpose'], result))
        if expected == 'known':
            entity = result['entity']
            self.assertEqual(entity['name'], 'ArchiveLine')
            self.assertIn(entity['file_path'], case['sources'])
            self.assertEqual(entity['field_declaration']['type'], 'string')
            source = case['sources'][entity['file_path']]
            fieldspan = entity['field_span']
            self.assertIn(entity['field_declaration']['name'], source[fieldspan['start_offset']:fieldspan['end_offset']])
    return test


for case in CONTROLS['cases']:
    setattr(SourceExtensionControls, 'test_' + case['id'], make_case_test(case))


class EntityJoinAuthenticationControls(unittest.TestCase):
    def setUp(self):
        self.sources = copy.deepcopy(CONTROLS['cases'][0]['sources'])
        result, self.args = source_qualification(self.sources)
        self.assertEqual(result['status'], 'known', result)

    def test_string_string_has_no_entity(self):
        old = json.loads((ROOT / 'docs/evidence/sql-method-container/SOURCE-CONTROLS.json').read_text())['source_cases'][0]
        sources = old['sources']
        inventories = {p: inventory_source(s) for p, s in sources.items()}
        service = 'src/services/IndexGateway.ets'
        page = 'src/pages/IndexView.ets'
        match = classify_sql_owner(sources[service], inventories[service]['declarations'][0], 'findRows', 'LIKE')['matches'][0]
        chain = classify_ui_owner(sources[page], inventories[page]['declarations'][0], 'findRows', 'rows')['chains'][0]
        result = entity_join(service, match, page, chain, inventories, sources)
        self.assertEqual(result, {'status': 'known', 'entity': None})

    def test_legacy_untyped_sql_with_string_ui_preserved(self):
        old = json.loads((ROOT / 'docs/evidence/sql-method-container/SOURCE-CONTROLS.json').read_text())['source_cases'][0]
        sources = dict(old['sources'])
        service = 'src/services/IndexGateway.ets'
        page = 'src/pages/IndexView.ets'
        sources[service] = sources[service].replace('findRows(term: string): Promise<string[]>', 'findRows(term: string)')
        inventories = {p: inventory_source(s) for p, s in sources.items()}
        match = classify_sql_owner(sources[service], inventories[service]['declarations'][0], 'findRows', 'LIKE')['matches'][0]
        chain = classify_ui_owner(sources[page], inventories[page]['declarations'][0], 'findRows', 'rows')['chains'][0]
        self.assertIsNone(match['result_type'])
        self.assertIsNone(match['result_import'])
        self.assertEqual(entity_join(service, match, page, chain, inventories, sources),
                         {'status': 'known', 'entity': None})

    def test_legacy_untyped_sql_cannot_infer_object_from_ui_or_helper(self):
        sources = dict(self.sources)
        service = 'src/services/ArchiveReader.ets'
        sources[service] = sources[service].replace('scanLines(term: string): Promise<ArchiveLine[]>', 'scanLines(term: string)')
        inv = inventory_source(sources[service])
        result = classify_sql_owner(sources[service], inv['declarations'][0], 'scanLines', 'LIKE')
        self.assertEqual(result['status'], 'known')
        self.assertIsNone(result['matches'][0]['result_type'])
        joined, _ = source_qualification(sources)
        self.assertEqual(joined['status'], 'unknown')

    def test_mixed_string_object_is_unknown(self):
        sources = dict(self.sources)
        service = 'src/services/ArchiveReader.ets'
        sources[service] = sources[service].replace('Promise<ArchiveLine[]>', 'Promise<string[]>')
        result, _ = source_qualification(sources)
        self.assertEqual(result['status'], 'unknown')

    def test_source_mutation_without_new_inventory(self):
        args = list(self.args)
        args[-1] = dict(args[-1])
        name = next(p for p in args[-1] if '/entities/' in p)
        args[-1][name] += '// later change\n'
        self.assertEqual(entity_join(*args)['status'], 'unknown')

    def test_inventory_cannot_substitute_plain_owner_record(self):
        args = list(self.args)
        inventories = dict(args[-2])
        name = next(p for p in inventories if '/entities/' in p)
        inventories[name] = dict(inventories[name])
        inventories[name]['declarations'] = [dict(x) for x in inventories[name]['declarations']]
        args[-2] = inventories
        self.assertEqual(entity_join(*args)['status'], 'unknown')

    def test_entity_scope_not_extensible_by_annotation(self):
        args = list(self.args)
        name = next(p for p in self.sources if '/entities/' in p)
        args[-2] = {k: v for k, v in args[-2].items() if k != name}
        args[-1] = {k: v for k, v in args[-1].items() if k != name}
        self.assertEqual(entity_join(*args)['status'], 'unknown')

    def test_descriptor_field_tampering(self):
        args = list(self.args)
        args[3] = dict(args[3], render_field='code')
        self.assertEqual(entity_join(*args)['status'], 'unknown')


if __name__ == '__main__':
    unittest.main()
