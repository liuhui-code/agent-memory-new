# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Post-candidate adversarial realization of the frozen negative contract list."""
import json,subprocess,sys,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent;root=Path(__file__).resolve().parents[3];base=root.parent/'rebuild37-callback-only-20261115'
p=json.loads((D/'protocol-v2.json').read_text());q=p['queries'][0]['query'];s=p['sources'];results={}
controls={
 'duplicate-owner':{**s,'SecondMenu.ets':s['SyncMenu.ets'].replace('SyncMenu','SecondMenu')},
 'neighbor-label':{**s,'SyncMenu.ets':s['SyncMenu.ets'].replace("caption: 'Restart sync',","nested: {caption: 'Restart sync'},")},
 'unknown-template':{**s,'SyncMenu.ets':'const text = `${dynamic()}`;\n'+s['SyncMenu.ets']},
 'unknown-competitor':{**s,'OpaqueMenu.ets':'const text = `${dynamic()}`;\n'+s['SyncMenu.ets'].replace('SyncMenu','OpaqueMenu')},
 'unwired-only':{**s,'SyncMenu.ets':s['SyncMenu.ets'].replace('Button(action.caption).onClick(action.run)','Text(action.caption)')},
 'cross-consumer':{**s,'SyncMenu.ets':s['SyncMenu.ets'].replace('ForEach(this.actions','ForEach(this.other)')},
 'complete-budget':{**s,'SyncMenu.ets':s['SyncMenu.ets'].replace('    Column() {','    /*'+'x'*1700+'*/ Column() {')}}
for name,sources in controls.items():
 with tempfile.TemporaryDirectory(prefix='command-negative-')as t:
  project=Path(t)/'source';project.mkdir()
  for file,source in sources.items():(project/file).write_text(source)
  outputs=[]
  for version in [base,root]:
   def cli(*args):
    r=subprocess.run([sys.executable,str(version/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',t+'/memory'],capture_output=True,text=True,check=True);return json.loads(r.stdout)if'--json'in args else r.stdout
   if version==base:cli('init');cli('learn-path','--path','.')
   outputs.append(cli('context','--query',q,'--compact','--json'))
  # Same project/index/runtime-contract snapshots; ignore no fields in handoff.
  equal=outputs[0]['query_handoff']==outputs[1]['query_handoff']
  results[name]={'same_handoff':equal,'baseline':outputs[0],'candidate':outputs[1]}
(D/'negative-public-v2.json').write_text(json.dumps(results,indent=2));print({k:v['same_handoff']for k,v in results.items()})
assert all(v['same_handoff']for v in results.values())
