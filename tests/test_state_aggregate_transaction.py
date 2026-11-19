from copy import deepcopy
from pathlib import Path
import json,sqlite3,subprocess,sys,tempfile,time,unittest
from unittest.mock import patch
from tools.agent_memory_runtime.state_aggregate_transaction import request,finalize,allowed_candidates
from tools.agent_memory_runtime.receiver_empty_transaction import EmptyReceiverSession,defer_accounting,inventory,authenticate
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.context_compact import compact_context
R=Path(__file__).resolve().parents[1];D=R/'docs/releases/state-aggregate-reading-20261119'
P=json.loads((D/'protocol.json').read_text())['cases'][0];Q=P['queries'][1]['query']
class StateAggregateTransactionTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)/'source';self.root.mkdir();self.home=Path(self.t.name)/'memory'
  for f,s in P['sources'].items():(self.root/f).write_text(s)
  self.cli('init');self.cli('learn-path','--path',str(self.root));self.project=resolve_project(str(self.root),str(self.home))
 def tearDown(self):self.t.cleanup()
 def cli(self,*args):
  p=subprocess.run([sys.executable,'-B',str(R/'tools/agent_memory.py'),*args,'--project',str(self.root),'--memory-home',str(self.home)],capture_output=True,text=True);self.assertEqual(0,p.returncode,p.stderr);return json.loads(p.stdout)if '--json'in args else p.stdout
 def base(self):
  raw=self.cli('context','--query',Q,'--json');return raw,compact_context(raw,token_budget=2000,preserve_selected_source_anchors=True)
 def test_public_optin_only(self):
  for flags in [[],['--compact'],['--compact','--compact-token-budget','2000']]:
   d=self.cli('context','--query',Q,'--json',*flags);self.assertEqual([],d['query_handoff']['code_anchors'])
  d=self.cli('context','--query',Q,'--json','--compact','--compact-token-budget','2000','--preserve-selected-source-anchors');a=d['query_handoff']['code_anchors'];self.assertEqual(1,len(a));self.assertEqual('WarehouseAccumulator.ets',a[0]['file_path']);self.assertEqual((5,10),(a[0]['source_excerpts'][0]['start_line'],a[0]['source_excerpts'][0]['end_line']))
 def test_finite_request_controls(self):
  p=json.loads((D/'prefix-controls.json').read_text())
  for q in p['positive']:self.assertTrue(request(q),q)
  for q in p['negative']:self.assertFalse(request(q),q)
 def test_state_binding_rejects_mutations_and_stale_source(self):
  raw,base=self.base();state=inventory(self.project)
  self.assertTrue(authenticate(self.project,raw,state,state_bound=True))
  f=self.root/'WarehouseAccumulator.ets';source=f.read_text()
  for before,after in [('@State total','total'),('@State total','@State other'),('@State total','// @State total'),('@State total','@Observed total'),('this.total += row.quantity','queueMicrotask(() => { this.total += row.quantity })'),('this.total +=','total +='),('  build() { Text(`${this.total}`) }','  total() {}\n  build() { Text(`${this.total}`) }')]:
   f.write_text(source.replace(before,after));self.cli('learn-path','--path',str(self.root));r,b=self.base();self.assertIs(b,finalize(self.project,r,b)[0])
  f.write_text(source);self.cli('learn-path','--path',str(self.root));raw,base=self.base();f.write_text(source+'\n');self.assertIs(base,finalize(self.project,raw,base)[0])
 def test_two_all_and_three_or_overfile_fallback(self):
  s=P['sources']['WarehouseAccumulator.ets'];(self.root/'Second.ets').write_text(s.replace('WarehouseAccumulator','Second'));self.cli('learn-path','--path',str(self.root));raw,base=self.base();out,m=finalize(self.project,raw,base);self.assertEqual(2,len(m));self.assertEqual(2,len(out['query_handoff']['code_anchors']))
  (self.root/'Third.ets').write_text(s.replace('WarehouseAccumulator','Third'));self.cli('learn-path','--path',str(self.root));raw,base=self.base();self.assertIs(base,finalize(self.project,raw,base)[0])
 def test_candidate_scope_exact_identity_not_file_only(self):
  raw,base=self.base();state=inventory(self.project);row=next(r for r in state[1]if r['file_path']=='WarehouseAccumulator.ets'and r['symbol']=='refresh')
  c=dict(file_path=row['file_path'],owner_name=row['owner_name'],owner_kind=row['owner_kind'],symbol=row['symbol'],source_range=dict(start_line=row['start_line'],end_line=row['end_line'],selection_reason='callable_symbol_range'))
  raw['query_handoff']['code_anchors']=[{'file_path':'WarehouseList.ets'}];raw['query_handoff']['callable_evidence']=dict(primary=c,alternatives=[])
  allowed=allowed_candidates(raw);self.assertTrue(authenticate(self.project,raw,inventory(self.project,paths=[row['file_path']]),state_bound=True,allowed=allowed))
  c['symbol']='build';allowed=allowed_candidates(raw);self.assertIsNone(authenticate(self.project,raw,inventory(self.project,paths=[row['file_path']]),state_bound=True,allowed=allowed))
 def test_second_validation_and_deadline(self):
  raw,base=self.base();qualified=authenticate(self.project,raw,inventory(self.project),state_bound=True)
  with patch('tools.agent_memory_runtime.receiver_empty_transaction.authenticate',side_effect=[qualified,None]):self.assertIs(base,finalize(self.project,raw,base)[0])
  self.assertIsNone(authenticate(self.project,raw,inventory(self.project),time.monotonic()-1,state_bound=True))
 def test_nonempty_append_preserves_every_old_object(self):
  raw,base=self.base();state=inventory(self.project);qualified=authenticate(self.project,raw,state,state_bound=True);row=qualified[1][0]
  old={'file_path':'WarehouseList.ets','source_excerpts':[],'unknown':'retained'};base['query_handoff']['code_anchors']=[old];base['query_handoff']['source_excerpt_policy']=dict(source='current_worktree',body_persisted=False,excerpt_count=0,excerpt_chars=0)
  raw['query_handoff']['code_anchors']=[old];raw['query_handoff']['callable_evidence']=dict(primary=dict(file_path=row['file_path'],symbol=row['symbol'],owner_name=row['owner_name'],owner_kind=row['owner_kind'],source_range=dict(start_line=row['start_line'],end_line=row['end_line'],selection_reason='callable_symbol_range')),alternatives=[])
  out,m=finalize(self.project,raw,base);self.assertTrue(m);self.assertEqual(out['query_handoff']['code_anchors'][0],old);self.assertEqual(out['query_handoff']['code_anchors'][1]['role'],'supporting')
  restored=deepcopy(out);restored['query_handoff']['code_anchors']=base['query_handoff']['code_anchors'];restored['query_handoff']['source_excerpt_policy']=base['query_handoff']['source_excerpt_policy'];restored['output_budget']=base['output_budget'];self.assertEqual(base,restored)
  base['correction_guards']=[{'body':'x'*8000}];self.assertIs(base,finalize(self.project,raw,base)[0])
 def test_final_accounting_and_failure_once(self):
  raw,base=self.base()
  with patch('tools.agent_memory_runtime.query_results.record_context_use')as use,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
   with EmptyReceiverSession(self.project,Q,allow_aggregate=True)as session:
    self.assertTrue(defer_accounting(self.project,Q,raw));out=session.finalize(base);self.assertTrue(out['query_handoff']['code_anchors'])
   self.assertEqual(1,use.call_count);self.assertEqual(1,miss.call_count);self.assertTrue(miss.call_args.args[-1]['query_handoff']['code_anchors'])
  with patch('tools.agent_memory_runtime.query_results.record_context_use',side_effect=RuntimeError('failed'))as use:
   with self.assertRaises(RuntimeError):
    with EmptyReceiverSession(self.project,Q,allow_aggregate=True)as session:
     self.assertTrue(defer_accounting(self.project,Q,raw));session.finalize(base)
   self.assertEqual(1,use.call_count)

 def test_empty_display_must_not_erase_nonempty_callable_evidence(self):
  raw,base=self.base();state=inventory(self.project);row=next(r for r in state[1]if r['file_path']=='WarehouseAccumulator.ets'and r['symbol']=='refresh')
  evidence=dict(primary=dict(file_path=row['file_path'],symbol=row['symbol'],owner_name=row['owner_name'],owner_kind=row['owner_kind'],source_range=dict(start_line=row['start_line'],end_line=row['end_line'],selection_reason='callable_symbol_range')),alternatives=[])
  raw['query_handoff']['code_anchors']=[{'file_path':row['file_path']}];raw['query_handoff']['callable_evidence']=deepcopy(evidence)
  base['query_handoff']['callable_evidence']=deepcopy(evidence);before=deepcopy(base)
  out,members=finalize(self.project,raw,base);self.assertIs(out,base);self.assertEqual(members,[]);self.assertEqual(base,before)
