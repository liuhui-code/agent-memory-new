# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_salience_score import prefix_match
from tools.agent_memory_runtime.query_salient_source_retention import source_matches
from tools.agent_memory_runtime.query_salience import salient_query_tokens
OUT=Path(__file__).resolve().parent
p=json.loads((OUT/'protocol.json').read_text());b=AgentMemoryTestBase()
report={'sources':p['sources'],'sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in p['sources'].items()},'setup':[],'results':[]}
with tempfile.TemporaryDirectory(prefix='compound-prefix-') as d:
 project=Path(d)/'source';project.mkdir()
 for name,source in p['sources'].items():(project/name).write_text(source)
 for args in [('init',),('learn-path','--path','.','--json')]:
  r=b.run_memory(project,*args);report['setup'].append({'command':r.args,'stdout':r.stdout,'stderr':r.stderr})
 for name,q,required in p['queries']:
  required=[required] if isinstance(required,str) else required
  raw=json.loads(b.run_memory(project,'context','--query',q,'--json').stdout)
  compact=json.loads(b.run_memory(project,'context','--query',q,'--compact','--json').stdout)
  paths=[a['file_path'] for a in compact['query_handoff']['code_anchors']]
  report['results'].append({'name':name,'query':q,'salient_terms':salient_query_tokens(q),'required':required,'paths':paths,'required_present':set(required)<=set(paths),'proposed_exact_source_set':set(required)==set(paths),'raw':raw,'compact':compact})
report['internal_pairs']=[{'left':a,'right':c,'match':prefix_match(a,c)} for a,c in p['internal_pairs']]
report['source_match_matrix']=[{'term':a,'source':s,'matches':sorted(source_matches({'method_evidence':s,'string_evidence':''},[a]))} for a,s in p['source_match_matrix']]
(OUT/'public.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
summary=[{k:r[k] for k in ('name','paths','required_present','proposed_exact_source_set')}|{'budget':r['compact']['output_budget']} for r in report['results']]
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
