# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from copy import copy,deepcopy
import hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from tools.agent_memory_runtime.query_ui_pair import pair_request,spelling_matches,bind_from_rows,retains_ui_pair,preserve_ui_pair,PairHandoff

Q='Locate the typography code for product tiles and price labels.'
class UIPairTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.project=SimpleNamespace(root=self.root,project_id='p');self.rows=[];self.files=[];self.anchors=[]
  for i,name in enumerate(['ProductTile','PriceLabel']):
   source=f'@Component\nstruct {name} {{\n build() {{ Text("hi") }}\n}}\n';path=name+'.ets';(self.root/path).write_text(source);digest=hashlib.sha256(source.encode()).hexdigest()
   r=dict(id=i*2+1,project_id='p',symbol_key=name,file_path=path,symbol=name,qualified_name=name,start_line=2,end_line=4,source_digest=digest,index_generation=1,symbol_type='component',owner_kind='component',owner_name='',evidence_class='static',semantic_adapter='arkts-static@1.2');m=dict(r,id=i*2+2,symbol_key=name+'.build',symbol='build',qualified_name=name+'.build',start_line=3,end_line=3,symbol_type='function',owner_name=name)
   self.rows.extend([r,m]);self.files.append(dict(file_path=path,source_digest=digest,index_generation=1));self.anchors.append(dict(file_path=path,symbol='build',symbol_type='function',start_line=3,end_line=3))
 def tearDown(self):self.tmp.cleanup()
 def bind(self,rows=None,anchors=None):return bind_from_rows(self.project,Q,{'code_anchors':self.anchors if anchors is None else anchors},self.rows if rows is None else rows,self.files)
 def valid(self,h,q=Q,anchors=None,path=None):return retains_ui_pair(h,self.anchors if anchors is None else anchors,q,path or {})
 def test_positive_method_and_components(self):
  h=self.bind();self.assertIsInstance(h,PairHandoff);self.assertTrue(self.valid(h));self.assertEqual(h,{'code_anchors':self.anchors})
  anchors=[dict(file_path=r['file_path'],symbol=r['symbol'],start_line=2,end_line=4)for r in self.rows if r['symbol_type']=='component'];self.assertTrue(self.valid(self.bind(anchors=anchors),anchors=anchors))
 def test_exact_plural_and_ambiguity(self):
  self.assertTrue(spelling_matches(('product','tiles'),'ProductTile'));self.assertTrue(spelling_matches(('price','labels'),'PriceLabel'));self.assertTrue(spelling_matches(('entry','policies'),'EntryPolicy'));self.assertFalse(spelling_matches(('entry','policied'),'EntryPolicy'));self.assertFalse(spelling_matches(('price','people'),'PricePerson'));self.assertFalse(spelling_matches(('tile',),'ProductTile'))
  other=dict(self.rows[0],id=50,symbol='ProductTiles',qualified_name='ProductTiles',symbol_key='other');self.assertNotIsInstance(self.bind(rows=[*self.rows,other]),PairHandoff)
 def test_full_grammar(self):
  self.assertIsNotNone(pair_request('Product tiles and price labels render inconsistent text sizes. Return both UI source contexts.'))
  self.assertIsNotNone(pair_request('Return both UI source contexts for product tiles and price labels.'))
  for q in [Q+' Extra.',Q+'\n',Q.replace('price labels','product tiles'),Q.replace('product tiles','"product tiles"'),Q.replace('product tiles','not product tiles'),Q.replace(' and price labels',' or price labels'),Q.replace(' and price labels',' and price labels and badges')]:self.assertIsNone(pair_request(q),q)
 def test_copies_and_json_cannot_authorize(self):
  h=self.bind()
  for c in [dict(h),copy(h),deepcopy(h),json.loads(json.dumps(h)),PairHandoff(h)]:self.assertFalse(self.valid(c))
 def test_mutations_legal_query_and_ranges_fail_closed(self):
  h=self.bind();self.assertFalse(self.valid(h,'Return both UI source contexts for product tiles and price labels.'));a=deepcopy(self.anchors);a[0]['end_line']=4;self.assertFalse(self.valid(h,anchors=a));h._proof=();self.assertFalse(self.valid(h))
 def test_state_only_missing_and_wrong_owner_refuse(self):
  self.assertNotIsInstance(self.bind(anchors=self.anchors[:1]),PairHandoff)
  rows=deepcopy(self.rows);rows[1]['owner_name']='Other';self.assertNotIsInstance(self.bind(rows=rows),PairHandoff)
  rows=deepcopy(self.rows);rows[1]['symbol_type']='state';self.assertNotIsInstance(self.bind(rows=rows),PairHandoff)
 def test_stale_digest_and_identity(self):
  (self.root/'ProductTile.ets').write_text('changed');self.assertNotIsInstance(self.bind(),PairHandoff)
 def test_invalid_identity_and_containment(self):
  for key,value in [('source_digest','bad'),('index_generation',None),('symbol_key',''),('end_line',2),('project_id','other')]:
   rows=deepcopy(self.rows);rows[0][key]=value;self.assertNotIsInstance(self.bind(rows=rows),PairHandoff,key)
 def test_path_log_guards(self):
  h=self.bind()
  for path in [{'activated':True},{'wrapped_log_evidence':True}]:self.assertFalse(self.valid(h,path=path))
 def test_unknown_unchanged(self):
  h={'code_anchors':self.anchors};self.assertIs(bind_from_rows(self.project,'Find one component.',h,self.rows,self.files),h)

 def test_legal_focus_with_both_owners_is_not_disabled(self):
  anchors=[*self.anchors,dict(self.anchors[0],symbol='extra')];h=self.bind(anchors=anchors)
  focused=deepcopy(self.anchors)
  self.assertIs(preserve_ui_pair(h,anchors,focused,Q,{}),focused)
  self.assertIs(preserve_ui_pair(h,anchors,focused[:1],Q,{}),anchors)
 def test_same_file_owner_ranges_not_just_path(self):
  source='@Component\nstruct ProductTile {\n build() {}\n}\n@Component\nstruct PriceLabel {\n build() {}\n}\n';(self.root/'Parts.ets').write_text(source);digest=hashlib.sha256(source.encode()).hexdigest()
  for i,r in enumerate(self.rows):
   r.update(file_path='Parts.ets',source_digest=digest)
   if i>=2:r['start_line']+=4;r['end_line']+=4
  self.files=[dict(file_path='Parts.ets',source_digest=digest,index_generation=1)]
  anchors=[dict(file_path='Parts.ets',symbol='build',start_line=n,end_line=n)for n in [3,7]]
  h=self.bind(anchors=anchors)
  self.assertIsInstance(h,PairHandoff)
  self.assertIs(preserve_ui_pair(h,anchors,anchors[:1],Q,{}),anchors)
  kept=deepcopy(anchors);self.assertIs(preserve_ui_pair(h,anchors,kept,Q,{}),kept)
