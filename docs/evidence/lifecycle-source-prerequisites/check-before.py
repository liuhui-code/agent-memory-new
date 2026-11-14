import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;p=json.loads((D/'protocol.json').read_text());observed=json.loads((D/'before-public.json').read_text());results=[]
for family in p['families']:
 example=next(x for x in observed if x['family']==family['id'] and (x['case']['id']=='lifecycle-1' or family['id']!='original-four'))
 trace=json.loads((D/example['trace']).read_text());focus=next(x for x in trace if x['function']=='focus_code_candidates');edges=json.loads((D/('before-edges-'+family['id']+'.json')).read_text())
 for path,source in family['sources'].items():
  if path not in {'BufferSession.ets','EditorSession.ets'}:continue
  owner=path[:-4];digest=hashlib.sha256(source.encode()).hexdigest();rows=[r for r in example['symbols']if r['file_path']==path];by={r['symbol']:r for r in rows};a,b=by['onMount'],by['reload']
  matching=[]
  for e in edges:
   if(e['source_type'],e['source_id'],e['relation'],e['target_type'],e['target_id'])!=('code_symbol',a['id'],'calls','code_symbol',b['id']):continue
   try:v=json.loads(e['evidence'])
   except(ValueError,TypeError):continue
   if e['valid_to']is None and e['evidence_kind']=='static_semantic_calls' and v.get('schema_version')=='semantic-evidence/v1' and v.get('source_digest')==digest and v.get('adapter')==a['semantic_adapter']==b['semantic_adapter'] and e['extractor_version']=='semantic-index:v1/'+a['semantic_adapter'] and v.get('line')==4:matching.append(e)
  inputs=[r for r in focus['items']if r['file_path']==path]
  checks={'file_in_pool':any(r.get('kind')=='file' and r.get('source_digest')==digest for r in inputs),'method_in_pool':any(r.get('kind')=='symbol' and r.get('symbol_key') and r.get('source_digest')==digest for r in inputs),'four_current_typed_rows':len(rows)==4 and all(r['source_digest']==digest and r['index_generation']==1 and r['symbol_key']for r in rows),'correct_ranges':[(by[k]['start_line'],by[k]['end_line'])for k in [owner,'onMount','reload','commit']]==[(1,12),(3,5),(6,8),(9,11)],'one_current_exact_call_edge':len(matching)==1,'no_log_path':not example['raw']['query_handoff']['log_anchors'] and not example['raw']['query_handoff']['path_context']['activated']}
  results.append({'family':family['id'],'owner':owner,'checks':checks,'edge':matching})
main=next(x for x in observed if x['case']['id']=='lifecycle-1');results.append({'main_red': 'BufferSession.ets' not in [a['file_path']for a in main['compact']['query_handoff']['code_anchors']]})
(D/'before-qualification-checks.json').write_text(json.dumps(results,indent=2));print([(r.get('owner'),r.get('checks',r))for r in results]);assert all(all(r['checks'].values())for r in results if 'checks'in r);assert results[-1]['main_red']
