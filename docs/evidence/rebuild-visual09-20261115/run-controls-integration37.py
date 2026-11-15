# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(ROOT))
from tests.agent_memory_test_base import AgentMemoryTestBase
b=AgentMemoryTestBase();results=[]
for case in json.loads((D/'public-controls-protocol.json').read_text()):
 with tempfile.TemporaryDirectory(prefix='background-control-')as tmp:
  project=Path(tmp)/'source';project.mkdir()
  for name,source in case['sources'].items():(project/name).write_text(source)
  b.run_memory(project,'init');b.run_memory(project,'learn-path','--path','.','--json')
  r=json.loads(b.run_memory(project,'context','--query',case['query'],'--compact','--json').stdout)
  paths=sorted({a['file_path']for a in r['query_handoff']['code_anchors']});snapshots=any(e.get('source')=='validated_request_snapshot'for a in r['query_handoff']['code_anchors']for e in a.get('source_excerpts',[]))
  passed=paths==case['expected']if 'expected'in case else snapshots==case['snapshot_expected']
  results.append(dict(name=case['name'],passed=passed,paths=paths,snapshots=snapshots,compact=r));print(case['name'],passed,paths,flush=True)
(D/'integration-after37-controls.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
assert all(r['passed']for r in results)
