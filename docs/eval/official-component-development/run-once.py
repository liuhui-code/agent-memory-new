# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,os,shutil,subprocess,sys,tempfile,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;p=json.loads((D/'protocol.json').read_text())
assert not (D/'public-before.json').exists(), 'Already executed; do not repeat'
assert p['source_hashes']=={str(f.relative_to(D/'source')):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((D/'source').rglob('*.ets'))}
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)/'source';shutil.copytree(D/'source',root)
 def call(*args,mode=None):
  cli=D/'trace-cli.py' if mode else Path('tools/agent_memory.py').resolve()
  env=dict(os.environ,TRACE_FILE=str(D/(str(mode)+'-trace.json')))
  r=subprocess.run([sys.executable,str(cli),*args,'--project',str(root),'--memory-home',tmp+'/memory'],text=True,capture_output=True,check=True,env=env)
  return json.loads(r.stdout) if '--json' in args else r.stdout
 call('init');call('learn-path','--path','.')
 out={'symbols':call('list','--type','code-symbol','--limit','200','--json'),'edges':call('list','--type','memory-edge','--limit','500','--json')}
 for mode,flags in [('raw',[]),('compact',['--compact'])]:out[mode]=call('context','--query',p['query'],*flags,'--json',mode=mode)
 (D/'public-before.json').write_text(json.dumps(out,indent=2))
 print([(a['file_path'],a.get('symbol')) for a in out['compact']['query_handoff']['code_anchors']])
