from pathlib import Path
import json,subprocess,hashlib
O=Path(__file__).resolve().parent;R=O.parent/'repo';source=O.parent/'original13/source';reference=json.loads((R/'docs/releases/command37-current-verification-20261118/source-verification.json').read_text())
checks=[dict(path=f['path'],expected=f['sha256'],actual=hashlib.sha256((source/f['path']).read_bytes()).hexdigest())for f in reference['files']];assert all(x['actual']==x['expected']for x in checks);(O/'source-verification.json').write_text(json.dumps(dict(file_count=len(checks),all_equal_original=True,files=checks),indent=2))
cli=['python','-B',str(R/'tools/agent_memory.py')];tail=['--project',str(source),'--memory-home',str(O/'body-memory')]
p=subprocess.run(cli+['learn-path','--path','.','--json']+tail,capture_output=True,text=True);assert p.returncode==0,p.stderr;(O/'body-learn.json').write_text(p.stdout)
mapping=json.loads((O/'mapping.json').read_text());results=[]
for variant in mapping['case']['query_variants']:
 p=subprocess.run(cli+['context','--query',variant['description'],'--compact','--json']+tail,capture_output=True,text=True);assert p.returncode==0,p.stderr;(O/(variant['id']+'-compact.json')).write_text(p.stdout);d=json.loads(p.stdout)
 rows=[]
 for a in d['query_handoff']['code_anchors']:
  for e in a.get('source_excerpts',[]):
   lines=(source/a['file_path']).read_text().split('\n');actual='\n'.join(lines[e['start_line']-1:e['end_line']]);rows.append(dict(path=a['file_path'],start=e['start_line'],end=e['end_line'],exact_body=e['content']==actual,contains_required_8_11=e['start_line']<=8 and e['end_line']>=11))
 results.append(dict(variant=variant['id'],excerpts=rows))
(O/'body-check.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
