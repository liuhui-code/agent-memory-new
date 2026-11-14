import json
from pathlib import Path
D=Path('/workspace/scratch/dcdb41e16594/build-marker-final-0fab179/docs/evidence/build-marker-boundary')
p=json.loads((D/'protocol.json').read_text()); b=json.loads((D/'before-fixed-public.json').read_text()); a=json.loads((D/'after-fixed-public.json').read_text());out=[]
for x,y in zip(b,a):
 c=y['case']; h=y['compact']['query_handoff'];checks={}
 if c['criterion']=='unchanged':
  checks['compact_handoff_exact']=h==x['compact']['query_handoff'];checks['raw_handoff_exact']=y['raw']['query_handoff']==x['raw']['query_handoff']
 else:
  checks['expected_paths']=set(c['expected'])=={z['file_path']for z in h['code_anchors']}
  sources=next(f['sources']for f in p['families']if f['id']==y['family'])
  checks['actual_excerpts_exact']=all(e['content']=='\n'.join(sources[z['file_path']].splitlines()[e['start_line']-1:e['end_line']]) and not e['truncated'] for z in h['code_anchors'] for e in z.get('source_excerpts',[]))
 for key in ['log_keywords','log_anchors','path_context']:
  checks[key+'_unchanged']=h[key]==x['compact']['query_handoff'][key]
 t=json.loads((D/y['trace']).read_text()); calls=[z for z in t if z['function']=='preserve_structural_boundary_neighbors']; predicates=[z['returned']for z in t if z['function']=='structural_boundary_query']
 if c['id'] in ('builder-source','bodybuilder-source'):
  checks['preserve_no_addition']=bool(calls)and all(z['focused']==z['returned']for z in calls);checks['predicate_false']=predicates==[False]
 out.append({'case':c['id'],'checks':checks,'predicates':predicates,'preserve_calls':len(calls)})
(D/'after-fixed-verdicts.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));assert all(all(r['checks'].values())for r in out)
