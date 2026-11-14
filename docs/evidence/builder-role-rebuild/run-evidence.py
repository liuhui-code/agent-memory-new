# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json, subprocess, sys
from pathlib import Path
D=Path(__file__).resolve().parent
REPO=D.parents[2]
phase=sys.argv[1]
work=REPO.parent/'builder-rebuild-execution'
work.mkdir(exist_ok=True)
def run(root, *args):
    cmd=[sys.executable,str(REPO/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',str(work/(root.name+'-memory'))]
    p=subprocess.run(cmd,capture_output=True,text=True,check=True)
    return json.loads(p.stdout) if '--json' in args else p.stdout
def prepare(root,sources):
    root.mkdir(exist_ok=True)
    for name,text in sources.items():(root/name).write_text(text)
    run(root,'init');run(root,'learn-path','--path','.','--json')
p=json.loads((D/'protocol.json').read_text());root=work/'activation'
if phase=='before':prepare(root,p['sources'])
if phase=='merged':run(root,'learn-path','--path','.','--json')
(D/('activation-'+phase+'.json')).write_text(json.dumps(run(root,'list','--type','code-symbol','--limit','300','--json'),indent=2))
if phase in ('before','merged'):
    p=json.loads((D/'compatibility-protocol.json').read_text());root=work/('compat-'+phase);prepare(root,p['sources']);result=[]
    for case in p['cases']:
        result.append({'case':case,'raw':run(root,'context','--query',case['query'],'--json'),'compact':run(root,'context','--query',case['query'],'--compact','--json')})
        (D/('compatibility-'+phase+'.json')).write_text(json.dumps(result,indent=2))
