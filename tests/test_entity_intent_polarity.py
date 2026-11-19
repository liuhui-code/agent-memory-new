import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_code_selection import behavior_owner_query, entity_definition_query

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/eval/fixtures/system-capability'
FILES = ('src/entities/ProductRecord.ets','src/pages/ProductSearchPage.ets','src/services/ProductSearchService.ets')

class EntityIntentPolarityTests(AgentMemoryTestBase):
    def test_negative_behavior_does_not_grant_entity_suppression(self):
        for q in ('Locate ProductRecord fields. Do not return page handlers.',
                  'Locate ProductRecord fields, not page handlers.',
                  'Locate ProductRecord fields; exclude ProductSearchPage.',
                  '定位 ProductRecord 字段，不要返回页面。'):
            with self.subTest(q=q):self.assertFalse(behavior_owner_query(q))

    def test_entity_polarity_and_unknown_clauses(self):
        self.assertTrue(entity_definition_query('Locate entity definition and fields.'))
        self.assertFalse(entity_definition_query('Locate page implementation, not entity definition.'))
        self.assertTrue(behavior_owner_query('Locate page implementation, not entity definition.'))
        for q in ('Locate fields, not only page handlers.',
                  "Don't return merely page handlers.",
                  'Locate fields, not entity but also page handlers.',
                  'Locate fields with literal "not page handlers".'):
            with self.subTest(q=q):self.assertTrue(behavior_owner_query(q))

    def test_public_negated_page_preserves_requested_entity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in FILES:
                file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes((FIXTURE/name).read_bytes())
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            for suffix in ('', '. Do not return page handlers.', ', not page handlers.'):
                for mode in ([],['--compact']):
                    data=json.loads(self.run_memory(root,'context','--query','Locate ProductRecord fields'+suffix,'--json',*mode).stdout)
                    self.assertEqual(FILES[0],data['query_handoff']['code_anchors'][0]['file_path'])
            data=json.loads(self.run_memory(root,'context','--query','Locate the SQL parameter owner and page that renders product search results.','--json').stdout)
            self.assertNotIn(FILES[0],{a['file_path']for a in data['query_handoff']['code_anchors']})
