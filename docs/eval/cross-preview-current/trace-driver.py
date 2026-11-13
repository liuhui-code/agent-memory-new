# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,tempfile,shutil,os
from pathlib import Path
with tempfile.TemporaryDirectory() as d:
 root=Path(d)/'source';shutil.copytree('docs/eval/fixtures/system-capability',root,ignore=shutil.ignore_patterns('.benchmark-fixtures','.agent-memory'))
 def run(*args):
  os.environ['TRACE_FILE']=str(Path('docs/eval/cross-preview-current')/('trace-'+str(run.n)+'.json'));run.n+=1
  r=subprocess.run(['python','docs/eval/cross-preview-current/trace-cli.py',*args,'--project',str(root),'--memory-home',d+'/memory'],capture_output=True,text=True,check=True);return json.loads(r.stdout) if '--json' in args else r.stdout
 run.n=0
 run('init');run('learn-path','--path',str(root))
 symbols=run('list','--type','code-symbol','--limit','2000','--json');edges=run('list','--type','memory-edge','--limit','5000','--json')
 Path('docs/eval/cross-preview-current/graph.json').write_text(json.dumps(dict(symbols=symbols,edges=edges),indent=2))
 cases=json.load(open('docs/eval/system-capability-cases.json'))['cases']
 out={}
 for c in cases:
  if c['id'] not in ['context-cross-component-preview']:continue
  for v in c['query_variants']:
   k=c['id']+'::'+v['id'];out[k]={mode:run('context','--query',v['description'],*flags,'--json') for mode,flags in [('raw',[]),('compact',['--compact'])]}
 Path('docs/eval/cross-preview-current/public.json').write_text(json.dumps(out,indent=2))
