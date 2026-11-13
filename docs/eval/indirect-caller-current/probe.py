# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[2]))
from tests.agent_memory_test_base import AgentMemoryTestBase
FILES={'ModalBridge.ets':'''export class ModalBridge {
 finish(): void { this.controller.close() }
 reset(): void { this.controller.reset() }
}
''','ConfirmPanel.ets':'''import { ModalBridge } from './ModalBridge'
@Component
export struct ConfirmPanel {
 bridge: ModalBridge = new ModalBridge()
 build() {
  Button('Confirm').onClick(() => {
   this.bridge.finish()
  })
 }
}
''','ResetPanel.ets':'''import { ModalBridge } from './ModalBridge'
@Component
export struct ResetPanel {
 bridge: ModalBridge = new ModalBridge()
 build() {
  Button('Reset').onClick(() => {
   this.bridge.reset()
  })
 }
}
'''}
QUERIES=[('finish','Find the actual caller of ModalBridge.finish.',['ConfirmPanel.ets']),('reset','Find the actual caller of ModalBridge.reset.',['ResetPanel.ets']),('both','Find both actual callers of ModalBridge.finish and ModalBridge.reset.',['ConfirmPanel.ets','ResetPanel.ets']),('broad','Find the actual callers of ModalBridge.',['ConfirmPanel.ets','ResetPanel.ets'])]
protocol=ROOT/'protocol.json'
if not protocol.exists():protocol.write_text(json.dumps({'classification':'independent Development','sources':FILES,'queries':QUERIES},indent=2))
p=json.loads(protocol.read_text());b=AgentMemoryTestBase();rows=[]
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 for name,s in p['sources'].items():(root/name).write_text(s)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 for name,q,expected in p['queries']:
  raw=json.loads(b.run_memory(root,'context','--query',q,'--json').stdout);out=json.loads(b.run_memory(root,'context','--query',q,'--compact','--json').stdout);paths=[a['file_path'] for a in out['query_handoff']['code_anchors']];rows.append({'name':name,'query':q,'expected':expected,'paths':paths,'pass':set(expected)==set(paths),'raw':raw,'output':out});print(name,paths,rows[-1]['pass'])
(ROOT/sys.argv[1]).write_text(json.dumps(rows,indent=2))
