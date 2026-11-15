# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import hashlib,json,pathlib,subprocess,sys,tempfile
D=pathlib.Path(__file__).resolve().parent;ROOT=D.parents[2];OUT=pathlib.Path(sys.argv[1]);assert not OUT.exists();OUT.mkdir(parents=True)
p=json.loads((D/'protocol.json').read_text());rows=[]
(OUT/'execution.json').write_text(json.dumps({'head':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'protocol_sha256':hashlib.sha256((D/'protocol.json').read_bytes()).hexdigest()},indent=2)+'\n')
for family in p['families']:
 with tempfile.TemporaryDirectory(prefix='lifecycle-English-'+family['id']+'-')as temp:
  project=pathlib.Path(temp)/'project';project.mkdir();home=pathlib.Path(temp)/'memory'
  for name,source in family['sources'].items():
   assert hashlib.sha256(source.encode()).hexdigest()==p['source_hashes'][family['id']][name]
   target=project/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source)
  def cli(stage,args,trace=False):
   command=[sys.executable,'-B',str(ROOT/'tools/agent_memory.py')]
   if trace:command=[sys.executable,'-B',str(ROOT/'docs/evidence/lifecycle-source-prerequisites/trace-input-cli.py'),str(OUT/(stage+'-trace.json')),str(ROOT/'tools/agent_memory.py')]
   r=subprocess.run(command+args+['--project',str(project),'--memory-home',str(home)],capture_output=True,text=True)
   (OUT/(stage+'.stdout')).write_text(r.stdout);(OUT/(stage+'.stderr')).write_text(r.stderr);r.check_returncode()
   return json.loads(r.stdout)if '--json'in args else r.stdout
  cli(family['id']+'-init',['init']);cli(family['id']+'-learn',['learn-path','--path','.','--json'])
  symbols=cli(family['id']+'-symbols',['list','--type','code-symbol','--limit','300','--json']);edges=cli(family['id']+'-edges',['list','--type','memory-edge','--limit','1000','--json'])
  for case in family['queries']:
   stage=family['id']+'-'+case['id'];raw=cli(stage+'-raw',['context','--query',case['query'],'--json']);compact=cli(stage+'-compact',['context','--query',case['query'],'--compact','--json'],True)
   row={'family':family['id'],'case':case,'raw':raw,'compact':compact,'symbols':symbols,'edges':edges,'trace':stage+'-compact-trace.json'};rows.append(row)
   (OUT/'public.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
   print(stage,[a['file_path']for a in compact['query_handoff']['code_anchors']],flush=True)
