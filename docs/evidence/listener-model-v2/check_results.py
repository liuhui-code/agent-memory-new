# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
from pathlib import Path
D=Path(__file__).resolve().parent
load=lambda name:json.loads((D/name).read_text())
fields=['symbol_key','file_path','qualified_name','symbol','symbol_type','owner_name','owner_kind','start_line','end_line','source_digest','signature']
identity=lambda rows:sorted(json.dumps({k:r.get(k)for k in fields},sort_keys=True)for r in rows)
a,b,c=[load(n+'-list.json')for n in ['before','code-only','merged']]
assert identity(a)==identity(b)==identity(c)
def facts(rows):return [w for r in rows for w in json.loads(r.get('typed_invocation_witnesses')or'[]')]
assert facts(a)==facts(b)==[] and len(facts(c))==2
for old,new in zip(sorted(a,key=lambda r:r['symbol_key'] or ''),sorted(c,key=lambda r:r['symbol_key'] or '')):
    assert old['mechanism_evidence']==new['mechanism_evidence']
    side=new.get('typed_invocation_witnesses')
    assert len(new['mechanism_evidence'].encode())+(len(side.encode())if side is not None else 0)<=4096
summary={'stable_identity_fields':fields,'installation_only_unknown':True,'merge_witnesses':len(facts(c)),'queries':[]}
for before,after in zip(load('before-queries.json'),load('after-queries.json')):
    assert before['case']==after['case']
    u,v=[x['compact']['query_handoff']for x in [before,after]]
    old,new=u['code_anchors'],v['code_anchors'];assert len(old)==len(new)
    changes=[]
    for x,y in zip(old,new):
        changed={k:[x.get(k),y.get(k)]for k in x.keys()|y.keys()if x.get(k)!=y.get(k)}
        assert set(changed)<= {'record_ids'}
        changes.append(changed)
    for k in ['file_path','symbol','source_range']:
        assert u['callable_evidence']['primary'].get(k)==v['callable_evidence']['primary'].get(k)
    paths={x['file_path']for x in new};expected={after['case']['expected']}
    body=json.dumps(new,ensure_ascii=False)
    summary['queries'].append({'query':after['case']['query'],'pass':paths==expected and after['case']['body']in body,'paths':sorted(paths),'anchor_changes':changes,'body_range_primary_identical':True,'before_budget':before['compact']['output_budget'],'after_budget':after['compact']['output_budget']})
summary['indexed_controls']=[{'id':x['id'],'pass':x['pass'],'expected':x['expected'],'actual':x['actual']}for x in load('indexed-controls.json')]
long=next(x for x in load('indexed-controls.json')if x['id']=='overcap-file')
old=load('length-baseline.json');assert identity(old)==identity(long['rows'])
assert sorted(r['mechanism_evidence'] for r in old)==sorted(r['mechanism_evidence']for r in long['rows'])
summary['length_legacy_preserved']=True
summary['model_checks']=load('model-results.json')
(D/'summary.json').write_text(json.dumps(summary,indent=2));print('Identity/body/primary assertions passed; source fact failures retained:',[x['id']for x in summary['indexed_controls']if not x['pass']])
