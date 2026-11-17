"""Learned independent log coexistence; no saved output or evaluator import."""
import json,tempfile,unittest
from pathlib import Path
from copy import copy,deepcopy
from unittest.mock import patch
from tests.archive_create_write_test_support import cli
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context,_compact_context
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.query_touch_index_selection import TouchIndexContext,touch_index_receipt,compact_touch_index

P=json.loads((Path(__file__).parent/'fixtures/touch_log_coexistence.json').read_text())
class TouchLogSelectionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.projects={}
  for world,sources in P['sources'].items():
   root=Path(cls.tmp.name)/world;root.mkdir();source=root/'source';source.mkdir()
   for name,text in sources.items():
    path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
   project=resolve_project(str(source),str(root/'memory'));cli(project,'init');cli(project,'learn-path','--path','.','--json');cls.projects[world]=project
 def data(self,ident):
  case=next(c for c in P['cases']if c['id']==ident)
  return case,build_context_facade(self.projects[case['cohort']]).execute(case['query'])
 def test_real_log_positive_set_and_full_whitelist(self):
  for ident in ('one-direct-observed-indexed','one-depth1-observed-indexed','one-depth2-observed-indexed','two-depth2-observed-indexed','strong-observation-event-direct-indexed'):
   with self.subTest(ident=ident):
    case,data=self.data(ident);self.assertIsInstance(data,TouchIndexContext)
    baseline=_compact_context(dict(data));result=compact_context(data)
    self.assertEqual(restore_whitelist(result,baseline),baseline)
    self.assertEqual(result['query_handoff']['log_anchors'],baseline['query_handoff']['log_anchors'])
    self.assertLessEqual(result['output_budget']['estimated_tokens'],1500)
    anchors=result['query_handoff']['code_anchors']
    self.assertEqual({a['file_path']for a in anchors},{a['file']for a in case['expected_callbacks']})
    for expected in case['expected_callbacks']:
     self.assertTrue(any(a['file_path']==expected['file'] and any(e['start_line']<=expected['start_line'] and e['end_line']>=expected['end_line'] and not e['truncated'] for e in a['source_excerpts']) for a in anchors))
 def test_strong_event_and_unsupported_request_never_gain_permission(self):
  for ident in ('strong-observation-event-observed-indexed','unsupported-explicit-owner'):
   _,data=self.data(ident);self.assertNotIsInstance(data,TouchIndexContext)
 def test_receipt_copies_changed_candidates_and_graph_path(self):
  _,data=self.data('one-depth2-observed-indexed');self.assertIsInstance(data,TouchIndexContext)
  self.assertIsNone(touch_index_receipt(copy(data)));self.assertIsNone(touch_index_receipt(deepcopy(data)))
  original=data._trial._baseline_logs;data._trial._baseline_logs=None
  try:self.assertIsNone(touch_index_receipt(data))
  finally:data._trial._baseline_logs=original
  self.assertIsNotNone(touch_index_receipt(data))
  old=data['query_handoff']['path_context'];data['query_handoff']['path_context']={'activated':True,'path_candidates':[]}
  try:self.assertIsNone(touch_index_receipt(data))
  finally:data['query_handoff']['path_context']=old
 def test_tiny_budget_and_repeated_presentation_account_once(self):
  with patch('tools.agent_memory_runtime.query_results.record_context_use')as use,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
   _,data=self.data('two-depth2-observed-indexed');self.assertIsInstance(data,TouchIndexContext)
   self.assertEqual(use.call_count,1);self.assertEqual(miss.call_count,1)
   self.assertEqual(compact_context(data),compact_context(data))
   tiny=_compact_context(dict(data));tiny['output_budget']['target_tokens']=100
   self.assertIs(compact_touch_index(data,tiny),tiny)
   self.assertEqual(use.call_count,1);self.assertEqual(miss.call_count,1)
