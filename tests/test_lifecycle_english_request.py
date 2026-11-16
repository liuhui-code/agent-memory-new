import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_lifecycle_english_request import english_lifecycle_request
from tools.agent_memory_runtime.query_lifecycle_selection import lifecycle_request


class EnglishLifecycleRequestTests(unittest.TestCase):
    def test_frozen_inputs(self):
        cases=json.loads((Path(__file__).resolve().parents[1]/'tests/fixtures/lifecycle_english_requests.json').read_text())
        self.assertEqual(len(cases),19)
        for case in cases:
            with self.subTest(case=case['id']):
                self.assertEqual(english_lifecycle_request(case['query']),case['english'])
                self.assertEqual(lifecycle_request(case['query']),case['lifecycle'])

    def test_complete_compositional_head(self):
        for verb in ['Find','Locate','Return']:
            for owner in ['owner','coordinator']:
                for relation in ['combining','owning']:
                    for restore in ['lifecycle restore','restore lifecycle']:
                        for state in ['current state','current text state','state update']:
                            for commit in ['storage commit','persistence']:
                                query=f'{verb} the {owner} {relation} {restore}, {state}, and {commit}'
                                self.assertTrue(english_lifecycle_request(query))
                                self.assertTrue(english_lifecycle_request(query.upper()+'.'))

    def test_observation_is_not_an_owner_selector(self):
        head='return the coordinator owning restore lifecycle, current state, and storage commit.'
        for label in ['scratch buffer','written notes','editor text','a b c d','x'*24]:
            self.assertTrue(english_lifecycle_request('Restart loses the saved '+label+'; '+head))
        for label in ['BufferSession','x'*25,'a b c d e','editor.text','editor_text','code','restore','both owners','saved and text','not text','literal','editor\ntext','é']:
            self.assertFalse(english_lifecycle_request('Restart loses the saved '+label+'; '+head))

    def test_unknown_and_full_consumption(self):
        head='Return the coordinator owning restore lifecycle, current state, and storage commit.'
        for query in [None,3,' '+head,head+' ',head+'\n',head+' Also show logs.',head.replace(', and ',', or '),head.replace(', and ',' and '),'"'+head+'"',head.replace('Return','Generate'),'Do not '+head,head.replace('the coordinator','both coordinators'),head+' except WriteQueue.',head+' after restart.',head.replace('restore lifecycle','lifecycle'),'unrelated; '+head,'Restart loses the saved text; '+head+'x'*240]:
            with self.subTest(query=query):self.assertFalse(english_lifecycle_request(query))

if __name__=='__main__':unittest.main()
