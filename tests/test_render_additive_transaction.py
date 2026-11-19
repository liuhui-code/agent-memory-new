from copy import deepcopy
from pathlib import Path
import json,sqlite3,subprocess,sys,tempfile,time,unittest
from unittest.mock import patch
from tools.agent_memory_runtime.render_additive_transaction import qualify,append_passages,finalize
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.receiver_empty_transaction import EmptyReceiverSession,defer_accounting
R=Path(__file__).resolve().parents[1]
P=json.loads((R/'docs/releases/render-additive-source-20261119/protocol.json').read_text())['cases'][0]
# The frozen public protocol is duplicated in the release before publication.
class RenderAdditiveTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)/'source';self.root.mkdir();self.home=Path(self.t.name)/'memory'
  for f,s in P['sources'].items():(self.root/f).write_text(s)
  self.cli('init');self.cli('learn-path','--path',str(self.root));self.project=resolve_project(str(self.root),str(self.home));self.q=P['queries'][0]['query']
  self.cli('update','--type','semantic','--fact','Bulletin UI rendering cleanup.','--source','fixture')
 def tearDown(self):self.t.cleanup()
 def cli(self,*args):
  p=subprocess.run([sys.executable,'-B',str(R/'tools/agent_memory.py'),*args,'--project',str(self.root),'--memory-home',str(self.home)],capture_output=True,text=True);self.assertEqual(0,p.returncode,p.stderr);return json.loads(p.stdout)if '--json'in args else p.stdout
 def count(self):
  with sqlite3.connect(next(self.home.glob('projects/*/memory.db')))as c:return c.execute('select sum(use_count) from semantic_facts').fetchone()[0] or 0
 def test_public_addition_and_accounting_once_raw_unchanged(self):
  before=self.count();raw=self.cli('context','--query',self.q,'--json');self.assertEqual(before+1,self.count())
  out=self.cli('context','--query',self.q,'--json','--compact');self.assertEqual(before+2,self.count())
  a=out['query_handoff']['code_anchors'];self.assertEqual(['BulletinDetailsStore.ets','BulletinDetails.ets'],[x['file_path']for x in a]);self.assertEqual([(7,13),(15,19)],[(x['start_line'],x['end_line'])for x in a[1]['source_excerpts']]);self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
  self.assertNotIn('source_snapshot',raw['query_handoff']['code_anchors'][0])
 def raw_and_receipts(self):
  raw=self.cli('context','--query',self.q,'--json');receipts=qualify(self.project,raw,time.monotonic()+2);self.assertTrue(receipts)
  from tools.agent_memory_runtime.context_compact import compact_context
  return raw,receipts,compact_context(raw)
 def test_all_old_evidence_and_metadata_unchanged(self):
  raw,receipts,base=self.raw_and_receipts();candidate,members=append_passages(base,receipts);self.assertTrue(members)
  restored=deepcopy(candidate);h=restored['query_handoff'];h['code_anchors']=base['query_handoff']['code_anchors'];h['source_excerpt_policy']=base['query_handoff']['source_excerpt_policy'];restored['output_budget']=base['output_budget'];self.assertEqual(base,restored)
  self.assertEqual(base['query_handoff']['code_anchors'],candidate['query_handoff']['code_anchors'][:len(base['query_handoff']['code_anchors'])])
 def test_complete_existing_body_noop_and_unknown_source(self):
  raw,receipts,base=self.raw_and_receipts();out=self.cli('context','--query',self.q,'--json','--compact','--compact-token-budget','2000','--preserve-selected-source-anchors');self.assertIs(out,append_passages(out,receipts)[0])
  path=self.root/'BulletinDetails.ets';path.write_text(path.read_text().replace('Text(this.cleanedBody())','Text(this.markup)'));self.assertIsNone(qualify(self.project,raw,time.monotonic()+2))
 def test_budget_and_excerpt_cap_are_atomic(self):
  raw,receipts,base=self.raw_and_receipts()
  for change in ('budget','cap'):
   b=deepcopy(base)
   if change=='budget':b['correction_guards']=[{'body':'x'*5000}]
   else:b['query_handoff']['code_anchors']*=3
   self.assertIs(b,append_passages(b,receipts)[0])
 def test_second_auth_change_and_deadline_fail_closed(self):
  raw,receipts,base=self.raw_and_receipts()
  with patch('tools.agent_memory_runtime.render_additive_transaction.qualify',side_effect=[receipts,None]):self.assertIs(base,finalize(self.project,raw,base)[0])
  self.assertIsNone(qualify(self.project,raw,time.monotonic()-1))
 def test_multiple_positive_near_name_and_unknown_are_not_excluded(self):
  src=P['sources']['BulletinDetails.ets'];(self.root/'BulletinRecordPreview.ets').write_text(src.replace('BulletinDetails','BulletinRecordPreview'))
  (self.root/'Unknown.ets').write_text('export class Unknown { delegate() { return external() } }')
  self.cli('learn-path','--path',str(self.root));raw=self.cli('context','--query',self.q,'--json')
  # Qualification is bounded by supplied recalled identities, not a whole-repo claim.
  with sqlite3.connect(next(self.home.glob('projects/*/memory.db')))as c:
   raw['wiki_matches']=[{'file_path':x[0]}for x in c.execute('select file_path from code_files')]
  receipts=qualify(self.project,raw,time.monotonic()+2);self.assertEqual({'BulletinDetails.ets','BulletinRecordPreview.ets'},{x['file']['file_path']for x in receipts})
  from tools.agent_memory_runtime.context_compact import compact_context
  base=compact_context(raw);base['output_budget']['target_tokens']=2000
  candidate,members=append_passages(base,receipts)
  self.assertIsNot(candidate,base)
  self.assertEqual({'BulletinDetails.ets','BulletinRecordPreview.ets'},{m['file_path']for m in members})
  for receipt in receipts:
   excerpts=[e for a in candidate['query_handoff']['code_anchors']if a['file_path']==receipt['file']['file_path']for e in a.get('source_excerpts',[])]
   self.assertTrue(all(any(e['start_line']<=r['start_line']<=r['end_line']<=e['end_line']for e in excerpts)for r in receipt['members']))
 def test_direct_context_and_failed_commit_remain_once(self):
  from tools.agent_memory_runtime.query_results import limited_context
  before=self.count();limited_context(self.project,self.q);self.assertEqual(before+1,self.count())
  raw,receipts,base=self.raw_and_receipts()
  with patch('tools.agent_memory_runtime.query_results.record_context_use')as use,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty',side_effect=RuntimeError('commit failure'))as miss:
   with self.assertRaises(RuntimeError):
    with EmptyReceiverSession(self.project,self.q,allow_render=True)as session:
     defer_accounting(self.project,self.q,raw);session.finalize(base)
   self.assertEqual(1,use.call_count);self.assertEqual(1,miss.call_count)
 def test_partial_same_file_is_separate_anchor_not_mutation(self):
  raw,receipts,base=self.raw_and_receipts();receipt=receipts[0];row=receipt['members'][0]
  span=dict(symbol=row['symbol'],start_line=row['start_line'],end_line=row['end_line'])
  visible=dict(file_path=row['file_path'],record_ids=[row['id']],record_type='code_symbol',source_ranges=[span],read_window=dict(start_line=row['start_line'],end_line=row['end_line']),source_excerpts=[dict(span,content='\n'.join(receipt['lines'][row['start_line']-1:row['end_line']]),source='current_worktree',truncated=False)])
  base['query_handoff']['code_anchors'].append(visible);base['output_budget']['target_tokens']=2000;original=deepcopy(base)
  out,members=append_passages(base,receipts);self.assertIsNot(out,base)
  self.assertEqual(original,base);self.assertEqual(base['query_handoff']['code_anchors'],out['query_handoff']['code_anchors'][:-1])
  self.assertEqual({'start_line':15,'end_line':19},out['query_handoff']['code_anchors'][-1]['read_window'])
  capped=deepcopy(base);capped['query_handoff']['code_anchors'].append(deepcopy(capped['query_handoff']['code_anchors'][0]))
  self.assertIs(capped,append_passages(capped,receipts)[0])
 def test_owner_kind_parent_and_source_bounds_fail_closed(self):
  raw=self.cli('context','--query',self.q,'--json')
  db=next(self.home.glob('projects/*/memory.db'))
  for field,value in [('owner_kind','store'),('owner_name','Other'),('start_line',1),('end_line',200)]:
   with sqlite3.connect(db)as c:
    old=c.execute('SELECT '+field+" FROM code_symbols WHERE symbol='BulletinDetails'").fetchone()[0]
    c.execute('UPDATE code_symbols SET '+field+"=? WHERE symbol='BulletinDetails'",(value,))
   self.assertIsNone(qualify(self.project,raw,time.monotonic()+2))
   with sqlite3.connect(db)as c:c.execute('UPDATE code_symbols SET '+field+"=? WHERE symbol='BulletinDetails'",(old,))
 def test_empty_output_is_outside_nonempty_addition_contract(self):
  raw,receipts,base=self.raw_and_receipts();base['query_handoff']['code_anchors']=[]
  self.assertIs(base,append_passages(base,receipts)[0])
 def test_once_attempt_on_exception_and_no_raw_capture(self):
  raw,receipts,base=self.raw_and_receipts()
  with patch('tools.agent_memory_runtime.query_results.record_context_use')as use,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
   with EmptyReceiverSession(self.project,self.q):self.assertFalse(defer_accounting(self.project,self.q,raw))
   with self.assertRaises(ValueError):
    with EmptyReceiverSession(self.project,self.q,allow_render=True):
     self.assertTrue(defer_accounting(self.project,self.q,raw));raise ValueError('render failed')
   self.assertEqual(1,use.call_count);self.assertEqual(1,miss.call_count)
 def test_legacy_render_context_keeps_once_accounting(self):
  (self.root/'BulletinDetailsStore.ets').unlink();self.cli('learn-path','--path',str(self.root));before=self.count()
  out=self.cli('context','--query','Return the UI rendering cleanup owner.','--json','--compact');self.assertEqual(before+1,self.count());self.assertTrue(out['query_handoff']['code_anchors']);self.assertTrue(any(e['source']=='validated_request_snapshot'for a in out['query_handoff']['code_anchors']for e in a.get('source_excerpts',[])))
if __name__=='__main__':unittest.main()
