# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys
from pathlib import Path
D=Path(__file__).resolve().parent
phase=sys.argv[1];before=json.loads((D/'before-public.json').read_text());after=json.loads((D/(phase+'-public.json')).read_text());protocol=json.loads((D/'protocol.json').read_text())
assert len(before)==len(after)==11
out=[]
for old,new in zip(before,after):
 assert old['case']==new['case'] and old['family']==new['family']
 key=new['case']['id'];a=new['compact']['query_handoff'];b=old['compact']['query_handoff'];raw=new['raw']['query_handoff']
 checks={'raw_handoff_unchanged':raw==old['raw']['query_handoff'],'logs_unchanged':all(a.get(k)==b.get(k)for k in ('log_keywords','log_anchors')),'path_unchanged':a.get('path_context')==b.get('path_context')}
 checks['budget']=new['compact']['output_budget']['estimated_tokens']<=1500
 paths={x['file_path']for x in a['code_anchors']}
 checks['required']=set(new['case'].get('required',[]))<=paths
 checks['forbidden']=not(set(new['case'].get('forbidden',[]))&paths)
 if key not in ('lifecycle-1','two-complete-owners'):checks['complete_handoff_unchanged']=a==b
 else:
  expected={'BufferSession.ets'} if key=='lifecycle-1' else {'BufferSession.ets','EditorSession.ets'}
  checks['all_positive_only']=paths==expected
  sources=next(f for f in protocol['families']if f['id']==new['family'])['sources']
  checks['complete_exact_snapshots']=all(any(e['start_line']==1 and e['end_line']==len(sources[x['file_path']].splitlines()) and e['content']==sources[x['file_path']].rstrip('\n') and e.get('source')=='validated_request_snapshot' for e in x.get('source_excerpts',[]))for x in a['code_anchors'])
 out.append({'id':key,'checks':checks,'paths':sorted(paths),'budget':new['compact']['output_budget']})
(D/(phase+'-checks.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2));assert all(all(r['checks'].values())for r in out)
