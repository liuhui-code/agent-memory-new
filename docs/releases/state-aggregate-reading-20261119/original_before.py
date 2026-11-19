from pathlib import Path
import json,subprocess
O=Path(__file__).resolve().parent;R=O.parent/'repo';root=O.parent/'render05-current-contract/source';home=O/'original-memory'
def run(args):
 p=subprocess.run(['python','-B',str(R/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',str(home)],capture_output=True,text=True);assert p.returncode==0,p.stderr;return json.loads(p.stdout)if '--json'in args else p.stdout
run(['init']);run(['learn-path','--path',str(root)])
c=next(x for x in json.load(open(R/'docs/eval/system-capability-cases.json'))['cases']if x['id']=='context-abstract-reactive-aggregate');out=[]
for q in c['query_variants']:
 values={m:run(['context','--query',q['description'],'--json']+(['--compact','--compact-token-budget','2000','--preserve-selected-source-anchors']if m=='compact'else[]))for m in ['raw','compact']};out.append(dict(variant=q['id'],query=q['description'],outputs=values));print(q['id'],values['compact']['output_budget'])
(O/'original-before.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
