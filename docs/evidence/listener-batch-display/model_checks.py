# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy,json,sys,subprocess
from pathlib import Path
candidate=Path(sys.argv[1]);D=Path(sys.argv[2]);ROOT=D.parents[2];sys.path.insert(0,str(candidate))
from tools.agent_memory_runtime.semantic_models import SemanticBatch,SemanticEntity,SemanticMechanism
from tools.agent_memory_runtime.semantic_mechanism_evidence import mechanism_evidence_payload,mechanism_search_terms
from tools.agent_memory_runtime.listener_experiment_support import pack
from tools.agent_memory_runtime.listener_experiment_prototype import validate_witness
rows=json.loads((D/'merged-list.json').read_text());row=next(r for r in rows if json.loads(r.get('typed_invocation_witnesses')or'[]'))
witness=json.loads(row['typed_invocation_witnesses'])[0]
e=SemanticEntity(key=row['symbol_key'],file_path=row['file_path'],name=row['symbol'],kind=row['symbol_type'],qualified_name=row['qualified_name'],signature=row['signature'],start_line=row['start_line'],end_line=row['end_line'])
mechanisms=[SemanticMechanism(**m)for m in json.loads(row['mechanism_evidence'])]
def batch(w):return SemanticBatch('experiment','2','ArkTS',[],{row['file_path']:row['source_digest']},[e],[],mechanisms,typed_invocation_witnesses=w)
from tools.agent_memory_runtime.listener_batch_support import normalize,optional_batch
from tools.agent_memory_runtime.listener_display import diagnose,display
results=[]
def check(name,fn):
    try:fn();results.append({'id':name,'pass':True})
    except Exception as ex:results.append({'id':name,'pass':False,'error':repr(ex)})
def rejected(v):
    try:normalize(v)
    except ValueError:return
    raise AssertionError('not rejected')
def dup():assert normalize([witness]*64)==[witness]
check('64-exact-duplicates-one',dup)
check('65-before-iterate',lambda:rejected([None]*65))
check('wrong-container',lambda:rejected({}))
check('byte-cap',lambda:rejected([{'oversized':'x'*65536}]))
def conflict():
    w=copy.deepcopy(witness);w['invocation']['member']='different'
    rejected([witness,w])
check('conflict-identity',conflict)
def preservation(values,entity=e):
    b=SemanticBatch('experiment','2','ArkTS',[],{row['file_path']:row['source_digest']},[entity],[],mechanisms,typed_invocation_witnesses=values)
    b.validate();assert b.typed_invocation_witnesses==[]
    assert b.entities==[entity] and b.mechanisms==batch([]).validate().mechanisms
for name,values in [('conflict',[witness,{**witness,'version':'other'}]),('overcount',[witness]*65),('wrongtype',True)]:
    check('legacy-preserved-'+name,lambda values=values:preservation(values))
def kind():
    entity=copy.deepcopy(e);entity.kind='class';preservation([witness],entity)
check('noncallable-legacy-preserved',kind)
for name,change in [('bool',lambda w:w['formal'].update(index=True)),('identity',lambda w:w['source'].update(symbol_key='wrong'))]:
    def mutated(change=change):
        w=copy.deepcopy(witness);change(w);preservation([w])
    check(name,mutated)
work=Path(json.loads((D/'workspace.json').read_text())['workspace']);root=work/'fixed'
def current():assert diagnose(row,root)['status']=='current-source-slices-checked'
check('current-source',current)
def unknown(r):assert diagnose(r,root)['status']=='unknown'
for name,value in [('absolute','/tmp/unauthorized.ets'),('escape','../outside.ets'),('missing','missing.ets')]:
    check(name,lambda value=value:unknown({**row,'file_path':value}))
def unknown(r):assert diagnose(r,root)['status']=='unknown'
# Repeat definitions above were not invoked until check: define unknown before actual controls.

check('stale-digest',lambda:unknown({**row,'source_digest':'0'*64}))
check('old-index',lambda:unknown({**row,'typed_invocation_witnesses':None}))
check('malformed',lambda:unknown({**row,'typed_invocation_witnesses':'broken'}))
def version():
    w=copy.deepcopy(witness);w['version']='unknown';unknown({**row,'typed_invocation_witnesses':json.dumps([w])})
check('version',version)
def symlink():
    path=root/'escape.ets';path.symlink_to(work/'outside.ets');(work/'outside.ets').write_text('outside')
    unknown({**row,'file_path':'escape.ets'})
check('symlink-escape',symlink)
def caps():
    rows=[{k:copy.deepcopy(v)for k,v in row.items()if k!='experimental_listener_diagnostic'}for _ in range(100)];out=display(rows,root)
    diagnostics=[r['experimental_listener_diagnostic']for r in out if 'experimental_listener_diagnostic'in r]
    assert len(out)==100 and len(diagnostics)<=64
    assert len(json.dumps(diagnostics,ensure_ascii=False).encode())<=65536
    assert all(len(json.dumps(d,ensure_ascii=False).encode())<=4096 for d in diagnostics)
check('list-diagnostic-caps',caps)
(D/'model-results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
