"""Exactly the reviewed Stage B protocol; CLI outputs unmodified by observer."""
import json,sys,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];D=Path(__file__).resolve().parent
p=json.loads((D/'POSITIVE-ONLY-PROTOCOL.json').read_text())
workspace=ROOT.parent/'record-loop-fixed-before';workspace.mkdir(exist_ok=False)
results=[];commands=[]
def call(project,home,*args,trace=None):
    cli=[str(ROOT/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(home)]
    cmd=[sys.executable,*cli]if trace is None else [sys.executable,str(D/'trace-before.py'),str(trace),*cli]
    out=subprocess.run(cmd,capture_output=True,text=True,cwd=ROOT)
    commands.append(dict(command=cmd,returncode=out.returncode,stdout=out.stdout,stderr=out.stderr))
    (D/'before-commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
    assert out.returncode==0,out.stderr
    return out.stdout
for cohort in p['cohorts']:
    project=workspace/cohort['id']/'source';project.mkdir(parents=True);home=workspace/cohort['id']/'memory'
    for name,source in cohort['sources'].items():
        assert hashlib.sha256(source.encode()).hexdigest()==p['source_hashes'][cohort['id']][name]
        (project/name).write_text(source)
    call(project,home,'init');learn=json.loads(call(project,home,'learn-path','--path','.','--json'))
    for case in cohort['queries']:
        key=cohort['id']+'-'+case['id'];row=dict(cohort=cohort['id'],case=case,learn=learn)
        for form in ['raw','compact']:
            flags=['context','--query',case['query'],'--json']+(['--compact']if form=='compact'else[])
            row[form]=json.loads(call(project,home,*flags,trace=D/('before-trace-'+key+'-'+form+'.json')))
        results.append(row)
        (D/'before-public.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
        print(key, [a.get('file_path')for a in row['compact']['query_handoff']['code_anchors']],flush=True)
