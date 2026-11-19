from pathlib import Path
import json,ast,subprocess,shutil
O=Path(__file__).resolve().parent;B=O.parent;R=B/'repo';S=O/'source';S.mkdir(exist_ok=True);shutil.copy2(B/'original13/source/src/services/CacheService.ets',S/'CacheService.ets')
t=ast.parse((R/'tests/test_explicit_context_intent.py').read_text());payload=next(ast.literal_eval(n.value)for n in ast.walk(t)if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='payload'for x in n.targets))
qs=['Locate cache file source.','Locate catalog cache file source.','Locate dialog cache file source.','Locate log cache file source.','Locate logging cache file source.','Locate logger cache file source.']
(O/'FREEZE.json').write_text(json.dumps({'queries':qs,'reflection':payload,'classification':'Existing controlled Development procedure fixture; not a real incident. Read-only code-location queries must not gain procedure lane from unrelated word substring.'},indent=2))
base=['python','-B',str(R/'tools/agent_memory.py')];tail=['--project',str(S),'--memory-home',str(O/'memory')]
for i,cmd in enumerate([['init'],['learn-path','--path','.'],['reflect','--payload',json.dumps(payload)]]):
 r=subprocess.run(base+cmd+tail,capture_output=True,text=True);(O/f'setup-{i}.json').write_text(r.stdout);assert r.returncode==0,r.stderr
for i,q in enumerate(qs):
 r=subprocess.run(base+['context','--query',q,'--json','--compact']+tail,capture_output=True,text=True);(O/f'{i}.json').write_text(r.stdout);(O/f'{i}.stderr').write_text(r.stderr);assert r.returncode==0,r.stderr;d=json.loads(r.stdout);print(i,d.get('memory_intent'),d['query_handoff'].get('experience_refs'))
