# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[2]))
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.text import query_tokens
FILES={
'GlyphList.ets':'''@Component
export struct GlyphList {
 build() {
  List() {
   ListItem() { Text('glyph') }
  }.divider({ strokeWidth: 2 })
 }
}
''',
'ByteMixer.ts':'''export class ByteMixer {
 mixBytes(input: number[]): number {
  let checksum = 0
  for (const value of input) { checksum = (checksum << 1) ^ value }
  return checksum
 }
}
''',
'EntryAbility.ets':'''export class EntryAbility {
 onWindowStageCreate(stage: WindowStage): void {
  stage.loadContent('pages/Entry')
 }
 onWindowStageDestroy(): void {
  this.stage.release()
 }
}
'''}
QUERIES=[
('ui-language','Find the ArkTS glyph divider implementation.','GlyphList.ets'),
('ui-plain','Find the glyph divider implementation.','GlyphList.ets'),
('algorithm-language','Locate the ArkTS checksum computation implementation.','ByteMixer.ts'),
('algorithm-plain','Locate the checksum computation implementation.','ByteMixer.ts'),
('ets-algorithm','Locate the ets checksum computation implementation.','ByteMixer.ts'),
('ability','Find the Ability Stage lifecycle implementation.','EntryAbility.ets'),
('platform','定位鸿蒙 Stage 页面加载的实现。','EntryAbility.ets'),
('qualified','Find EntryAbility.onWindowStageCreate source.','EntryAbility.ets'),
('arkts-ability','Locate the ArkTS Ability Stage implementation.','EntryAbility.ets')]
protocol=ROOT/'protocol.json'
if not protocol.exists():protocol.write_text(json.dumps({'classification':'independent Development','sources':FILES,'queries':QUERIES},ensure_ascii=False,indent=2))
p=json.loads(protocol.read_text());b=AgentMemoryTestBase();rows=[]
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 for f,s in p['sources'].items():(root/f).write_text(s)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 for name,q,expected in p['queries']:
  raw=json.loads(b.run_memory(root,'context','--query',q,'--json').stdout);out=json.loads(b.run_memory(root,'context','--query',q,'--compact','--json').stdout)
  paths=[a['file_path'] for a in out['query_handoff']['code_anchors']];rows.append({'name':name,'query':q,'expected':expected,'paths':paths,'pass':paths==[expected],'tokens':query_tokens(q),'raw':raw,'output':out});print(name,paths,rows[-1]['pass'])
(ROOT/sys.argv[1]).write_text(json.dumps(rows,indent=2,ensure_ascii=False))
