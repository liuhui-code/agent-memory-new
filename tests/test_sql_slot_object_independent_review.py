"""Independent extension review controls; source-only, no CLI/DB calls."""
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.sql_slot_source import inventory_source, classify_sql_owner


class ObjectExtensionReview(unittest.TestCase):
    def test_legacy_string_sql_binding_without_return_annotation_is_preserved(self):
        corpus=Path(__file__).resolve().parents[1]/'docs/evidence/sql-method-container/SOURCE-CONTROLS.json'
        case=json.loads(corpus.read_text())['source_cases'][0]
        source=next(s for p,s in case['sources'].items() if '/services/' in p)
        source=source.replace('async findRows(term: string): Promise<string[]>',
                              'async findRows(term: string)')
        owner=inventory_source(source)['declarations'][0]
        result=classify_sql_owner(source,owner,'findRows','LIKE')
        # Legacy certifies SQL parameter syntax, not an object result type.
        self.assertEqual(result['status'],'known')
        self.assertEqual(len(result['matches']),1)

    def test_legacy_non_object_annotation_spelling_preserved(self):
        corpus=Path(__file__).resolve().parents[1]/'docs/evidence/sql-method-container/SOURCE-CONTROLS.json'
        case=json.loads(corpus.read_text())['source_cases'][0]
        original=next(s for p,s in case['sources'].items() if '/services/' in p)
        for annotation in ('Promise<Array<string>>', 'string[]'):
            with self.subTest(annotation=annotation):
                source=original.replace('async findRows(term: string): Promise<string[]>',
                                        'async findRows(term: string): '+annotation)
                owner=inventory_source(source)['declarations'][0]
                result=classify_sql_owner(source,owner,'findRows','LIKE')
                self.assertEqual(result['status'],'known')
                self.assertEqual(len(result['matches']),1)

    def test_unknown_annotation_final_join_string_only(self):
        from tools.agent_memory_runtime.sql_slot_source import classify_ui_owner
        from tools.agent_memory_runtime.sql_slot_entity_join import entity_join
        root=Path(__file__).resolve().parents[1]/'docs/evidence/sql-method-container'
        old=json.loads((root/'SOURCE-CONTROLS.json').read_text())['source_cases'][0]
        for annotation in ('Promise<Array<string>>', 'string[]', 'CustomResult'):
            with self.subTest(annotation=annotation):
                sources=dict(old['sources']);service='src/services/IndexGateway.ets';page='src/pages/IndexView.ets'
                sources[service]=sources[service].replace('findRows(term: string): Promise<string[]>',
                                                         'findRows(term: string): '+annotation)
                inventories={p:inventory_source(v) for p,v in sources.items()}
                match=classify_sql_owner(sources[service],inventories[service]['declarations'][0],'findRows','LIKE')['matches'][0]
                chain=classify_ui_owner(sources[page],inventories[page]['declarations'][0],'findRows','rows')['chains'][0]
                self.assertIsNone(match['result_type'])
                self.assertIsNone(match['result_import'])
                self.assertEqual(entity_join(service,match,page,chain,inventories,sources),
                                 {'status':'known','entity':None})

    def test_unknown_annotation_final_join_object_rejects(self):
        from test_sql_slot_source_extension import source_qualification
        root=Path(__file__).resolve().parents[1]/'docs/evidence/sql-method-container'
        original=json.loads((root/'SOURCE-EXTENSION-CONTROLS.json').read_text())['cases'][0]['sources']
        for annotation in ('Promise<Array<ArchiveLine>>', 'ArchiveLine[]', 'CustomResult'):
            with self.subTest(annotation=annotation):
                sources=dict(original);service='src/services/ArchiveReader.ets'
                sources[service]=sources[service].replace('scanLines(term: string): Promise<ArchiveLine[]>',
                                                         'scanLines(term: string): '+annotation)
                owner=inventory_source(sources[service])['declarations'][0]
                local=classify_sql_owner(sources[service],owner,'scanLines','LIKE')
                self.assertEqual(local['status'],'known')
                self.assertIsNone(local['matches'][0]['result_type'])
                self.assertEqual(source_qualification(sources)[0]['status'],'unknown')


if __name__=='__main__':unittest.main()
