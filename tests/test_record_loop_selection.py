from copy import copy,deepcopy
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.agent_memory_runtime.query_record_loop_selection import (bind_record_loop_context,RecordLoopContext,record_loop_receipt,enrich_record_loop,compact_record_loop)
from tools.agent_memory_runtime.query_record_loop_request import record_loop_request
D=Path(__file__).resolve().parents[1]/'docs/evidence/record-loop-contract'
class Rows:
 def __init__(self,s,f):self.s,self.f=s,f
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def execute(self,sql,args):return self.s if 'FROM code_symbols' in sql else self.f
class RecordLoopSelectionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  p=json.loads((D/'POSITIVE-ONLY-PROTOCOL.json').read_text())['cohorts'][1]
  for name,source in p['sources'].items():(self.root/name).write_text(source)
  r=next(r for r in json.loads((D/'stage-c-merge-public.json').read_text()) if r['cohort']==p['id'] and r['case']['id']=='contextual-result')
  self.base=deepcopy(r['raw']);self.compact=deepcopy(r['compact']);self.query=r['case']['query'];self.base['project_path']=str(self.root)
  trace=json.loads((D/'stage-c-merge-trace-two-positive-result-contextual-result-compact.json').read_text())
  self.pool=trace[0]['gated']['matches']['wiki_matches']
  index=next(r for r in json.loads((D/'stage-c-merge-index.json').read_text())if r['cohort']==p['id'])
  self.rows=index['symbols'];self.files=index['files'];self.project=SimpleNamespace(root=self.root,project_id=self.base['project_id'])
 def bind(self):
  with patch('tools.agent_memory_runtime.query_record_loop_selection.connect',return_value=Rows(self.rows,self.files)):
   return bind_record_loop_context(self.project,self.query,self.base,self.pool)
 def test_request_closed_and_source_name_protected(self):
  self.assertEqual(record_loop_request(self.query),'result')
  self.assertEqual(record_loop_request('Locate the record iteration and accumulator implementation.'),'accumulator')
  for q in ['Do not '+self.query,'"'+self.query+'"',self.query+' Also find logs.',self.query.replace('message fragments','only fragments')]:self.assertIsNone(record_loop_request(q))
  self.query=self.query.replace('message fragments','chunkassembler');self.base['query']=self.query
  self.assertIsNotNone(record_loop_request(self.query));self.assertIs(self.bind(),self.base)
 def test_positive_all_and_copy_mutation(self):
  r=self.bind();self.assertIsInstance(r,RecordLoopContext);self.assertEqual(dict(r),self.base)
  self.assertEqual([a['file_path']for a in r._anchors],['ChunkAssembler.ts','FragmentSelector.ts'])
  self.assertTrue(all(a['symbol_type']=='function' for a in r._anchors))
  for c in [dict(r),copy(r),deepcopy(r),json.loads(json.dumps(r))]:self.assertIsNone(record_loop_receipt(c))
  r._anchors[0]['record_ids']=[999];self.assertIsNone(record_loop_receipt(r))
 def test_identity_entire_tuple_and_source_change(self):
  original=deepcopy(self.rows)
  for field,value in [('id',0),('qualified_name','Other.assemble'),('owner_name','Other'),('owner_kind','Other'),('semantic_adapter','unknown'),('evidence_class','unknown'),('source_digest','0'*64),('index_generation',99),('symbol_type','class'),('start_line',3)]:
   self.rows=deepcopy(original);next(r for r in self.rows if r['symbol']=='assemble')[field]=value
   self.assertIs(self.bind(),self.base,field)
  self.rows=original;(self.root/'ChunkAssembler.ts').write_text('unsupported changed file')
  self.assertIs(self.bind(),self.base)
 def test_protection_and_freshness(self):
  initial=deepcopy(self.base)
  for k in ['activated','wrapped_log_evidence','path_candidates','seeds']:
   self.base=deepcopy(initial);self.base['query_handoff']['path_context'][k]=True
   self.assertIs(self.bind(),self.base,k)
  for k in ['identity_match','log_identity_match','graph_neighbor','graph_relation']:
   self.base=deepcopy(initial);self.base['query_handoff']['code_anchors']=[{k:True}]
   self.assertIs(self.bind(),self.base,k)
  self.base=deepcopy(initial);r=self.bind()
  self.assertIsInstance(enrich_record_loop(r,self.query,self.base['query_handoff']['path_context'],self.base['source_freshness']),RecordLoopContext)
  stale=dict(self.base['source_freshness'],status='stale')
  self.assertNotIsInstance(enrich_record_loop(r,self.query,self.base['query_handoff']['path_context'],stale),RecordLoopContext)
 def test_snapshot_and_log_preserving_transaction(self):
  r=self.bind();before=deepcopy(dict(r));(self.root/'ChunkAssembler.ts').write_text('later change')
  result=compact_record_loop(r,self.compact)
  self.assertEqual(dict(r),before);self.assertEqual(result['query_handoff']['log_anchors'],self.compact['query_handoff']['log_anchors'])
  self.assertEqual([a['file_path']for a in result['query_handoff']['code_anchors']],['ChunkAssembler.ts','FragmentSelector.ts'])
  self.assertIn('merged = merged + chunk',result['query_handoff']['code_anchors'][0]['source_excerpts'][0]['content'])
