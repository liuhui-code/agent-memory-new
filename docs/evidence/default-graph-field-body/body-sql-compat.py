exec(open('/tmp/run-body-controls-v2.py').read().split('for n,c in')[0].replace('recall-audit13/body-controls-v2','recall-audit13/body-sql-compat'))
protocol=json.loads((b/'repo/docs/evidence/sql-reading/protocol.json').read_text());source=o/'source';source.mkdir()
for n,v in protocol['sources'].items():
 p=source/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(v)
seed=o/'seed'
for args in [['init'],['learn-path','--path','.','--json']]:
 p=subprocess.run([sys.executable,str(b/'repo/tools/agent_memory.py'),*args,'--project',str(source),'--memory-home',str(seed)],capture_output=True,text=True);assert p.returncode==0,p.stderr
for arm in ['before','after']:
 home=o/(arm+'-memory');shutil.copytree(seed,home);cmd=([sys.executable,'-c',runner,str(b/'repo')]if arm=='before' else [sys.executable,str(b/'repo/tools/agent_memory.py')])+['context','--query',protocol['positive_queries'][0],'--project',str(source),'--memory-home',str(home),'--json','--compact'];p=subprocess.run(cmd,capture_output=True,text=True);(o/(arm+'.json')).write_text(p.stdout);(o/(arm+'.stderr')).write_text(p.stderr);results.append(dict(cmd=cmd,rc=p.returncode))
(o/'commands.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.loads((o/'before.json').read_text())==json.loads((o/'after.json').read_text()))
