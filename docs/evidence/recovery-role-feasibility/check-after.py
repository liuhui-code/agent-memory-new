import json
from pathlib import Path
D=Path(__file__).resolve().parent
before=json.loads((D/'before-public.json').read_text());after=json.loads((D/'after321-public.json').read_text());p=json.loads((D/'protocol.json').read_text());results=[]
for b,a in zip(before,after):
 old=b['compact']['query_handoff'];new=a['compact']['query_handoff'];case=a['case'];checks={'same_input':case==b['case'],'raw_handoff_unchanged':b['raw']['query_handoff']==a['raw']['query_handoff'],'budget':a['compact']['output_budget']['estimated_tokens']<=1500}
 for key in ['log_keywords','log_anchors','path_context','relation_hints']:checks[key+'_unchanged']=old.get(key)==new.get(key)
 if a['family']=='pair' and case['criterion']=='required':
  checks['required_files']=set(p['required_files'])<={r['file_path']for r in new['code_anchors']}
  checks['normal_anchors_unchanged']=all(r in new['code_anchors']for r in old['code_anchors'])
  for path,source in p['sources'].items():
   anchors=[r for r in new['code_anchors']if r['file_path']==path];lines=source.splitlines()
   checks[path+'_full_excerpt']=len(anchors)==1 and any(e['start_line']==1 and e['end_line']==len(lines) and e['content']=='\n'.join(lines) for e in anchors[0].get('source_excerpts',[]))
 else:checks['complete_compact_unchanged']=old==new
 family=next(f for f in p['families']if f['id']==a['family'])
 checks['source_bytes_unchanged']=all((Path(a['raw']['project_path'])/path).read_bytes()==s.encode() for path,s in family['sources'].items())
 results.append({'family':a['family'],'case':case['id'],'checks':checks,'passed':all(checks.values())})
(D/'after321-verdicts.json').write_text(json.dumps(results,indent=2));print([(r['case'],r['passed'])for r in results]);assert all(r['passed']for r in results)
