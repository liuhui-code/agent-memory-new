# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,tempfile,shutil,hashlib
from pathlib import Path
from install_overlay import install
D=Path(__file__).resolve().parent;ROOT=D.parents[2]

def main():
    work=Path(tempfile.mkdtemp(prefix='listener-model-v2-'))
    candidate=work/'runtime';candidate.mkdir();shutil.copytree(ROOT/'tools',candidate/'tools')
    (candidate/'EXPERIMENTAL_DISPOSABLE_RUNTIME').write_text('Experiment only, not approved for deployment')
    def run(repo,project,*args):
        cmd=[sys.executable,str(repo/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(work/(project.name+'-memory'))]
        p=subprocess.run(cmd,text=True,capture_output=True)
        if p.returncode:raise RuntimeError(json.dumps({'cmd':cmd,'stdout':p.stdout,'stderr':p.stderr}))
        return json.loads(p.stdout) if '--json'in args else p.stdout
    def prepare(project,sources):
        project.mkdir()
        for name,source in sources.items():(project/name).write_text(source)
        run(ROOT,project,'init');run(ROOT,project,'learn-path','--path','.','--json')
    def rows(repo,project):return run(repo,project,'list','--type','code-symbol','--limit','300','--json')
    protocol=json.loads((ROOT/'docs/eval/native-listener-current-20261114/protocol.json').read_text())
    project=work/'fixed';prepare(project,protocol['sources'])
    before=rows(ROOT,project);(D/'before-list.json').write_text(json.dumps(before,indent=2))
    def queries(repo,phase):
        out=[]
        for case in protocol['queries']:
            out.append({'case':case,'raw':run(repo,project,'context','--query',case['query'],'--json'),'compact':run(repo,project,'context','--query',case['query'],'--compact','--json')})
            (D/(phase+'-queries.json')).write_text(json.dumps(out,indent=2))
    queries(ROOT,'before');install(candidate)
    (D/'code-only-list.json').write_text(json.dumps(rows(candidate,project),indent=2))
    learned=run(candidate,project,'learn-path','--path','.','--json');(D/'merge.json').write_text(json.dumps(learned,indent=2))
    (D/'merged-list.json').write_text(json.dumps(rows(candidate,project),indent=2));queries(candidate,'after')
    controls=json.loads((ROOT/'docs/evidence/listener-producer-feasibility/protocol.json').read_text());out=[]
    for case in [*controls['cases'], {**json.loads((D/'case-collision.json').read_text()), 'id':'case-collision'},json.loads((D/'length-control.json').read_text()),json.loads((D/'capacity-control.json').read_text())]:
        p=work/('control-'+case['id']);p.mkdir();(p/case['file_path']).write_text(case['source']);run(candidate,p,'init');run(candidate,p,'learn-path','--path','.','--json')
        r=rows(candidate,p)
        if case['id'] in ['overcap-file','actual-near-cap']:
            oldproject=work/(case['id']+'-baseline');prepare(oldproject,{case['file_path']:case['source']});oldrows=rows(ROOT,oldproject)
            (D/(case['id']+'-baseline.json')).write_text(json.dumps(oldrows,indent=2))
        facts=[w for row in r for w in json.loads(row.get('typed_invocation_witnesses')or'[]')]
        actual=[[w['source']['qualified_name'],w['formal']['declared_type'],w['callback']['property'],w['invocation']['member']]for w in facts]
        out.append({'id':case['id'],'expected':case['expected'],'actual':actual,'pass':sorted(actual)==sorted(case['expected']) if case['id']!='actual-near-cap' else None,'rows':r})
        (D/'indexed-controls.json').write_text(json.dumps(out,indent=2))
    (D/'workspace.json').write_text(json.dumps({'workspace':str(work),'candidate':str(candidate)},indent=2))
    print(json.dumps({'controls':len(out),'passed':sum(x['pass'] is True for x in out),'workspace':str(work)}))

if __name__=='__main__':main()
