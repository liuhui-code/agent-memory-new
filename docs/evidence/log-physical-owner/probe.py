from pathlib import Path
import json,subprocess
O=Path(__file__).resolve().parent;R=O.parent/'repo'
for name,ext,owner,method in [('worker','ts','JobWorker','run'),('bridge','js','FetchBridge','connect')]:
 root=O/name;root.mkdir(exist_ok=True)
 source=f"export class {owner} {{\n  label = 'Display\u2028label'\n  {method}() {{ console.error('{name} request failed') }}\n}}\n"
 (root/('Source.'+ext)).write_text(source)
 tail=['--project',str(root),'--memory-home',str(O/(name+'-memory'))];cli=['python','-B',str(R/'tools/agent_memory.py')]
 for args in [['init'],['learn-path','--path','.'],['list','--type','code-log','--json'],['context','--query',f'Locate {owner}.{method} handling {name} request failed','--json']]:
  p=subprocess.run(cli+args+tail,capture_output=True,text=True);print(name,args[:2],p.returncode,p.stdout[:600],p.stderr[:100]);(O/(name+'-'+args[0]+'.txt')).write_text(p.stdout)
