# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import hashlib,json,subprocess,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
D=Path(__file__).resolve().parent
E=REPO.parent/'reactive-aggregate-fixed-evidence'
protocol=json.loads((D/'protocol.json').read_text());manifest=json.loads((D/'frozen-manifest.json').read_text())
assert hashlib.sha256((D/'protocol.json').read_bytes()).hexdigest()==manifest['protocol_sha256']
root=E/'project';home=E/'memory'
assert not (D/'public.json').exists(), 'Do not rerun a completed fixed pass'
root.mkdir(parents=True, exist_ok=True)
for name,source in protocol['sources'].items():
 assert hashlib.sha256(source.encode()).hexdigest()==manifest['source_sha256'][name]
 (root/name).write_text(source)
commands=[]
def run(args):
 cmd=[sys.executable,str(REPO/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',str(home)]
 r=subprocess.run(cmd,cwd=REPO,text=True,capture_output=True)
 commands.append({'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 if r.returncode:raise RuntimeError(r.stderr)
 return r.stdout if args[0]=='init' else json.loads(r.stdout)
run(['init']);run(['learn-path','--path','.','--json'])
results=[]
for case in protocol['queries']:
 raw=run(['context','--query',case['query'],'--json']);compact=run(['context','--query',case['query'],'--compact','--json'])
 anchors=compact['query_handoff']['code_anchors'];paths=list(dict.fromkeys(a['file_path'] for a in anchors))
 bodies={path:'\n'.join(e['content'] for a in anchors if a['file_path']==path for e in a.get('source_excerpts',[])) for path in paths}
 required=set(case['required'])<=set(paths);forbidden=sorted(set(paths)&set(case['forbidden']))
 missing={path:[s for s in strings if s not in bodies.get(path,'')] for path,strings in case['source_fragments'].items()};missing={p:v for p,v in missing.items() if v}
 source_valid=all('\n'.join(protocol['sources'][a['file_path']].splitlines()[e['start_line']-1:e['end_line']])==e['content'] for a in anchors for e in a.get('source_excerpts',[]))
 budget=compact['output_budget']['estimated_tokens'];passed=required and not forbidden and not missing and source_valid and budget<=1500
 results.append({'id':case['id'],'query':case['query'],'paths':paths,'required_present':required,'forbidden_hits':forbidden,'extra_paths':sorted(set(paths)-set(case['required'])),'missing_source_fragments':missing,'source_bytes_valid':source_valid,'tokens':budget,'pass':passed,'raw':raw,'compact':compact})
(D/'public.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
(D/'commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
for r in results:print(r['id'],r['pass'],r['paths'],r['missing_source_fragments'],r['tokens'])
