# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,tempfile
from pathlib import Path
R=Path.cwd();D=R/'docs/eval/import-traversal-current';p=json.loads((D/'arkts-protocol.json').read_text());out=[]
with tempfile.TemporaryDirectory() as d:
 root=Path(d)/'source';root.mkdir();mem=Path(d)/'memory'
 for n,s in p['sources'].items():(root/n).write_text(s)
 def call(repo,*args):
  r=subprocess.run([sys.executable,str(repo/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',str(mem)],capture_output=True,text=True,check=True);return json.loads(r.stdout) if '--json'in args else r.stdout
 old=R.parent/'import-traversal-baseline';call(old,'init');call(old,'learn-entry','--entry',p['entry'],'--depth','1')
 for stage,learn in [('old-archive-install-only',False),('ordinary-merge',True)]:
  if learn:call(R,'learn-entry','--entry',p['entry'],'--depth','1')
  syms=call(R,'list','--type','code-symbol','--limit','100','--json');edges=call(R,'list','--type','memory-edge','--limit','100','--json');byid={s['id']:s for s in syms}
  calls=[(byid[e['source_id']]['qualified_name'],byid[e['target_id']]['qualified_name'])for e in edges if e['relation']=='calls'and e['source_type']=='code_symbol'and e['target_type']=='code_symbol']
  files=call(R,'list','--type','code-file','--limit','100','--json'); imports=[e['evidence'] for e in edges if e['relation']=='imports']; out.append(dict(stage=stage,calls=calls,symbols=syms,edges=edges,files=files));print(stage,[f['file_path'] for f in files],imports)
(D/'upgrade.json').write_text(json.dumps(out,indent=2))
