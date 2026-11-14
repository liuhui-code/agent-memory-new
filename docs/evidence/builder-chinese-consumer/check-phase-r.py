import json
from pathlib import Path
root=Path(__file__).resolve().parents[3]
p=root/'docs/evidence/builder-chinese-consumer';before=json.loads((p/'before-public.json').read_text());after=json.loads((p/'phase-r-after-public.json').read_text());rules=json.loads((p/'phase-r-acceptance.json').read_text());out=[]
for b,a,r in zip(before,after,rules):
 x=b['compact']['query_handoff'];y=a['compact']['query_handoff'];checks={}
 checks['logs_unchanged']=x['log_anchors']==y['log_anchors'];checks['path_unchanged']=x['path_context']==y['path_context']
 checks['no_builder_selection_authority']='builder_declaration_selection' not in y['callable_evidence']
 if r['phase_r'].startswith('unchanged'):
  checks['code_unchanged']=x['code_anchors']==y['code_anchors'];checks['callable_unchanged']=x['callable_evidence']==y['callable_evidence']
 trace=json.loads((p/a['trace']).read_text());ranked=[row for t in trace if t['function']=='rank_callables' for row in (t['returned']or[])]
 checks['target_full_ranked_identity']=all(any(row.get('file_path')==name and all(row.get(k) for k in ['id','symbol_key','source_digest','start_line','end_line','index_generation']) and 'arkts_builder' in str(row.get('callable_roles')) for row in ranked) for name in r['required_target_in_full_ranked'])
 out.append({'family':a['family'],'case':a['case']['id'],'files':[v['file_path']for v in y['code_anchors']],'checks':checks,'ranked_count':len(ranked)})
# English outputs compare accepted fixed842 artifacts, not the earlier pre-consumer red.
e=root/'docs/evidence/builder-positive-consumer'
b=json.loads((e/'final842-public.json').read_text());a=json.loads((e/'phase-r-english-public.json').read_text());english=[]
for x,y in zip(b,a):
 bx=x['compact']['query_handoff'];ay=y['compact']['query_handoff'];english.append({'case':y['case']['id'],'same':all(bx[k]==ay[k]for k in ['code_anchors','callable_evidence','log_anchors','path_context'])})
oldb=json.loads((e/'final842-old-index.json').read_text());olda=json.loads((e/'phase-r-english-old-index.json').read_text())
old=[x['compact']['query_handoff']==y['compact']['query_handoff']for x,y in zip(oldb['cases'],olda['cases'])]
result={'chinese':out,'english':english,'old_index_handoff_unchanged':old,'old_symbols_unchanged':oldb['symbols']==olda['symbols']}
(p/'phase-r-verdicts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('Chinese false',[(x['case'],k)for x in out for k,v in x['checks'].items()if not v]);print('English false',[x for x in english if not x['same']]);print('old',old,'symbols',result['old_symbols_unchanged'])
