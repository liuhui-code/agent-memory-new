from pathlib import Path
import json,subprocess,sqlite3
O=Path(__file__).resolve().parent;R=O.parent/'repo'
sources={
 'inside':"export class DocumentStore {\n  save(value: string): string {\n    const label = 'Document\u2028label'\n    if (value.length === 0) { return label }\n    return value.trim()\n  }\n}\n",
 'template':"export class DocumentStore {\n  label: string = `Document\u2029label`\n  save(value: string): string {\n    return value.trim()\n  }\n}\n",
 'comment':"export class DocumentStore {\n  /* Document\u2028label */\n  save(value: string): string {\n    return value.trim()\n  }\n}\n",
 'outside':"export class DocumentStore {\n  label: string = 'a';\u2028hidden(): string { return 'b' }\n  save(value: string): string {\n    return value.trim()\n  }\n}\n",
}
(O/'EXTENDED-FREEZE.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2));out=[]
for name,text in sources.items():
 root=O/name;root.mkdir(exist_ok=True);(root/'DocumentStore.ts').write_text(text);tail=['--project',str(root),'--memory-home',str(O/(name+'-memory'))];base=['python','-B',str(R/'tools/agent_memory.py')]
 for cmd in [['init'],['learn-path','--path','.']]:
  p=subprocess.run(base+cmd+tail,capture_output=True,text=True);assert p.returncode==0,p.stderr
 p=subprocess.run(base+['context','--query','Locate DocumentStore.save source.','--json','--compact']+tail,capture_output=True,text=True);(O/(name+'-compact.json')).write_text(p.stdout);(O/(name+'-compact.stderr')).write_text(p.stderr);assert p.returncode==0,p.stderr;d=json.loads(p.stdout);out.append({'name':name,'anchors':d['query_handoff']['code_anchors']})
print(json.dumps(out,ensure_ascii=False));(O/'extended-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
