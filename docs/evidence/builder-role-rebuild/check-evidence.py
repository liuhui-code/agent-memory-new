# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
from pathlib import Path
D=Path(__file__).resolve().parent
load=lambda name:json.loads((D/name).read_text())
fields=['symbol_key','file_path','qualified_name','symbol','symbol_type','owner_name','owner_kind','start_line','end_line','source_digest','signature']
identity=lambda rows:sorted(json.dumps({k:r.get(k) for k in fields},sort_keys=True)for r in rows)
roles=lambda rows:sorted((r['file_path'],r['qualified_name'])for r in rows if 'arkts_builder' in json.loads(r['callable_roles']or'[]'))
a,b,c=[load('activation-'+p+'.json')for p in ['before','code-only','merged']]
assert identity(a)==identity(b)==identity(c)
assert roles(a)==roles(b)==[]
expected=sorted(tuple(x)for x in load('protocol.json')['expected'])
assert roles(c)==expected
summary={'activation':{'identity_fields':fields,'unchanged':True,'before':roles(a),'code_only':roles(b),'merged':roles(c)},'compatibility':[]}
for before,after in zip(load('compatibility-before.json'),load('compatibility-merged.json')):
    assert before['case']==after['case']
    old,new=before['compact'],after['compact']
    oa,na=[v['query_handoff']['code_anchors']for v in(old,new)]
    assert oa==na
    op,np=[v['query_handoff']['callable_evidence'].get('primary') for v in(old,new)]
    primary_fields=['file_path','symbol','source_range']
    assert {k:op.get(k) for k in primary_fields}=={k:np.get(k) for k in primary_fields}
    paths={a['file_path']for a in na}
    passed=paths==set(after['case']['expected'])
    row={'id':after['case']['id'],'paths':sorted(paths),'pass':passed,'anchors_identical':True,'before_budget':old['output_budget'],'after_budget':new['output_budget']}
    summary['compatibility'].append(row)
(D/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
