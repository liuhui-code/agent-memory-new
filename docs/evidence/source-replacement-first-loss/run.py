# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,os,subprocess,tempfile,shutil
from pathlib import Path
D=Path(__file__).parent.resolve();p=json.load(open('docs/eval/system-capability-cases.json'));case=next(x for x in p['cases']if x['id']=='context-source-replacement-state-owner');query=case['query_variants'][0]['description']
with tempfile.TemporaryDirectory()as tmp:
 root=Path(tmp)/'source';shutil.copytree('docs/eval/fixtures/system-capability',root,ignore=shutil.ignore_patterns('.benchmark-fixtures','.agent-memory'))
 def run(label,*args):
  r=subprocess.run(['python',str(D/'trace-cli.py'),*args,'--project',str(root),'--memory-home',tmp+'/memory'],capture_output=True,text=True,check=True,env=dict(os.environ,TRACE_FILE=str(D/(label+'-trace.json'))));return json.loads(r.stdout)if'--json'in args else r.stdout
 run('init','init');run('learn','learn-path','--path','.')
 out={'case':case,'raw':run('raw','context','--query',query,'--json'),'compact':run('compact','context','--query',query,'--compact','--json')}
 (D/'public.json').write_text(json.dumps(out,indent=2))
