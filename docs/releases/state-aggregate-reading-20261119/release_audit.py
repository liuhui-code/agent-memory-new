from pathlib import Path
import json,copy
O=Path(__file__).resolve().parent
result=[]
for b,a in zip(json.loads((O/'baseline.json').read_text()),json.loads((O/'release.json').read_text())):
 old=b['outputs']['compact'];new=a['outputs']['compact'];positive=b['query']['required']is not None
 if not positive:assert old==new
 else:
  added=new['query_handoff']['code_anchors'];assert len(added)==1 and added[0]['file_path']==b['query']['required']
  assert (added[0]['source_excerpts'][0]['start_line'],added[0]['source_excerpts'][0]['end_line'])==(5,10)
 result.append(dict(fixture=b['fixture'],request=b['query']['id'],unchanged=old==new,before=old['output_budget']['estimated_tokens'],after=new['output_budget']['estimated_tokens']))
for b,a in zip(json.loads((O/'original-before.json').read_text()),json.loads((O/'original-release.json').read_text())):
 old=b['outputs']['compact'];new=a['outputs']['compact']
 if b['variant']!='zh-noise':assert old==new
 else:
  original=old['query_handoff']['code_anchors'];current=new['query_handoff']['code_anchors'];assert current[:len(original)]==original
  added=current[len(original):];assert len(added)==1;assert added[0]['file_path']=='src/pages/RevenueQuarterPage.ets';assert added[0]['role']=='supporting';assert [(e['start_line'],e['end_line'])for e in added[0]['source_excerpts']]==[(9,16)]
  reverse=copy.deepcopy(new);reverse['query_handoff']['code_anchors']=original;reverse['query_handoff']['source_excerpt_policy']=old['query_handoff']['source_excerpt_policy'];reverse['output_budget']=old['output_budget'];assert reverse==old
 result.append(dict(original08=b['variant'],unchanged=old==new,before=old['output_budget']['estimated_tokens'],after=new['output_budget']['estimated_tokens']))
(O/'comparison.json').write_text(json.dumps(result,indent=2));print('12 independent and3 original2000 public outputs verified; original zh old fields preserved')
