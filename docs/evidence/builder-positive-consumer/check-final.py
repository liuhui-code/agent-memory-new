# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;p=json.loads((D/'protocol.json').read_text())
a=json.loads((D/'before-public.json').read_text());b=json.loads((D/'final842-public.json').read_text());assert len(a)==len(b)==24
checks=[]
for x,y in zip(a,b):
 assert x['family']==y['family'] and x['case']==y['case'];c=x['case'];h=x['compact']['query_handoff'];g=y['compact']['query_handoff']
 item={'family':x['family'],'id':c['id'],'before_paths':[v['file_path']for v in h['code_anchors']],'after_paths':[v['file_path']for v in g['code_anchors']],'checks':{}}
 def check(name,value):item['checks'][name]=bool(value);assert value,(c['id'],name)
 check('log_anchors_equal',h['log_anchors']==g['log_anchors']);check('path_context_equal',h['path_context']==g['path_context'])
 check('within_1500',y['compact']['output_budget']['estimated_tokens']<=1500)
 if not c['authority'] or c['id']=='unknown-role':
  check('entire_code_anchors_equal',h['code_anchors']==g['code_anchors']);check('entire_callable_evidence_equal',h['callable_evidence']==g['callable_evidence'])
  check('no_new_role_annotation','builder_declaration_selection'not in g['callable_evidence'])
 else:
  m=g['callable_evidence'].get('builder_declaration_selection',{});check('non_exhaustive',m.get('scope')=='retrieved_candidates_non_exhaustive');check('uncertain',g['callable_evidence']['certainty']=='uncertain');check('not_behavior_certificate',m.get('behavior_certified')is False)
  expected=c.get('expected_symbols')or ['RibbonCanvas.renderStrip'];check('all_known_count',m['known_matches']==len(expected))
  for symbol in expected:
   row=next(v for v in y['symbols']if v.get('qualified_name')==symbol and 'arkts_builder'in str(v.get('callable_roles')))
   anchors=[v for v in g['code_anchors']if v['file_path']==row['file_path']]
   check('range_'+symbol,any(r.get('symbol')==row['symbol']and r['start_line']==row['start_line']and r['end_line']==row['end_line']for v in anchors for r in v.get('source_ranges',[])))
   check('body_'+symbol,any(e['start_line']<=row['start_line']<=row['end_line']<=e['end_line']and not e.get('truncated')for v in anchors for e in v.get('source_excerpts',[])))
  if c['id']=='builder-role':check('fixed_original_independent_red',set(item['after_paths'])==set(c['expected']))
 item['tokens']=y['compact']['output_budget']['estimated_tokens'];checks.append(item)
old=json.loads((D/'before-old-index.json').read_text());new=json.loads((D/'final842-old-index.json').read_text());assert old['symbols']==new['symbols'];oldchecks=[]
for x,y in zip(old['cases'],new['cases']):
 h=x['compact']['query_handoff'];g=y['compact']['query_handoff'];assert h['code_anchors']==g['code_anchors']and h['callable_evidence']==g['callable_evidence']and h['log_anchors']==g['log_anchors']and h['path_context']==g['path_context'];oldchecks.append({'id':x['case']['id'],'unchanged':True})
W=D.parents[3]/'builder-consumer-execution';hashes=[]
for f in p['families']:
 for name,s in f['sources'].items():
  content=(W/('final842-'+f['id'])/name).read_bytes();assert content==s.encode();hashes.append({'family':f['id'],'file':name,'sha256':hashlib.sha256(content).hexdigest()})
(D/'final842-verdicts.json').write_text(json.dumps({'source_sha':'842f73b','cases':checks,'old_index':oldchecks,'source_hashes':hashes},indent=2,ensure_ascii=False))
print('24 fixed public controls pass; 5 old-index controls unchanged; all source bytes equal frozen protocol.')
print('Max tokens',max(x['tokens']for x in checks))
