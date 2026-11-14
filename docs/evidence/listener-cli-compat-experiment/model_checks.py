# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Executed in the disposable interpreter only, using actual indexed records."""
import copy,json,sys,subprocess
from pathlib import Path
candidate=Path(sys.argv[1]);D=Path(sys.argv[2]);ROOT=D.parents[2]
sys.path.insert(0,str(candidate))
from tools.agent_memory_runtime.semantic_models import SemanticBatch,SemanticEntity,SemanticMechanism
from tools.agent_memory_runtime.semantic_mechanism_evidence import mechanism_evidence_payload
rows=json.loads((D/'merged-list.json').read_text())
row=next(r for r in rows if any(m.get('typed_invocation_witness')for m in json.loads(r.get('mechanism_evidence')or'[]')))
records=json.loads(row['mechanism_evidence']);record=next(m for m in records if m.get('typed_invocation_witness'))
e=SemanticEntity(key=row['symbol_key'],file_path=row['file_path'],name=row['symbol'],kind=row['symbol_type'],qualified_name=row['qualified_name'],signature=row['signature'],start_line=row['start_line'],end_line=row['end_line'])
def batch(m):return SemanticBatch('experiment','1','ArkTS',[],{row['file_path']:row['source_digest']},[e],[],[SemanticMechanism(**m)])
results=[]
def check(name,fn):
    try:fn();results.append({'id':name,'pass':True})
    except Exception as ex:results.append({'id':name,'pass':False,'error':repr(ex)})
def same():
    b=batch(record);encoded=b.to_dict();assert SemanticBatch.from_dict(encoded).to_dict()==encoded
    (D/'experimental-batch.json').write_text(json.dumps(encoded,indent=2))
check('new-roundtrip',same)
def legacy():
    old=copy.deepcopy(record);old.pop('typed_invocation_witness');encoded=batch(old).to_dict();encoded['schema_version']='semantic-index/v1'
    b=SemanticBatch.from_dict(encoded);assert b.mechanisms[0].typed_invocation_witness is None
check('legacy-unknown',legacy)
def old_reader():
    code='import sys,json;sys.path.insert(0,sys.argv[1]);from tools.agent_memory_runtime.semantic_models import SemanticBatch;SemanticBatch.from_dict(json.load(open(sys.argv[2])))'
    p=subprocess.run([sys.executable,'-c',code,str(ROOT),str(D/'experimental-batch.json')],cwd='/tmp',capture_output=True,text=True)
    (D/'old-reader.txt').write_text(p.stderr);assert p.returncode!=0 and 'unsupported or malformed semantic batch'in p.stderr
check('old-reader-explicit-rejection',old_reader)
mutations={
'bad-version':lambda w:w.update(version='v999'),
'bool-coordinate':lambda w:w['invocation']['range'].__setitem__(0,True),
'bad-nesting':lambda w:w['invocation'].update(range=[0,1]),
'wrong-key':lambda w:w['source'].update(symbol_key='symbol:other'),
'wrong-digest':lambda w:w['source'].update(source_digest='0'*64),
'oversized':lambda w:w['source'].update(coordinate_unit='x'*10000),
'wrong-receiver':lambda w:w['invocation'].update(receiver='other'),
}
for name,change in mutations.items():
    def reject(change=change):
        m=copy.deepcopy(record);change(m['typed_invocation_witness'])
        try:batch(m).validate()
        except (ValueError,TypeError,KeyError):return
        raise AssertionError('accepted malformed witness')
    check(name,reject)
def cap():
    m=SemanticMechanism(**record);payload,_=mechanism_evidence_payload([m]*16);parsed=json.loads(payload)
    assert 0<len(parsed)<16 and len(payload.encode())<=4096
    assert all(x==record for x in parsed)
    huge=copy.deepcopy(record);huge['typed_invocation_witness']['source']['coordinate_unit']='x'*6000
    payload,_=mechanism_evidence_payload([SemanticMechanism(**huge)])
    assert json.loads(payload)==[]
check('atomic-byte-cap-omits-whole-witness',cap)
(D/'model-results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))
