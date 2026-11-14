# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(ROOT))
from tools.agent_memory_runtime.query_hierarchical_localization import select_diverse_callables,compact_callable,valid_source_ranges,MAX_CALLABLES
from tools.agent_memory_runtime.query_callable_passage_portfolio import query_supported,support_reasons,range_lookup,identity
from tools.agent_memory_runtime.query_language import positive_retrieval_query,excluded_code_candidate
from tools.agent_memory_runtime.query_target_scope import classify_target_scope,permits_cross_file_portfolio
out=[]
for c in json.loads((D/'public.json').read_text()):
    traces=json.loads((D/(c['id']+'-raw-trace.json')).read_text());ranked=[t['result']for t in traces if t['function']=='rank_callables'][-1]
    q=c['query'];selected=select_diverse_callables(ranked,MAX_CALLABLES);projected=[compact_callable(i)for i in selected];ranges=range_lookup(valid_source_ranges(selected,positive_retrieval_query(q)))
    primary=c['raw']['query_handoff']['callable_evidence']['primary'];assert(projected[0]['file_path'],projected[0]['symbol'])==(primary['file_path'],primary['symbol'])
    out.append({'variant':c['id'],'kind':'internal helper replay over saved ranked result, not new CLI','scope':classify_target_scope(q),'permits_crossfile':permits_cross_file_portfolio(classify_target_scope(q)),'matches_public_primary':True,'eligibility':[{'id':i['symbol_id'],'path':i['file_path'],'symbol':i['symbol'],'range':ranges.get(identity(i)),'support_reasons':support_reasons(i,q),'query_supported':query_supported(i,q),'excluded':excluded_code_candidate(q,i)}for i in projected],'actual_portfolio':c['raw']['query_handoff']['callable_evidence'].get('passage_portfolio'),'actual_path':c['raw']['query_handoff']['path_context']})
(D/'portfolio-conditions.json').write_text(json.dumps(out,indent=2))
print(json.dumps([{'variant':c['variant'],'scope':c['scope'],'required':[r for r in c['eligibility']if r['path']in ['src/gateways/JobTransport.ets','src/pages/JobDispatchPage.ets']]}for c in out],indent=2))
