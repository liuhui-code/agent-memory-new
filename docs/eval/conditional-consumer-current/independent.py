# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parents[2]))
from tests.agent_memory_test_base import AgentMemoryTestBase
sources={'TouchReader.ets':'''export class TouchReader {
 onTouch(event: TouchEvent): void {
  const finger = event.touches[0]
  this.x = finger.x
 }
}
''','ConsoleSink.ets':'''export class ConsoleSink {
 report(error: Error): void {
  console.error('touch interaction failed', error)
 }
}
''','AuditPage.ets':'''import { ConsoleSink } from './ConsoleSink'
export class AuditPage {
 sink: ConsoleSink = new ConsoleSink()
 onFailure(error: Error): void { this.sink.report(error) }
}
'''}
queries=[('source','触摸事件为空时第一个手指缺失并导致交互异常，请只返回触摸回调和索引读取所在源码。',['TouchReader.ets']),('named','Locate TouchReader.onTouch source.',['TouchReader.ets']),('log','Find the console error logging implementation.',['ConsoleSink.ets']),('multiple','Locate TouchReader.onTouch and ConsoleSink.report source.',['TouchReader.ets','ConsoleSink.ets'])]
p={'classification':'independent Development diagnostic, no serving candidate','sources':sources,'queries':queries}
(D/'independent-protocol.json').write_text(json.dumps(p,indent=2,ensure_ascii=False))
b=AgentMemoryTestBase();out=[]
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 for n,s in sources.items():(root/n).write_text(s)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 for name,q,required in queries:
  raw=json.loads(b.run_memory(root,'context','--query',q,'--json').stdout)
  compact=json.loads(b.run_memory(root,'context','--query',q,'--compact','--json').stdout)
  paths=[a['file_path'] for a in compact['query_handoff']['code_anchors']]
  out.append(dict(name=name,query=q,required=required,paths=paths,strict_pass=set(paths)==set(required),raw=raw,compact=compact));print(name,paths)
(D/'independent-current.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
