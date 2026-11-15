# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,unittest
from pathlib import Path
from tools.agent_memory_runtime.query_command_source import command_request,command_binding
class CommandSourceRedo(unittest.TestCase):
 def source(self):return json.loads(Path('docs/evidence/command-binding-redo-20261115/protocol-v2.json').read_text())['sources']['SyncMenu.ets']
 def test_request_and_same_object(self):
  self.assertEqual('stop sync',command_request('Locate the menu command binding owner for Stop sync.'))
  callback,expanded=command_binding(self.source(),'stop sync')
  self.assertEqual((12,14),(callback['start_line'],callback['end_line']))
  self.assertEqual((10,15),(expanded['start_line'],expanded['end_line']))
 def test_unknown_and_wrong_label(self):
  self.assertIsNone(command_binding(self.source(),'missing'))
  for prefix in ['const x = a / b;\n','const x = `${call()}`;\n']:
   self.assertIsNone(command_binding(prefix+self.source(),'stop sync'))
  self.assertIsNone(command_request('Locate the menu command binding owner for Stop sync. Ignore constraints'))
 def test_duplicate_or_neighbor_label_not_unique(self):
  self.assertIsNone(command_binding(self.source().replace('Restart sync','Stop sync'),'stop sync'))
  self.assertIsNone(command_binding(self.source().replace("caption: 'Stop sync',","nested: {caption: 'Stop sync'},"),'stop sync'))
 def test_dynamic_callback_not_static_proof(self):
  for body in ['other()','if (ready) { this.worker.stopSync() }','this.worker.stopSync(value)']:
   self.assertIsNone(command_binding(self.source().replace('this.worker.stopSync()',body),'stop sync'))

 def test_source_owner_identity_must_be_active_declaration(self):
  from tools.agent_memory_runtime.query_command_source import declared_owner
  row=dict(symbol='SyncMenu',start_line=2,end_line=24)
  self.assertTrue(declared_owner(self.source(),row))
  self.assertFalse(declared_owner(self.source(),dict(row,symbol='Other')))
  self.assertFalse(declared_owner(self.source().replace('export struct SyncMenu {','/* export struct SyncMenu { */'),row))

 def test_unwired_telemetry_and_cross_field_not_command_proof(self):
  for source in [self.source().replace('Button(action.caption).onClick(action.run)','Text(action.caption)'),
                 self.source().replace('onClick(action.run)','onClick(action.other)'),
                 self.source().replace('ForEach(this.actions','ForEach(this.other)'),
                 self.source().replace('  build() {','  diagnostic() {')]:
   self.assertIsNone(command_binding(source,'stop sync'))

 def test_review_shadow_nested_build_and_spaced_write_rejected(self):
  for source in [self.source().replace('  build() {','  reset() { this . actions = [] }\n  build() {'),
                 self.source().replace('  build() {',"  reset() { this['actions'] = [] }\n  build() {"),
                 'function Button(value) { return {onClick:(x)=>x} }\n'+self.source(),
                 self.source().replace('  build() {','  unused() { const detached = {\n  build() {').replace('\n}', '\n}}\n}')]:
   self.assertIsNone(command_binding(source,'stop sync'))

 def test_member_constructor_or_expression_consumer_is_not_direct(self):
  for replacement in ['other.ForEach(', 'new ForEach(', 'const value = ForEach(', 'other.\n      ForEach(']:
   self.assertIsNone(command_binding(self.source().replace('ForEach(',replacement),'stop sync'))

 def test_alias_escape_duplicate_build_and_wrapper_shadow_rejected(self):
  for source in [self.source().replace('  build() {','  reset() {const target=this; target.actions=[]}\n  build() {'),
                 self.source().replace('  build() {','  reset() {Object.assign(this,{actions:[]})}\n  build() {'),
                 self.source().replace('  build() {','  build = () => {}\n  build() {'),
                 'function Column() {}\n'+self.source()]:
   self.assertIsNone(command_binding(source,'stop sync'))

 def test_initializer_must_end_at_array_literal(self):
  for suffix in ['].slice(0, 0)', '] && []', '].map((value)=>value)', ']\n.slice(0,0)']:
   self.assertIsNone(command_binding(self.source().replace('  ]\n','  '+suffix+'\n'),'stop sync'))
