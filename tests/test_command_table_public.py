"""Frozen source/request inputs through real CLI; no private evidence dependency."""
import json,tempfile,unittest
from tests.command_table_test_support import P,prepare,ordinary,cli,snapshot_database,restore_database
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist

class TablePublic(unittest.TestCase):
 def test_eighteen_fixed_requests_and_atomic_code_view(self):
  cohorts=dict(P['cohorts']);cases=list(P['cases']);cohorts['valid_wrong_array']={'sources':P['wrong_array']}
  cases.append(dict(id='valid_wrong_array',cohort='valid_wrong_array',query=P['cases'][0]['query'],proposed_authority=False))
  count=0
  for cohort,description in cohorts.items():
   with tempfile.TemporaryDirectory()as t:
    project=prepare(t,sources=description['sources']);saved=snapshot_database(project)
    try:
     for case in [c for c in cases if c['cohort']==cohort]:
      with self.subTest(case=case['id']):
       q=case['query'];restore_database(project,saved);baseline,compact,pool=ordinary(project,q)
       restore_database(project,saved);raw=json.loads(cli(project,'context','--query',q,'--json'))
       restore_database(project,saved);candidate=json.loads(cli(project,'context','--query',q,'--compact','--json'))
       self.assertEqual(raw,baseline);self.assertLessEqual(candidate['output_budget']['estimated_tokens'],1500)
       if case['proposed_authority']:
        targets=['SyncMenu.ets']+(['SecondMenu.ets']if cohort=='two'else[]);anchors=candidate['query_handoff']['code_anchors']
        self.assertEqual({a['file_path']for a in anchors},set(targets));self.assertEqual(len(anchors),len(targets))
        self.assertTrue(all(a.get('symbol_type')in {'component','struct'}for a in anchors))
        for name in targets:
         self.assertTrue(any(e.get('content')=='\n'.join(description['sources'][name].splitlines()[1:])and e.get('truncated')is False for a in anchors if a['file_path']==name for e in a.get('source_excerpts',[])))
        self.assertEqual(restore_whitelist(candidate,compact),compact)
       else:self.assertEqual(candidate,compact)
      count+=1
    finally:saved.close()
  self.assertEqual(count,18)

if __name__=='__main__':unittest.main()
