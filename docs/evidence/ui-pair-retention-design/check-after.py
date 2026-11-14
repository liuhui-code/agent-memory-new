import json
from pathlib import Path
D=Path(__file__).resolve().parent;p=json.loads((D/'protocol.json').read_text());before=json.loads((D/'before-public.json').read_text());after=json.loads((D/'after-fixed-public.json').read_text());out=[]
for b,a in zip(before,after):
 c=a['case'];x=b['compact']['query_handoff'];y=a['compact']['query_handoff'];checks={}
 checks['raw_handoff_same']=b['raw']['query_handoff']==a['raw']['query_handoff']
 for key in ['log_keywords','log_anchors','path_context','callable_evidence']:
  checks[key+'_same']=x[key]==y[key]
 if c.get('criterion')=='unchanged':checks['whole_compact_handoff_same']=x==y
 else:
  checks['required_files']=set(c['required'])=={z['file_path']for z in y['code_anchors']}
  source=next(f['sources']for f in p['families']if f['id']==a['family']);decls=[r for r in a['symbols']if r.get('symbol_type')=='component'and r['file_path']in c['required']]
  checks['requested_declarations_complete']=all(any(e['start_line']<=r['start_line']<=r['end_line']<=e['end_line']and '\n'.join(source[r['file_path']].splitlines()[r['start_line']-1:r['end_line']])in e['content']for z in y['code_anchors']if z['file_path']==r['file_path']for e in z.get('source_excerpts',[]))for r in decls)
  if c.get('required_owners'):
   checks.pop('requested_declarations_complete')
   checks['same_file_whole_handoff_unchanged']=x==y
   ranges=[r for z in y['code_anchors']for r in z.get('source_ranges',[])]
   checks['both_owner_intervals_retained']=all(any(v.get('symbol')==r['symbol'] and v.get('start_line')==r['start_line'] and v.get('end_line')==r['end_line']for v in ranges)for r in decls)
  checks['all_excerpts_exact']=all(e['content']=='\n'.join(source[z['file_path']].splitlines()[e['start_line']-1:e['end_line']])for z in y['code_anchors']for e in z.get('source_excerpts',[]))
 checks['budget']=a['compact']['output_budget']['estimated_tokens']<=1500
 out.append({'family':a['family'],'case':c['id'],'checks':checks,'budget':a['compact']['output_budget']})
(D/'after-fixed-verdicts.json').write_text(json.dumps(out,indent=2));print([(r['case'],k)for r in out for k,v in r['checks'].items()if not v]);assert len(out)==19 and all(all(r['checks'].values())for r in out)
