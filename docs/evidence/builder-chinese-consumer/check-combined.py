import json
from pathlib import Path
root=Path(__file__).resolve().parents[3];p=root/'docs/evidence/builder-chinese-consumer';proto=json.loads((p/'protocol.json').read_text());before=json.loads((p/'phase-r-after-public.json').read_text());after=json.loads((p/'combined-zh-public.json').read_text());out=[]
for b,a in zip(before,after):
 c=a['case'];x=b['compact']['query_handoff'];y=a['compact']['query_handoff'];checks={'logs_unchanged':x['log_anchors']==y['log_anchors'],'path_unchanged':x['path_context']==y['path_context']}
 if c['authority']:
  checks['exact_expected_files']=set(v['file_path']for v in y['code_anchors'])==set(c['expected'])
  mark=y['callable_evidence'].get('builder_declaration_selection',{});checks['bounded_marker']=mark.get('kind')=='positive_builder_direct_modifiers' and mark.get('behavior_certified') is False and y['callable_evidence'].get('certainty')=='uncertain'
  family=next(f for f in proto['families']if f['id']==a['family']);full=[]
  for row in a['symbols']:
   if row['file_path'] not in c['expected'] or 'arkts_builder' not in str(row.get('callable_roles')):continue
   lines=family['sources'][row['file_path']].splitlines();start=row['start_line'];end=row['end_line'];body='\n'.join(lines[start-1:end])
   anchors=[v for v in y['code_anchors']if v['file_path']==row['file_path']]
   full.append(any(any(e['start_line']<=start and e['end_line']>=end and body in e['content']for e in v.get('source_excerpts',[]))for v in anchors))
  checks['all_expected_methods_complete']=bool(full) and all(full)
 else:
  checks['code_unchanged']=x['code_anchors']==y['code_anchors'];checks['callable_unchanged']=x['callable_evidence']==y['callable_evidence']
 out.append({'family':a['family'],'case':c['id'],'files':[v['file_path']for v in y['code_anchors']],'checks':checks,'output_budget':a['compact'].get('output_budget')})
e=root/'docs/evidence/builder-positive-consumer';b=json.loads((e/'phase-r-english-public.json').read_text());a=json.loads((e/'combined-en-public.json').read_text());english=[]
for x,y in zip(b,a):
 bx=x['compact']['query_handoff'];ay=y['compact']['query_handoff'];english.append({'case':y['case']['id'],'same':all(bx[k]==ay[k]for k in ['code_anchors','callable_evidence','log_anchors','path_context'])})
oldb=json.loads((e/'phase-r-english-old-index.json').read_text());olda=json.loads((e/'combined-en-old-index.json').read_text());old=[x['compact']['query_handoff']==y['compact']['query_handoff']for x,y in zip(oldb['cases'],olda['cases'])]
r={'chinese':out,'english':english,'old_handoff_same':old,'old_symbols_same':oldb['symbols']==olda['symbols']};(p/'combined-verdicts.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('Chinese false',[(x['case'],k)for x in out for k,v in x['checks'].items()if not v]);print('English false',[x for x in english if not x['same']]);print('old',old,r['old_symbols_same'])
