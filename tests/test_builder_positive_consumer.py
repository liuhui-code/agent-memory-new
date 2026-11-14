# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from copy import deepcopy
import hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from tools.agent_memory_runtime.query_builder_selection import (
 declaration_request, bind_localization, project_builder_evidence, builder_anchors, MARKER)

class BuilderPositiveConsumerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.source=b'@Builder\nfunction part() { Text("part") }\n';(self.root/'Parts.ets').write_bytes(self.source)
  self.project=SimpleNamespace(root=self.root,project_id='project')
  self.row=dict(id=1,project_id='project',file_path='Parts.ets',symbol='part',symbol_key='key',qualified_name='part',start_line=2,end_line=2,source_digest=hashlib.sha256(self.source).hexdigest(),index_generation=1,symbol_type='function',evidence_class='static',semantic_adapter='arkts-static@1.2',callable_roles='["arkts_builder"]')
  self.query='Locate the declared Builder.'
 def tearDown(self):self.tmp.cleanup()
 def local(self,rows):
  return {'callable_candidates':[dict(r,symbol_id=r['id'])for r in rows]}
 def evidence(self,rows=None):
  rows=rows or [self.row];local=bind_localization(self.project,self.query,rows,rows,self.local(rows))
  return project_builder_evidence(local,{'primary':None,'alternatives':[]})
 def test_frozen_request_authority(self):
  p=json.loads((Path(__file__).resolve().parents[1]/'docs/evidence/builder-positive-consumer/protocol.json').read_text())
  for family in p['families']:
   for c in family['cases']:
    with self.subTest(c=c['id']):self.assertEqual(declaration_request(c['query']),c['authority'])
 def test_positive_private_projection_and_copy_rejection(self):
  evidence=self.evidence();anchors=[{'file_path':'Other.ets'}]
  result=builder_anchors(anchors,evidence,False,self.query)
  self.assertEqual(result[0]['symbol'],'part');self.assertEqual(evidence['certainty'],'uncertain')
  for copied in [dict(evidence),json.loads(json.dumps(evidence))]:self.assertEqual(builder_anchors(anchors,copied,False,self.query),anchors)
  self.assertEqual(builder_anchors(anchors,evidence,False,self.query+' extra'),anchors)
  evidence['primary']['symbol']='changed';self.assertEqual(builder_anchors(anchors,evidence,False,self.query),anchors)
 def test_unknown_and_partial_identity_fallback(self):
  for key,value in [('id',True),('source_digest',''),('symbol_key',''),('end_line',0),('index_generation',False),('semantic_adapter','unknown')]:
   row=dict(self.row);row[key]=value;original=self.local([row])
   self.assertIs(bind_localization(self.project,self.query,[row],[row],original),original)
  row=dict(self.row,callable_roles='[]');original=self.local([row]);self.assertIs(bind_localization(self.project,self.query,[row],[row],original),original)
 def test_stale_source_and_capacity_fallback(self):
  (self.root/'Parts.ets').write_bytes(self.source+b'// edit\n');original=self.local([self.row]);self.assertIs(bind_localization(self.project,self.query,[self.row],[self.row],original),original)
  (self.root/'Parts.ets').write_bytes(self.source)
  rows=[dict(self.row,id=i,symbol='part'+str(i),symbol_key='key'+str(i),qualified_name='part'+str(i))for i in range(1,5)];original=self.local(rows)
  self.assertIs(bind_localization(self.project,self.query,rows,rows,original),original)
  self.assertIs(bind_localization(self.project,self.query,[self.row],[],original),original)
 def test_multiple_known_and_unknown_not_absence(self):
  other=dict(self.row,id=2,symbol='second',symbol_key='key2',qualified_name='second')
  unknown=dict(self.row,id=3,symbol='third',symbol_key='key3',qualified_name='third',callable_roles='[]')
  evidence=self.evidence([self.row,other,unknown]);self.assertEqual(evidence[MARKER]['known_matches'],2)
  self.assertEqual([a['symbol']for a in builder_anchors([],evidence,False,self.query)],['part','second'])
  self.assertFalse(evidence[MARKER]['behavior_certified']);self.assertEqual(evidence['certainty'],'uncertain')
 def test_graph_path_identity_protection(self):
  evidence=self.evidence()
  for key in ['graph_neighbor','graph_relation','identity_match','log_identity_match']:
   anchors=[{'file_path':'Other.ets',key:True}];self.assertEqual(builder_anchors(anchors,evidence,False,self.query),anchors)
  anchors=[{'file_path':'Other.ets'}];self.assertEqual(builder_anchors(anchors,evidence,True,self.query),anchors)
 def test_original_query_not_cleaned(self):
  from tools.agent_memory_runtime.query_language import positive_retrieval_query
  query='Locate the declared Builder, do not return Builder.'
  self.assertFalse(declaration_request(query));self.assertTrue(declaration_request(positive_retrieval_query(query).strip(' ,')))
  original=self.local([self.row]);self.assertIs(bind_localization(self.project,query,[self.row],[self.row],original),original)
