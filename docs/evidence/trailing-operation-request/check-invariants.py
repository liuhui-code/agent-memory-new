# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import dataclasses,json,sys
from pathlib import Path
from types import SimpleNamespace
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D.parents[2]))
from tools.agent_memory_runtime.semantic_ecma import parse_source
old=json.loads((D/'source-before.json').read_text());new=json.loads((D/'producer-source.json').read_text())
assert len(old)==len(new)==15
for a,b in zip(old,new):
 assert a['id']==b['id'];assert a['entities']==b['entities'];assert b['mechanisms'][:len(a['mechanisms'])]==a['mechanisms'];assert a['gaps']==b['gaps']
res=[]
for c in json.loads((D/'capacity-protocol.json').read_text())['controls']:
 s='@Component\nexport struct Control {\n build() {\n'+c['body']+'\n }\n}\n'
 r=parse_source(SimpleNamespace(root=Path('/tmp')),Path('/tmp/Control.ets'),s.encode(),'ArkTS',True)
 assert len(r.mechanisms)==c['expected_old_count'];assert all(not m.detail.startswith('call:.')for m in r.mechanisms)
 res.append({'id':c['id'],'mechanisms':[dataclasses.asdict(m)for m in r.mechanisms]})
(D/'producer-capacity.json').write_text(json.dumps(res,indent=2))
p=json.loads((D/'producer-activation.json').read_text());assert p['before']==p['code_only'];a={v['symbol_key']:v for v in p['before']};b={v['symbol_key']:v for v in p['after']};assert a.keys()==b.keys()
for k in a:
 for f in ['symbol_key','qualified_name','signature','start_line','end_line','source_digest','callable_roles','method_evidence','calls','evidence_class']:assert a[k][f]==b[k][f]
old=json.loads((D/'public-before.json').read_text());new=json.loads((D/'producer-public.json').read_text());out=[]
for a,b in zip(old,new):
 h=a['compact']['query_handoff'];g=b['compact']['query_handoff'];same=a['paths']==b['paths']
 row={'id':a['id'],'query':a['query'],'before_paths':a['paths'],'after_paths':b['paths'],'frozen_required_path_check':b['passed_frozen_path_check'],'same_code_owner_paths':same,'same_log_anchors':h['log_anchors']==g['log_anchors'],'same_path_context':h['path_context']==g['path_context']}
 row['preservation_control_pass']=all(row[k]for k in ['same_code_owner_paths','same_log_anchors','same_path_context'])if a['id'] in ['quoted','negative_conflict','unknown']else None;out.append(row)
(D/'producer-fixed-control-verdicts.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
print('Candidate d06114c: 15 source prefix/entity/gap invariants pass; cap counts 8/16/1 unchanged. Public activation stable keys/ranges/digests/roles pass, code-only rows identical; SQL IDs may reinsert. Fixed quote/conflict preservation FAIL as recorded; candidate rejected.')
