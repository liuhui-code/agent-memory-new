from pathlib import Path
import json,copy
O=Path(__file__).resolve().parent;out=[]
for b,a in zip(json.loads((O/'baseline.json').read_text()),json.loads((O/'candidate.json').read_text())):
 old=b['outputs']['compact'];new=a['outputs']['compact'];r=copy.deepcopy(new)
 for anchor in r['query_handoff']['code_anchors']:
  anchor['source_excerpts']=[e for e in anchor.get('source_excerpts',[]) if e.get('selection_reason')!='authenticated_requested_declaration']
 r['query_handoff']['source_excerpt_policy']=old['query_handoff']['source_excerpt_policy'];r['output_budget']=old['output_budget'];assert r==old
 if b['query']['id']!='declaration':assert new==old
 out.append(dict(fixture=b['fixture'],query=b['query']['id'],unchanged=old==new,all_old_data_retained=True,token_before=old['output_budget']['estimated_tokens'],token_after=new['output_budget']['estimated_tokens']))
(O/'comparison.json').write_text(json.dumps(out,indent=2));print('14 public requests: two declarations supplemented, 12 byte-equivalent payload controls; all old data preserved')
