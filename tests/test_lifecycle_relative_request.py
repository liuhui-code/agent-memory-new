import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_lifecycle_english_request import english_lifecycle_request as accepts


class LifecycleRelativeRequestTests(unittest.TestCase):
    def test_frozen_twenty_one(self):
        rows=json.loads((Path(__file__).resolve().parents[1]/'tests/fixtures/lifecycle_relative_requests.json').read_text())
        self.assertEqual(len(rows),21)
        for row in rows:
            with self.subTest(case=row['id']):self.assertEqual(accepts(row['query']),row['accepted'])

    def test_compositional_forms_and_that_owns(self):
        for relation in ['combining','owning','that combines','that owns']:
            for command in ['Find','Locate','Return']:
                for owner in ['owner','coordinator']:
                    head=f'{command} the {owner} {relation} lifecycle restore, state update, and persistence.'
                    self.assertTrue(accepts(head))
                    self.assertTrue(accepts('Restart loses the saved working copy; '+head))
                    for article in ['A','The']:
                        for state in ['resets','is cleared']:
                            for event in ['relaunch','restart']:
                                self.assertTrue(accepts(f'{article} saved working copy {state} after {event}. '+head))
                    self.assertTrue(accepts('a SAVED working copy RESETS AFTER RELAUNCH. '+head.upper()))

    def test_original_byte_np_and_scope_refusals(self):
        head='Locate the owner that combines lifecycle restore, state update, and persistence.'
        for np in ['draft','working copy','a b c d','x'*24]:self.assertTrue(accepts('A saved '+np+' resets after relaunch. '+head))
        for np in ['BufferSession','bufferSession','PendingQueue.append','source','both owners','not text','code','restore','a b c d e','x'*25,'é','a_b','text\ncopy']:
            with self.subTest(np=np):self.assertFalse(accepts('A saved '+np+' resets after relaunch. '+head))
        query='A saved draft resets after relaunch. '+head
        for bad in [query+' ',query+'\n',' '+query,query.replace('. ','.\n'),query.replace(' and ',' or '),query.replace('the owner','both owners'),query+' Also show logs.',query+' except WriteQueue.','"'+query+'"',query.replace('Locate','Generate'),query.replace('Locate','Do not locate'),query.replace('that combines','which combines'),query.replace('that combines','that combine'),query.replace('resets','was changed'),query.replace('after','before'),'A saved draft resets after relaunch; '+head,query.replace('draft','x'*241)]:
            with self.subTest(query=bad):self.assertFalse(accepts(bad))

    def test_published_inputs_keep_identical_classification(self):
        rows=json.loads((Path(__file__).resolve().parents[1]/'tests/fixtures/lifecycle_english_requests.json').read_text())
        for row in rows:
            with self.subTest(case=row['id']):self.assertEqual(accepts(row['query']),row['english'])

if __name__=='__main__':unittest.main()
