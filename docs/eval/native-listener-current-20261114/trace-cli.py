# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import sys,json,runpy
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO/'tools'))
import agent_memory_runtime.query_hierarchical_localization as loc
out=Path(__file__).resolve().parent/'rank-trace.jsonl'
original=loc.rank_callables
fields=('file_path','symbol','signature','start_line','end_line','owner_name','owner_kind','method_evidence','string_evidence','mechanism_evidence','direct_score','file_rank','localization_score','evidence_score','localization_reasons','typed_contract_match','source_operation_match','target_owner_kind_match')
def traced(items, query, use_direct_score=True):
 result=original(items,query,use_direct_score)
 with out.open('a') as f:f.write(json.dumps({'query':query,'candidates':[{k:x.get(k) for k in fields} for x in result]},ensure_ascii=False)+'\n')
 return result
loc.rank_callables=traced
runpy.run_path(str(REPO/'tools/agent_memory.py'),run_name='__main__')
