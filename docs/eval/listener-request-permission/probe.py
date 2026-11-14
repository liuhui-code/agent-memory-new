# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json, sys
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parents[2]))
from tools.agent_memory_runtime.text import identifier_tokens
from tools.agent_memory_runtime.query_typed_contract import classify_contract
p=json.loads((D/'protocol.json').read_text()); rows=[]
for c in p['cases']:
 d=classify_contract(c['query'])
 expected=(d is not None and d['kind']==c['existing_kind']) if 'existing_kind' in c else d==c['existing_descriptor']
 rows.append({'id':c['id'],'existing_descriptor':d,'descriptor_expected':expected,'member_tokens':{m:identifier_tokens(m) for m in c['members']},'overlap_members':[m for m in c['members'] if c['selector'] in identifier_tokens(m)],'safe_token_authority':False})
(D/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
