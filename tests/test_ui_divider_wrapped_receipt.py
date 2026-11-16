"""Normal synthetic learn/query plus private receipt mutation controls."""
from copy import copy,deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.archive_create_write_test_support import cli,snapshot_database,restore_database
from tools.agent_memory_runtime.storage import resolve_project,connect
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.query_ui_divider_selection import DividerContext,bind_divider_context,divider_receipt,compact_divider,enrich_divider
P=json.loads((Path(__file__).parent/'fixtures/ui_divider_wrapped.json').read_text())

class WrappedDividerReceipt(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.samples={};cls.projects={};cls.saved={}
  for cohort,sources in P['sources'].items():
   root=Path(cls.tmp.name)/cohort/'source';root.mkdir(parents=True)
   for name,body in sources.items():
    f=root/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(body)
   project=resolve_project(str(root),str(root.parent/'memory'));cli(project,'init');cli(project,'learn-path','--path','.','--json')
   cls.projects[cohort]=project;cls.saved[cohort]=snapshot_database(project);cls.addClassCleanup(cls.saved[cohort].close)
   captures=[]
   def observe(_p,_q,data,pool):captures.append((deepcopy(data),deepcopy(pool)));return data
   with patch('tools.agent_memory_runtime.query_ui_divider_selection.bind_divider_context',side_effect=observe):
    raw=build_context_facade(project).execute(P['queries'][cohort]);baseline=compact_context(raw)
   assert len(captures)==1
   cls.samples[cohort]=(deepcopy(dict(raw)),baseline,captures[0][1])
 def setUp(self):
  for cohort,p in self.projects.items():restore_database(p,self.saved[cohort])
 def bind(self,cohort='static'):
  raw,baseline,pool=deepcopy(self.samples[cohort]);p=self.projects[cohort]
  data=bind_divider_context(p,P['queries'][cohort],raw,pool)
  self.assertIsInstance(data,DividerContext);self.assertTrue(data._log_provenance)
  return p,data,baseline
 def test_real_static_and_inferred_preserve_logs(self):
  for cohort in P['sources']:
   _,data,baseline=self.bind(cohort);self.assertIsNotNone(divider_receipt(data))
   out=compact_divider(data,baseline);self.assertEqual(restore_whitelist(out,baseline),baseline)
   # Capacity remains a real guard, not a reason to discard preserved logs.
   if out!=baseline:
    self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
    self.assertEqual([x['read_window']for x in out['query_handoff']['code_anchors']],[dict(start_line=3,end_line=7),dict(start_line=11,end_line=15)])
 def test_graph_revision_drift(self):
  p,d,b=self.bind()
  with connect(p)as db:db.execute('UPDATE graph_runtime_state SET graph_revision=graph_revision+1');db.commit()
  self.assertIsNone(divider_receipt(d));self.assertIs(compact_divider(d,b),b)
 def test_effect_drift(self):
  p,d,b=self.bind()
  with connect(p)as db:db.execute("UPDATE code_log_effects SET message_template='changed'");db.commit()
  self.assertIsNone(divider_receipt(d))
 def test_retired_edge(self):
  p,d,b=self.bind()
  with connect(p)as db:db.execute("UPDATE memory_edges SET valid_to='retired' WHERE relation='emits_log'");db.commit()
  self.assertIsNone(divider_receipt(d))
 def test_raw_log_add_remove_change(self):
  for mode in ('add','remove','change'):
   _,d,b=self.bind();logs=d['query_handoff']['log_anchors']
   if mode=='add':logs.append(deepcopy(logs[0]))
   elif mode=='remove':logs.pop()
   else:logs[0]['message_template']='changed'
   self.assertIsNone(divider_receipt(d))
 def test_copy_no_authority_and_snapshot_mutation(self):
  _,d,b=self.bind();self.assertIsNone(divider_receipt(copy(d)));self.assertIsNone(divider_receipt(deepcopy(d)))
  d._log_provenance+=' ';self.assertIsNone(divider_receipt(d))
 def test_enrich_carries_identical_witness(self):
  _,d,b=self.bind();result=enrich_divider(d,d['query'],d['query_handoff']['path_context'],d['source_freshness'])
  self.assertIsInstance(result,DividerContext);self.assertEqual(result._log_provenance,d._log_provenance);self.assertIsNotNone(divider_receipt(result))
 def test_full_query_guard_and_budget_remain(self):
  _,d,b=self.bind();protected=deepcopy(dict(d));protected['query_handoff']['path_context']['activated']=True
  raw,_,pool=deepcopy(self.samples['static'])
  self.assertIs(bind_divider_context(self.projects['static'],P['queries']['static'],protected,pool),protected)
  b['output_budget']['target_tokens']=1;self.assertIs(compact_divider(d,b),b)
