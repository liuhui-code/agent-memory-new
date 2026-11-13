# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[2]))
from tests.agent_memory_test_base import AgentMemoryTestBase
FILES={
'MessageSurface.ets':'''@Component
export struct MessageSurface {
  content: string = ''
  build() {
    Column() { Text(this.plainBody()) }
  }
  plainBody(): string {
    return this.content.replace('<p>', '').replace('</p>', '')
  }
}
''',
'MessageRecord.ets':'''export class MessageRecord {
  content: string = ''
  title: string = ''
}
''',
'DetailPanel.ets':'''@Component
export struct DetailPanel {
  build() {
    Column() { Text('Message details') }
  }
}
''',
'DisplaySettings.ets':'''export class DisplaySettings {
  displayName: string = ''
  saveName(): void {
    this.displayName = this.displayName.trim()
  }
}
'''}
QUERIES=[
('generic','Message details still display markup tags. Locate the UI rendering cleanup owner rather than the message data entity.', ['MessageSurface.ets'],['DetailPanel.ets','DisplaySettings.ets','MessageRecord.ets']),
('explicit','Locate MessageSurface.plainBody source.',['MessageSurface.ets'],['DetailPanel.ets','DisplaySettings.ets']),
('two','Locate MessageSurface.plainBody and DetailPanel.build source.',['MessageSurface.ets','DetailPanel.ets'],[]),
('literal','Find the literal Message details.',['DetailPanel.ets'],[])]
(ROOT/'render-protocol.json').write_text(json.dumps({'classification':'independent Development','sources':FILES,'queries':QUERIES},indent=2))
b=AgentMemoryTestBase();results=[]
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 for f,s in FILES.items():(root/f).write_text(s)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.','--json')
 for name,q,required,excluded in QUERIES:
  raw=json.loads(b.run_memory(root,'context','--query',q,'--json').stdout)
  compact=json.loads(b.run_memory(root,'context','--query',q,'--compact','--json').stdout)
  paths=[a['file_path'] for a in compact['query_handoff']['code_anchors']]
  results.append({'name':name,'query':q,'paths':paths,'pass':set(required)<=set(paths) and not set(excluded)&set(paths),'raw':raw,'compact':compact})
  print(name,paths,results[-1]['pass'])
(ROOT/'render-independent.json').write_text(json.dumps(results,indent=2))
