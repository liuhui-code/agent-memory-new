import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from tools.agent_memory_runtime.record_loop_source import parse_record_loop
from tools.agent_memory_runtime.callable_behavior_hints import callable_behavior_hints
from tools.agent_memory_runtime.code_wiki_extractors import summarize_file

ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/'docs/evidence/record-loop-contract/POSITIVE-ONLY-PROTOCOL.json').read_text())
S=P['cohorts'][1]['sources']
BODY="assemble(chunks: string[]): string {\n let merged = ''\n for (const chunk of chunks) {\n  merged = merged + chunk\n }\n return merged\n}"

class RecordLoopSourceTests(unittest.TestCase):
 def test_frozen_positives_unknowns(self):
  for name in ['ChunkAssembler.ts','FragmentSelector.ts']:
   self.assertIsNotNone(parse_record_loop(S[name],whole_class=True),name)
  for name in ['AfterIteration.ts','DeferredAssembly.ts']:
   self.assertIsNone(parse_record_loop(S[name],whole_class=True),name)
  original=(ROOT/'docs/eval/fixtures/system-capability/src/sharing/SharedRecordCollector.ets').read_text()
  self.assertIsNotNone(parse_record_loop(original,whole_class=True))

 def test_append_overwrite_member_converter_branch(self):
  for expression,mode in [('merged + chunk','append'),('chunk','overwrite'),('chunk.content','overwrite'),('this.convert(chunk.content)','overwrite')]:
   source=BODY.replace('merged + chunk',expression)
   self.assertEqual(parse_record_loop(source)['update_form'],mode)
  self.assertEqual(parse_record_loop(BODY.replace('merged = merged + chunk','merged += chunk'))['update_form'],'append')
  source=BODY.replace('merged = merged + chunk',"if (chunk.kind === 'markup') { merged = this.convert(chunk.content) } else { merged = chunk.content }")
  self.assertIsNotNone(parse_record_loop(source))

 def test_complete_body_unknown_scope_and_identity(self):
  bad=[BODY.replace('return merged','return chunks'),BODY.replace('const chunk','const merged'),
       BODY.replace('of chunks','of other'),BODY.replace('merged = merged + chunk','queueMicrotask(() => { merged = chunk })'),
       BODY.replace('merged = merged + chunk','let merged = chunk'),
       BODY.replace('merged = merged + chunk','merged = chunk; break'),
       BODY.replace('merged = merged + chunk','merged = chunk; return merged'),
       BODY.replace('merged = merged + chunk','merged = chunk["content"]'),
       BODY.replace('merged = merged + chunk','merged = /text/.test(chunk)'),
       BODY.replace("let merged = ''",'let merged = `${chunks}`'),
       BODY.replace('merged = merged + chunk',"if (chunk.kind === 'x') { merged = chunk.content }"),
       BODY+' trailing',BODY[:-1]]
  for source in bad:self.assertIsNone(parse_record_loop(source),source)

 def test_asi_comments_and_operator_boundaries(self):
  self.assertIsNotNone(parse_record_loop(BODY.replace("let merged = ''","let merged = ''; // init").replace('merged = merged + chunk','merged += chunk;')))
  self.assertIsNotNone(parse_record_loop(BODY.replace('return merged','return /* inline */ merged')))
  for source in [BODY.replace('return merged','return\nmerged'),BODY.replace('return merged','return /*\n*/ merged'),BODY.replace('merged = merged + chunk','merged + = chunk'),BODY.replace('merged = merged + chunk','merged = chunk\n + chunk'),BODY.replace("let merged = ''","let merged = '' + 'prefix'"),BODY.replace('merged = merged + chunk','merged = chunk; ignored()')]:
   self.assertIsNone(parse_record_loop(source),source)

 def test_whole_class_is_not_partial_positive(self):
  base=S['ChunkAssembler.ts']
  for extra in ['private count: number = 0','other() { unknown() }',BODY]:
   source=base[:-2]+'\n'+extra+'\n}\n'
   self.assertIsNone(parse_record_loop(source,whole_class=True))
  source=base[:-2]+" label(): string { return 'text only' }\n}\n"
  self.assertIsNotNone(parse_record_loop(source,whole_class=True))

 def test_hint_interfaces_and_non_target_language(self):
  for suffix in ['.ts','.ets']:
   entity=SimpleNamespace(name='assemble',file_path='Unit'+suffix)
   self.assertIn('collectionfold',callable_behavior_hints(entity,BODY))
   self.assertNotIn('collectionfold',callable_behavior_hints(entity,BODY.replace('return merged','return chunks')))
  self.assertNotIn('collectionfold',callable_behavior_hints(SimpleNamespace(name='assemble',file_path='Unit.java'),BODY))
  with tempfile.TemporaryDirectory() as temp:
   for name,source in S.items():
    p=Path(temp)/name;p.write_text(source)
    self.assertEqual('collectionfold'in summarize_file(p,'TypeScript'),name in ['ChunkAssembler.ts','FragmentSelector.ts'])

 def test_quoted_syntax_crlf_and_bare_cr(self):
  for newline in ['\r\n','\r']:
   self.assertIsNotNone(parse_record_loop(BODY.replace('\n',newline)))
  for source in [BODY.replace('for (',"'for' ("),BODY.replace('return merged',"return 'merged'"),BODY.replace('merged = merged + chunk',"merged '+= ' chunk"),BODY.replace('of chunks',"of 'chunks'")]:
   self.assertIsNone(parse_record_loop(source))
  self.assertIsNone(parse_record_loop(BODY.replace("let merged = ''","let merged = 'for (const fake of chunks) { merged = fake }' ")+" trailing"))

 def test_entity_source_span_and_method_name_alignment(self):
  from tools.agent_memory_runtime.semantic_symbol_evidence import method_evidence_payload
  lines=S['ChunkAssembler.ts'].splitlines()
  entity=SimpleNamespace(name='assemble',file_path='ChunkAssembler.ts',kind='method',start_line=2,end_line=8)
  self.assertIn('collectionfold',method_evidence_payload(entity,lines)[0])
  entity.end_line=7
  self.assertNotIn('collectionfold',method_evidence_payload(entity,lines)[0])
  entity.end_line=8;entity.start_line=3
  self.assertNotIn('collectionfold',method_evidence_payload(entity,lines)[0])
  entity.start_line=2;entity.name='other'
  self.assertNotIn('collectionfold',method_evidence_payload(entity,lines)[0])

if __name__=='__main__':unittest.main()
