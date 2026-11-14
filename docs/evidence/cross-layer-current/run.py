# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,subprocess,tempfile,os
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(ROOT))
from tools.agent_memory_runtime.benchmark_workspace import materialized_workspace
p=json.loads((D/'protocol.json').read_text());work=Path(tempfile.mkdtemp(prefix='cross-layer-current-'));manager=work/'manager';manager.mkdir()
def run(project,*args,traced=None):
    entry=D/'trace_cli.py'if traced else ROOT/'tools/agent_memory.py'
    r=subprocess.run([sys.executable,str(entry),*args,'--project',str(project),'--memory-home',str(work/'memory')],text=True,capture_output=True,env={**os.environ,'TRACE_OUT':str(D/(traced or 'unused.json'))})
    if r.returncode:raise RuntimeError(json.dumps({'args':args,'stderr':r.stderr,'stdout':r.stdout}))
    return json.loads(r.stdout)if '--json'in args else r.stdout
run(manager,'init')
result=run(manager,'eval-context-capability','--cases',str(ROOT/'docs/eval/system-capability-cases.json'),'--source',str(ROOT/p['source_project']),'--case-id',p['case']['id'],'--json');(D/'original-current.json').write_text(json.dumps(result,indent=2))
with materialized_workspace(ROOT/p['source_project'],p['case'])as project:
    run(project,'init');run(project,'learn-path','--path','.','--json');out=[]
    for c in p['case']['query_variants']:
        q=c['description'];raw=run(project,'context','--query',q,'--json',traced=c['id']+'-raw-trace.json');compact=run(project,'context','--query',q,'--compact','--json',traced=c['id']+'-compact-trace.json');out.append({'id':c['id'],'query':q,'raw':raw,'compact':compact});(D/'public.json').write_text(json.dumps(out,indent=2))
    for kind in ['code-symbol','memory-edge']:(D/(kind+'.json')).write_text(json.dumps(run(project,'list','--type',kind,'--limit','5000','--json'),indent=2))
print(json.dumps({'workspace':str(work),'results':[(c['query_variant'],c['status'])for c in result['cases']]}))
