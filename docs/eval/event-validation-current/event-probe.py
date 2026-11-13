# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[2]))
from tests.agent_memory_test_base import AgentMemoryTestBase
FILES={'SelectionBridge.ets':'''export class SelectionBridge {
 currentId: string = ''
 onItemSelected(entry: Entry): void {
  this.currentId = entry.id
  this.openEditor()
 }
 openEditor(): void {}
}
''','SelectionHint.ets':'''export class SelectionHint {
 selected: boolean = false
 onClick(): void {
  this.selected = !this.selected
 }
}
''','PanelLauncher.ets':'''export class PanelLauncher {
 onItemSelected(entry: Entry): void {
  this.openEditor()
 }
 openEditor(): void {}
}
''','SplitSelection.ets':'''export class SplitSelection {
 currentId: string = ''
 onItemSelected(entry: Entry): void {
  this.currentId = entry.id
 }
 openEditor(): void {}
}
'''}
QUERIES=[('handoff','Selecting a different row opens the editor for the previous item. Locate the event-to-state handoff owner.',['SelectionBridge.ets']),('chinese','选择另一行却打开之前条目，请定位事件到状态交接源码。',['SelectionBridge.ets']),('hint','Locate SelectionHint.onClick source.',['SelectionHint.ets']),('two','Locate SelectionBridge.onItemSelected and SelectionHint.onClick source.',['SelectionBridge.ets','SelectionHint.ets'])]
protocol=ROOT/'event-protocol.json'
if not protocol.exists():protocol.write_text(json.dumps({'classification':'independent Development','sources':FILES,'queries':QUERIES},indent=2,ensure_ascii=False))
p=json.loads(protocol.read_text());b=AgentMemoryTestBase();rows=[]
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 for f,s in p['sources'].items():(root/f).write_text(s)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 for name,q,required in p['queries']:
  raw=json.loads(b.run_memory(root,'context','--query',q,'--json').stdout);out=json.loads(b.run_memory(root,'context','--query',q,'--compact','--json').stdout)
  paths=[a['file_path'] for a in out['query_handoff']['code_anchors']];rows.append({'name':name,'query':q,'expected':required,'paths':paths,'pass':set(paths)==set(required),'raw':raw,'output':out});print(name,paths,rows[-1]['pass'])
(ROOT/sys.argv[1]).write_text(json.dumps(rows,indent=2,ensure_ascii=False))
