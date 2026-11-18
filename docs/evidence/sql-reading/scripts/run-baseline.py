from pathlib import Path
import json,subprocess,sys,shutil
b=Path(__file__).resolve().parent;r=b.parent/'repo';p=json.loads((b/'protocol.json').read_text());root=b/'source';root.mkdir()
for f,s in p['sources'].items():
 path=root/f;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(s)
seed=b/'seed';base=[sys.executable,'-B',str(r/'tools/agent_memory.py')]
for args in [['init'],['learn-path','--path','.','--json']]:
 x=subprocess.run(base+args+['--project',str(root),'--memory-home',str(seed)],capture_output=True,text=True);assert x.returncode==0,x.stderr
commands=[]
for i,q in enumerate(p['positive_queries']):
 for mode,extra in [('raw',[]),('compact',['--compact'])]:
  h=b/f'before-{i}-{mode}-home';shutil.copytree(seed,h);cmd=base+['context','--project',str(root),'--memory-home',str(h),'--query',q,'--json']+extra;x=subprocess.run(cmd,capture_output=True,text=True);assert x.returncode==0,x.stderr;(b/f'before-{i}-{mode}.json').write_text(x.stdout);(b/f'before-{i}-{mode}.stderr').write_text(x.stderr);commands.append({'query_index':i,'mode':mode,'command':cmd,'rc':x.returncode})
(b/'baseline-commands.json').write_text(json.dumps(commands,indent=2));print('16 actual CLI baseline outputs saved')
