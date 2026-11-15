# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile
from pathlib import Path
from agent_memory_test_base import AgentMemoryTestBase
from test_output_loop_source_rebuild import SOURCE
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.query_collect import collect_matches_with_audit
from tools.agent_memory_runtime.query_output_loop_selection import qualify_output_loop

QUERY='Locate output iteration and accumulation ownership.'
class OutputLoopPublicTests(AgentMemoryTestBase):
 def run_case(self,sources,query=QUERY):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);root=Path(temporary.name)
  for name,source in sources.items():(root/name).write_text(source)
  self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
  project=resolve_project(str(root),str(self.memory_home(root)))
  items=collect_matches_with_audit(project,query).matches['wiki_matches']
  authority=qualify_output_loop(project,query,items)
  compact=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)
  return authority,compact
 def test_multiple_positive_owners_not_unique_gate(self):
  # Independent ordinary learn-path, rather than mocked duplicate rows.
  second=SOURCE.replace('PacketCollector','TextCollector').replace('pieces','segments').replace('item','line')
  authority,result=self.run_case({'PacketCollector.ts':SOURCE,'TextCollector.ts':second},'Locate command output iteration and accumulation ownership when the process line reader has data.')
  self.assertEqual(len(authority._receipts),2)
  self.assertEqual({a['file_path']for a in result['query_handoff']['code_anchors']},{'PacketCollector.ts','TextCollector.ts'})
  self.assertTrue(all(a['symbol']=='collect'for a in result['query_handoff']['code_anchors']))
 def test_label_only_recall_is_not_promoted(self):
  authority,result=self.run_case({'PacketCollector.ts':SOURCE})
  self.assertIsNone(authority)
 def test_non_witnesses_never_create_authority(self):
  for source in [SOURCE.replace('pieces.push(item)','defer(() => pieces.push(item))'),SOURCE.replace('      pieces.push(item)\n','').replace('    return pieces.join','    pieces.push(item)\n    return pieces.join'),"export class TextCollector { read(feed: Feed): string { return feed.readLine() } label(): string { return 'output iteration accumulation' } }"]:
   with self.subTest(source=source):
    authority,result=self.run_case({'TextCollector.ts':source})
    self.assertIsNone(authority)
    self.assertFalse(any(e.get('selection_reason')=='finite_direct_output_loop_source_shape'for a in result['query_handoff']['code_anchors']for e in a.get('source_excerpts',[])))
