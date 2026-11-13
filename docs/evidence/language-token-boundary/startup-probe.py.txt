# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,os.environ.get('RUNTIME_REPO',str(ROOT.parents[2])))
from tests.agent_memory_test_base import AgentMemoryTestBase
p=json.loads((ROOT/'protocol.json').read_text())
protocol=ROOT/'startup-protocol.json'
if not protocol.exists():protocol.write_text(json.dumps({'classification':'independent Development supplemental guard','sources':p['sources'],'queries':['Find the ArkTS application startup implementation.','Find the ets application initialization code.','ArkTS应用启动源码在哪里？','查找ets应用初始化实现。'],'expected':'EntryAbility.ets','body':'stage.loadContent'},ensure_ascii=False,indent=2))
p=json.loads(protocol.read_text());b=AgentMemoryTestBase();rows=[]
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 for f,s in p['sources'].items():(root/f).write_text(s)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.')
 for q in p['queries']:
  out=json.loads(b.run_memory(root,'context','--query',q,'--compact','--json').stdout);paths=[a['file_path'] for a in out['query_handoff']['code_anchors']];body='\n'.join(e['content'] for a in out['query_handoff']['code_anchors'] for e in a.get('source_excerpts',[]));rows.append({'query':q,'expected':p['expected'],'paths':paths,'pass':paths==[p['expected']] and p['body'] in body,'output':out});print(q,paths,rows[-1]['pass'])
(ROOT/sys.argv[1]).write_text(json.dumps(rows,ensure_ascii=False,indent=2))
