from copy import deepcopy
import json,tempfile,unittest
from pathlib import Path
from tests.command_table_test_support import prepare,ordinary
from tools.agent_memory_runtime.query_command_table_selection import bind_command_table_context,CommandTableContext,command_table_receipt,compact_command_table
from tools.agent_memory_runtime.query_command_table_scope import metadata_frames
from tools.agent_memory_runtime.query_command_table_roles import protected_table_scope
from tools.agent_memory_runtime.storage import connect
P=json.loads((Path(__file__).parent/'fixtures/command_table_scope.json').read_text())
Q='Return the UI action-to-method dispatch table.'

class CertifiedScope(unittest.TestCase):
 def test_frozen_independent_cases(self):
  for case in P['cases']:
   with self.subTest(case=case['id']),tempfile.TemporaryDirectory()as t:
    project=prepare(t,sources=P['cohorts'][case['cohort']]['sources']);base,compact,pool=ordinary(project,case['query'])
    receipt=bind_command_table_context(project,case['query'],base,pool);out=compact_command_table(receipt,compact)
    self.assertEqual(out is not compact,case['proposed_authority'])
    if out is not compact:
     evidence=out['query_handoff']['callable_evidence']
     self.assertEqual(evidence['certification_scope'],'non_exhaustive_recalled_component_frames')
     self.assertEqual(evidence['boundary'],'certified_static_ui_tables_only_not_exhaustive_or_unique')
 def test_metadata_double_corruption_cannot_hide_callback(self):
  with tempfile.TemporaryDirectory()as t:
   project=prepare(t);base,compact,pool=ordinary(project,Q)
   for row in pool:
    if row.get('signature','').startswith('callback'):
     row['signature']='ordinary()';row['qualified_name']='SyncMenu.ordinary'
   self.assertIs(bind_command_table_context(project,Q,base,pool),base)
 def test_known_nonmatch_digest_and_scope_binding(self):
  with tempfile.TemporaryDirectory()as t:
   project=prepare(t,sources=P['cohorts']['scope_index']['sources']);base,compact,pool=ordinary(project,Q)
   r=bind_command_table_context(project,Q,base,pool);self.assertIsInstance(r,CommandTableContext)
   self.assertEqual(r._scope['qualified_frame_count'],2)
   r._scope['unverified_path_count']=0;self.assertIsNone(command_table_receipt(r))
   r=bind_command_table_context(project,Q,base,pool)
   path=project.root/'GesturePad.ets';path.write_text(path.read_text()+'\n')
   self.assertIsNone(command_table_receipt(r));self.assertIs(bind_command_table_context(project,Q,base,pool),base)
 def test_partial_frames_and_true_protections(self):
  with tempfile.TemporaryDirectory()as t:
   project=prepare(t,sources=P['cohorts']['scope_index']['sources']);base,compact,pool=ordinary(project,Q)
   for removed in [r for r in pool if r['file_path']=='GesturePad.ets'and(r['kind']=='file'or r.get('symbol')=='build')]:
    subset=[r for r in pool if r is not removed]
    self.assertIsNone(metadata_frames(project,subset))
   for flag in ['identity_match','log_identity_match','graph_neighbor','graph_relation']:
    changed=deepcopy(pool);changed[0][flag]=True
    self.assertTrue(protected_table_scope(base,Q,changed))
   for key,value in [('activated',True),('seeds',[{}]),('path_candidates',[{}]),('wrapped_log_evidence',True)]:
    changed=deepcopy(base);changed['query_handoff']['path_context'][key]=value
    self.assertTrue(protected_table_scope(changed,Q,pool))

 def test_all_metadata_frames_counted_not_topk(self):
  sources=dict(P['cohorts']['base']['sources']);template=sources.pop('SyncMenu.ets')
  for i in range(13):sources[f'Menu{i}.ets']=template.replace('SyncMenu',f'Menu{i}')
  with tempfile.TemporaryDirectory()as t:
   project=prepare(t,sources=sources)
   with connect(project)as db:
    pool=[dict(r,kind='file')for r in db.execute('SELECT * FROM code_files')]
    pool += [dict(r,kind='symbol')for r in db.execute('SELECT * FROM code_symbols')]
   self.assertIsNone(metadata_frames(project,pool))
   reduced=[r for r in pool if r['file_path']!='Menu12.ets']
   self.assertEqual(len(metadata_frames(project,reduced)['frames']),12)
   self.assertEqual(len(metadata_frames(project,list(reversed(reduced)))['frames']),12)
 def test_many_nonframes_do_not_consume_frame_cap(self):
  sources=dict(P['cohorts']['base']['sources'])
  for i in range(14):sources[f'View{i}.ets']='@Component\nexport struct View'+str(i)+' {\n  build() {\n    Text("Status")\n  }\n}\n'
  with tempfile.TemporaryDirectory()as t:
   project=prepare(t,sources=sources);base,compact,_=ordinary(project,Q)
   with connect(project)as db:
    pool=[dict(r,kind='file')for r in db.execute('SELECT * FROM code_files')]
    pool += [dict(r,kind='symbol')for r in db.execute('SELECT * FROM code_symbols')]
   frames=metadata_frames(project,pool);self.assertEqual(len(frames['frames']),1)
   r=bind_command_table_context(project,Q,base,pool);self.assertIsInstance(r,CommandTableContext)
   self.assertGreater(r._scope['unverified_path_count'],12)
 def test_event_frame_cannot_hide_unrecalled_property_table(self):
  sources=dict(P['cohorts']['base']['sources'])
  sources['SyncMenu.ets']=sources['SyncMenu.ets'].replace('    Column() {',"    Column() {\n      Button('Extra').onClick(() => {\n        this.worker.stopSync()\n      })")
  with tempfile.TemporaryDirectory()as t:
   project=prepare(t,sources=sources);base,compact,_=ordinary(project,Q)
   with connect(project)as db:
    pool=[dict(r,kind='file')for r in db.execute('SELECT * FROM code_files')]
    pool += [dict(r,kind='symbol')for r in db.execute("SELECT * FROM code_symbols WHERE symbol != 'run'")]
   self.assertEqual(len(metadata_frames(project,pool)['frames']),1)
   self.assertIs(bind_command_table_context(project,Q,base,pool),base)

 def test_active_identifier_escape_is_unknown_not_negative_certificate(self):
  from tools.agent_memory_runtime.command_table_frame_source import certify_frame
  with tempfile.TemporaryDirectory()as t:
   project=prepare(t);base,compact,pool=ordinary(project,Q)
   frame=metadata_frames(project,pool)['frames'][0];source=(project.root/frame['path']).read_text()
   self.assertIsInstance(certify_frame(source,frame),dict)
   for changed in [source.replace('ForEach',r'For\u0045ach'),source.replace('ForEach',r'For\u{45}ach')]:
    self.assertIs(certify_frame(changed,frame),False)
   self.assertIsInstance(certify_frame(source+'\n// For\\u0045ach is a comment\n',frame),dict)

 def test_multiline_plain_quote_cannot_hide_consumer(self):
  from tools.agent_memory_runtime.command_table_frame_source import certify_frame,known_frame_quotes
  with tempfile.TemporaryDirectory()as t:
   project=prepare(t);base,compact,pool=ordinary(project,Q)
   frame=metadata_frames(project,pool)['frames'][0];source=(project.root/frame['path']).read_text()
   for quote in ("'",'"'):
    changed=source.replace('      ForEach(', '      '+quote+'ForEach(').replace('      })','      })'+quote)
    self.assertIs(certify_frame(changed,frame),False)
   self.assertTrue(known_frame_quotes("// ' comment\n/* ' more\n comment */\nconst s = `multiline\ntext`;"))
   self.assertFalse(known_frame_quotes("const s = 'multiline\ntext';"))

 def test_negative_certificate_masks_only_valid_string_and_comment_tokens(self):
  from tools.agent_memory_runtime.command_table_frame_source import certify_frame
  with tempfile.TemporaryDirectory()as t:
   project=prepare(t,sources=P['cohorts']['scope_index']['sources']);base,compact,pool=ordinary(project,Q)
   frame=next(f for f in metadata_frames(project,pool)['frames']if f['owner']['symbol']=='GesturePad')
   source=(project.root/frame['path']).read_text()
   for replacement in ["'ForEach'",r"'For\u0045ach'",'`ForEach`']:
    self.assertIsNone(certify_frame(source.replace("'Slide'",replacement),frame))
   self.assertIsNone(certify_frame(source+'\n// For\\u0045ach and ForEach\n',frame))
   self.assertIs(certify_frame(source.replace("'Slide'",'`${unknown()}`'),frame),False)

if __name__=='__main__':unittest.main()
