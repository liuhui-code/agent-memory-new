"""Internal saved-payload budget arithmetic, NOT a public serving trial."""
import json,copy,sys
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(ROOT))
from tools.agent_memory_runtime.context_compact import compact_code_anchor
from tools.agent_memory_runtime.context_budget import estimate_payload_tokens,enforce_budget,finalize_budget,synchronize_estimate
saved=json.loads((ROOT/'docs/evidence/cross-layer-current/public.json').read_text())[0]
payload=copy.deepcopy(saved['compact']);original=copy.deepcopy(payload)
required=[('src/gateways/JobTransport.ets','submit',4,12),('src/pages/JobDispatchPage.ets','onClick',7,14)]
expected={}
for file,symbol,start,end in required:
 row=next(r for r in saved['raw']['query_handoff']['code_anchors']if r.get('file_path')==file and r.get('symbol')==symbol and r.get('start_line')==start and r.get('end_line')==end)
 anchor=compact_code_anchor(row);lines=(ROOT/'docs/eval/fixtures/system-capability'/file).read_text().splitlines();content='\n'.join(lines[start-1:end]);expected[file]=content
 anchor['source_excerpts']=[dict(symbol=symbol,start_line=start,end_line=end,content=content,source='current_worktree',selection_reason='anchor_range',truncated=False)]
 payload['query_handoff']['code_anchors'].append(anchor)
pre=estimate_payload_tokens(payload);before=copy.deepcopy(payload)
paths=frozenset(a['file_path']for a in payload['query_handoff']['code_anchors'])
enforce_budget(payload,1500,reserve_tokens=0,protected_paths=paths);finalize_budget(payload,1500,truncated=True)
h=payload['query_handoff'];oh=original['query_handoff']
checks={'original_anchor_unchanged':h['code_anchors'][0]==oh['code_anchors'][0], 'all_three_paths':set(a['file_path']for a in h['code_anchors'])==set(paths), 'two_full_bodies':all(any(a['file_path']==file and any(e.get('content')==content and not e.get('truncated')for e in a.get('source_excerpts',[]))for a in h['code_anchors'])for file,content in expected.items()),'log_path_same':all(h.get(k)==oh.get(k)for k in ['log_keywords','log_anchors','path_context']), 'relation_hints_same':h.get('relation_hints')==oh.get('relation_hints')}
result={'classification':'internal saved-payload diagnostic; no CLI/permission/new fixture','saved_base':'cdb8f39','normal_tokens':original['output_budget']['estimated_tokens'],'unminimized_tokens':pre,'after_existing_budget':payload['output_budget'],'checks':checks,'before_added':before,'after_existing_budget_payload':payload}
restored=copy.deepcopy(payload)
for key in ['log_keywords','log_anchors','path_context']:
 restored['query_handoff'][key]=copy.deepcopy(original['query_handoff'][key])
synchronize_estimate(restored)
result['diagnostic_restore_original_log_path']={'estimated_tokens':estimate_payload_tokens(restored),'payload':restored,'note':'internal feasibility only; existing budget pass did trim keywords, so this restore is not current serving behavior'}
(D/'budget-audit.json').write_text(json.dumps(result,indent=2));print(result['normal_tokens'],pre,result['after_existing_budget'],checks)
