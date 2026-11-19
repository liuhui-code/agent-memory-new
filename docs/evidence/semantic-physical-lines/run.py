from pathlib import Path
import json,subprocess
O=Path(__file__).resolve().parent;R=O.parent/'repo'
base="export class DocumentStore {\n  label: string = 'Document%slabel'\n  save(value: string): string {\n    return value.trim()\n  }\n}\n"
query='Locate DocumentStore.save source.'
(O/'FREEZE.json').write_text(json.dumps({'source_template':base,'variants':['space','U+2028','U+2029'],'query':query,'scope':'Controlled valid string-literal separator Development; no production changes, source-line identity hypothesis only.'},indent=2))
for label,char in [('space',' '),('ls','\u2028'),('ps','\u2029')]:
 src=O/label;src.mkdir(exist_ok=True);(src/'DocumentStore.ts').write_text(base%char)
 cli=['python','-B',str(R/'tools/agent_memory.py')];tail=['--project',str(src),'--memory-home',str(O/(label+'-memory'))]
 for cmd in [['init'],['learn-path','--path','.']]:
  r=subprocess.run(cli+cmd+tail,capture_output=True,text=True);assert r.returncode==0,r.stderr
 for mode in ['raw','compact']:
  r=subprocess.run(cli+['context','--query',query,'--json']+tail+(['--compact']if mode=='compact'else[]),capture_output=True,text=True);(O/f'{label}-{mode}.json').write_text(r.stdout);(O/f'{label}-{mode}.stderr').write_text(r.stderr);assert r.returncode==0,r.stderr;d=json.loads(r.stdout);print(label,mode,[(a.get('symbol'),a.get('source_ranges'),a.get('source_excerpts'))for a in d['query_handoff']['code_anchors']])
