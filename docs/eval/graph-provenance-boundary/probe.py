# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tools.agent_memory_runtime.query_graph_neighbors import promote_neighbor,neighbor_item,boost_match
root=Path(__file__).resolve().parent
p=json.loads((root/'protocol.json').read_text())
assert not (root/'observation.json').exists()
origin=tuple(p['origin']);neighbor=tuple(p['neighbor']);out=[]
for score in p['neighbor_scores']:
 edge=copy.deepcopy(p['edge']);candidates={}
 matched={origin:p['origin_score'],neighbor:score}
 promote_neighbor(candidates,matched,origin,neighbor,edge,'passes_property',False)
 row={'id':22,'file_path':'Child.ets','symbol':'Child','symbol_type':'component','start_line':1,'end_line':5,'summary':'component','business_terms':[]}
 target={**row,'kind':'symbol','score':score,'match_reasons':['symbol_summary']}
 evidence=neighbor_item(row,candidates[neighbor]) if neighbor in candidates else None
 if evidence is not None:boost_match(target,evidence)
 out.append({'existing_score':score,'candidates':[[list(k),list(v)]for k,v in candidates.items()],'resolved_neighbor_item':evidence,'boosted_existing':target,'edge_unchanged':edge==p['edge'],'matched_unchanged':matched=={origin:p['origin_score'],neighbor:score}})
(root/'observation.json').write_text(json.dumps(out,indent=2))
