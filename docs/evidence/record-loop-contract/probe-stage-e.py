"""Saved-payload capacity diagnostic only; not a serving-path after or authority."""
import copy, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools'))
from agent_memory_runtime.context_budget import synchronize_estimate
from agent_memory_runtime.context_sufficiency import diagnosis_sufficiency
D=Path(__file__).parent
rows=json.loads((D/'stage-c-merge-public.json').read_text());out=[]
for r in rows:
 cohort=r['cohort'];case=r['case'];cid=case['id']
 if not (cid in ('contextual-result','contextual-accumulator') or (cohort=='two-positive-result' and cid=='direct-result')):continue
 baseline=r['compact'];trial=copy.deepcopy(baseline);h=trial['query_handoff'];anchors=[]
 trace=json.loads((D/f'stage-c-merge-trace-{cohort}-{cid}-compact.json').read_text())
 pool=trace[0]['gated']['matches']['wiki_matches']
 for path in case['required']:
  method=next(x for x in pool if x.get('file_path')==path and x.get('symbol_type') in ('function','method'))
  source=(Path(r['raw']['project_path'])/path).read_text();assert hashlib.sha256(source.encode()).hexdigest()==method['source_digest']
  lo,hi=method['start_line'],method['end_line'];span={'symbol':method['symbol'],'start_line':lo,'end_line':hi}
  anchors.append({'file_path':path,'symbol':method['symbol'],'symbol_type':'method','record_ids':[method['id']], 'record_type':'code_symbol','source_ranges':[span], 'read_window':{'start_line':lo,'end_line':hi},'role':'primary','source_excerpts':[dict(span,content='\n'.join(source.splitlines()[lo-1:hi]),source='validated_request_snapshot',selection_reason='complete_direct_loop_result_method',focus_line=None,truncated=False)]})
 h['code_anchors']=anchors
 h['callable_evidence']={'schema_version':'agent-callable-evidence/v1','certainty':'non_exhaustive','primary':None,'alternatives':[], 'boundary':'positive_direct_syntax_not_unique_owner_or_runtime_causality'}
 h['source_excerpt_policy']={'source':'validated_request_snapshot','body_persisted':False,'excerpt_count':len(anchors),'excerpt_chars':sum(len(a['source_excerpts'][0]['content']) for a in anchors)}
 trial['evidence_gaps']=[x for x in trial['evidence_gaps'] if x not in ('no_code_anchor','limited_code_anchor_diversity')] + (['limited_code_anchor_diversity'] if len(anchors)<3 else [])
 trial['sufficiency']=diagnosis_sufficiency(h,trial['evidence_gaps'],trial.get('source_freshness'))
 synchronize_estimate(trial)
 restored=copy.deepcopy(trial)
 for k in ('code_anchors','callable_evidence','source_excerpt_policy'):
  if k in baseline['query_handoff']:restored['query_handoff'][k]=copy.deepcopy(baseline['query_handoff'][k])
  else:restored['query_handoff'].pop(k,None)
 for k in ('evidence_gaps','sufficiency','output_budget'):restored[k]=copy.deepcopy(baseline[k])
 assert restored==baseline
 out.append({'cohort':cohort,'id':cid,'kind':'hypothetical_saved_payload_capacity_not_public_after','baseline_tokens':baseline['output_budget']['estimated_tokens'],'hypothetical_tokens':trial['output_budget']['estimated_tokens'],'fits_1500':trial['output_budget']['estimated_tokens']<=1500,'non_code_objects_equal':restored==baseline,'raw_log_count':len(r['raw']['query_handoff']['log_anchors']),'compact_log_count':len(baseline['query_handoff']['log_anchors']),'hypothetical_payload':trial})
(D/'stage-e-capacity.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print([(x['cohort'],x['id'],x['hypothetical_tokens'],x['fits_1500'])for x in out])
