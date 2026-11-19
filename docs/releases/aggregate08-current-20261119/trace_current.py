from pathlib import Path
import json,shutil,subprocess,hashlib
O=Path(__file__).resolve().parent;R=O.parent/'repo';src=O.parent/'original13/source';target=O/'standard-source';target.mkdir()
manifest=json.loads((O/'materialized-files.json').read_text());assert len(manifest)==157
for f in manifest:
 data=(src/f['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==f['sha256'];p=target/f['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
cli=['python','-B',str(R/'tools/agent_memory.py')];seed=O/'seed-memory'
for cmd in [['init'],['wiki-index']]:
 p=subprocess.run(cli+cmd+['--project',str(target),'--memory-home',str(seed)],capture_output=True,text=True);assert p.returncode==0,p.stderr
q=json.loads((O/'mapping.json').read_text())['case']['query_variants'][2]['description']
for label,script,compact in [('traced-raw',O/'trace-cli.py',False),('traced-compact',O/'trace-cli.py',True),('clean-compact',R/'tools/agent_memory.py',True)]:
 home=O/(label+'-memory');shutil.copytree(seed,home);cmd=['python','-B',str(script),'context','--query',q,'--json','--project',str(target),'--memory-home',str(home)]+(['--compact']if compact else[])
 p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr;(O/(label+'.json')).write_text(p.stdout)
a=json.loads((O/'traced-compact.json').read_text());b=json.loads((O/'clean-compact.json').read_text());assert a==b
(O/'trace-equality.json').write_text(json.dumps(dict(equal=True,standard_files=len(manifest),query=q),ensure_ascii=False,indent=2))
