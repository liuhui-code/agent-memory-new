from pathlib import Path
import sys,runpy,json
r=Path(__file__).resolve().parent.parent/'repo';sys.path.insert(0,str(r/'tools'))
trace=[];names={'recall_table_candidates','fts_table_ids','fts_ids','fielded_passage_rankings','fielded_serving_candidates','merge_lane_ids','fetch_rows_by_ids','collect_matches_with_audit','gate_matches_by_intent','limited_matches','focus_code_candidates','diverse_code_matches','bind_validation_field_context','bind_logs','validation_field_scope','append_field_alternatives','qualify_graph_field_navigation'}
keys={'id','record_id','file_path','symbol','kind','score','match_reasons','recall_lanes','source_type','channel','record_type'}
def clean(x):
 if hasattr(x,'__dict__'):return clean(vars(x))
 if isinstance(x,dict):
  ks=keys.intersection(x)if 'file_path'in x else x.keys()
  return {str(k):clean(x[k])for k in ks}
 if isinstance(x,(list,tuple,set,frozenset)):return [clean(v)for v in x]
 return x if x is None or isinstance(x,(str,int,float,bool))else str(type(x))
def profile(f,e,a):
 if e=='return'and f.f_code.co_name in names:
  trace.append({'name':f.f_code.co_name,'locals':{k:clean(v)for k,v in f.f_locals.items()if k in ('query','table_name','table','source_type','limit','ids','lanes','items','pool','permission','no_logs','focus_terms','broad_limit','broad_saturated')},'result':clean(a)})
out=Path(sys.argv.pop(1));sys.argv=[str(r/'tools/agent_memory.py'),*sys.argv[1:]];sys.setprofile(profile)
try:runpy.run_path(sys.argv[0],run_name='__main__')
finally:sys.setprofile(None);out.write_text(json.dumps(trace,ensure_ascii=False,indent=2))
