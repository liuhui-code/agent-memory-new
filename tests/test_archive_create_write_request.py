import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_archive_create_write_request import archive_create_write_request as accepts


class ArchiveRequestTests(unittest.TestCase):
    def test_heads(self):
        for verb in ['Find','Locate','Return']:
            for obj in ['source','implementation','owner','owners','ownership']:
                for prefix in ['','the ','temporary ','the temporary ']:
                    with self.subTest(verb=verb,obj=obj,prefix=prefix):
                        self.assertTrue(accepts(f'{verb} {prefix}archive creation and write {obj}.'))
                        self.assertTrue(accepts(f'{verb} {prefix}archive creation and write {obj}'.upper()))

    def test_context_orders(self):
        for article in ['A','An','The']:
            for existing in ['','existing ']:
                for domain in ['asset','resource','bundle']:
                    for state in ['is reused','remains available']:
                        self.assertTrue(accepts(f'{article} {existing}temporary archive {state} during {domain} extraction. Locate archive creation and write ownership.'))
                    self.assertTrue(accepts(f'{domain.title()} extraction reuses {article.lower()} {existing}temporary archive. Find archive creation and write source.'))

    def test_frozen_requests(self):
        root=Path(__file__).resolve().parents[1]
        p=json.loads((root/'tests/fixtures/archive_create_write.json').read_text())
        for case in p['cases']:
            with self.subTest(case=case['id']):
                # Unsupported source cohort still has an admissible request head.
                expected=case['proposed_authority'] or case['id']=='unsupported-head'
                self.assertEqual(bool(accepts(case['query'])),expected)

    def test_unknown_requests(self):
        head='Locate archive creation and write ownership.'
        for value in [None,1, head+' More.', ' '+head,head+' ',head+'\n',head.replace(' ','  ',1),
                      'Do not '+head, '"'+head+'"',head.replace(' and ',' or '),
                      head.replace('archive','PackageStager'),head+' Return logs.',
                      head.replace('creation and write','read'),head.replace('Locate','Identıfy'),
                      'A bad operation failed. '+head,head.replace(' ','\t',1),
                      '请定位创建和写入归档的源码。',head.replace('creation','creation,')]:
            with self.subTest(query=value): self.assertIsNone(accepts(value))


if __name__=='__main__': unittest.main()
