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
results=[]
def check(name,fn):
    try:fn();results.append({'id':name,'pass':True})
    except Exception as ex:results.append({'id':name,'pass':False,'error':repr(ex)})
def roundtrip():
    data=batch([witness]).to_dict();assert SemanticBatch.from_dict(data).to_dict()==data
    (D/'experimental-batch.json').write_text(json.dumps(data,indent=2))
check('v2-roundtrip',roundtrip)
def legacy_data():
    data=batch([]).to_dict();data['schema_version']='semantic-index/v1';data.pop('typed_invocation_witnesses');return data
def clean_legacy():assert SemanticBatch.from_dict(legacy_data()).typed_invocation_witnesses==[]
check('clean-legacy-unknown',clean_legacy)
for location in ['batch','entity','mechanism']:
 for value in [None,[],{}]:
    def reject(location=location,value=value):
        data=legacy_data();target=data if location=='batch' else data['entities'if location=='entity'else'mechanisms'][0]
        target['typed_invocation_witnesses']=value
        try:SemanticBatch.from_dict(data)
        except ValueError:return
        raise AssertionError('legacy pollution accepted')
    check('v1-pollution-'+location+'-'+type(value).__name__,reject)
def old_reader():
    code='import sys,json;sys.path.insert(0,sys.argv[1]);from tools.agent_memory_runtime.semantic_models import SemanticBatch;SemanticBatch.from_dict(json.load(open(sys.argv[2])))'
    p=subprocess.run([sys.executable,'-c',code,str(ROOT),str(D/'experimental-batch.json')],cwd='/tmp',capture_output=True,text=True)
    (D/'old-reader.txt').write_text(p.stderr);assert p.returncode!=0 and 'unsupported or malformed'in p.stderr
check('old-reader-rejects-v2',old_reader)
mutations={
'wrong-index':lambda w:w['formal'].update(index=0),
'wrong-type':lambda w:w['formal'].update(declared_type='OtherSink'),
'wrong-name':lambda w:w['formal'].update(name='other'),
'bool-index':lambda w:w['formal'].update(index=True),
'unit':lambda w:w['source'].update(coordinate_unit='UTF8-byte'),
'bool-coordinate':lambda w:w['invocation']['range'].__setitem__(0,True),
'outside-outer':lambda w:w['source'].update(outer_range=[0,1]),
'outer-line':lambda w:w['source'].update(start_line=1),
'key':lambda w:w['source'].update(symbol_key='wrong'),
'path':lambda w:w['source'].update(file_path='other.ets'),
'signature':lambda w:w['source'].update(signature='other():void'),
'digest':lambda w:w['source'].update(source_digest='0'*64),
'version':lambda w:w.update(version='v99'),
'oversized':lambda w:w['source'].update(coordinate_unit='x'*10000),
'callreceiver':lambda w:w['argument_call'].update(receiver='other'),
'invalid-callmember':lambda w:w['argument_call'].update(member='x.y'),
'unknown-field':lambda w:w['formal'].update(extra=True),
}
for name,change in mutations.items():
    def reject(change=change):
        w=copy.deepcopy(witness);change(w)
        try:batch([w]).validate()
        except (ValueError,TypeError,KeyError):return
        raise AssertionError('invalid accepted')
    check(name,reject)
def source_not_decoder():
    w=copy.deepcopy(witness);w['invocation']['member']='differentMember';batch([w]).validate()
    source=json.loads((ROOT/'docs/eval/native-listener-current-20261114/protocol.json').read_text())['sources'][row['file_path']]
    try:validate_witness(w,{'source':source,'file_path':row['file_path'],'sha256':row['source_digest']})
    except AssertionError:return
    raise AssertionError('source validation missed member mismatch')
check('decoder-structure-not-source-authentication',source_not_decoder)
def caps():
    old,terms=mechanism_evidence_payload(mechanisms)
    for legacy in [old,'["'+'x'*4088+'"]','["'+'x'*4092+'"]']:
        before=legacy;side=pack(legacy,[witness]*16)
        assert legacy==before
        assert len(legacy.encode())+(len(side.encode())if side is not None else 0)<=4096
        kept=json.loads(side)if side else[];assert all(v==witness for v in kept)
        if len(legacy.encode())>4000:assert not kept
    side=pack(old,[witness])
    actual_before=next(r for r in json.loads((D/'before-list.json').read_text())if r['symbol_key']==row['symbol_key'])
    assert actual_before['mechanism_evidence']==row['mechanism_evidence']
    assert mechanism_search_terms(actual_before['mechanism_evidence'])==mechanism_search_terms(row['mechanism_evidence'])
    retained,_=mechanism_evidence_payload(mechanisms);assert retained==old
    (D/'cap-observation.json').write_text(json.dumps({'legacy_bytes':len(old.encode()),'side_bytes':len(side.encode())if side else 0,'terms':terms,'legacy_unchanged':True},indent=2))
check('4096-whole-side-omission-legacy-preserved',caps)
(D/'model-results.json').write_text(json.dumps(results,indent=2));print(json.dumps({'total':len(results),'passed':sum(r['pass']for r in results),'failures':[r for r in results if not r['pass']]}))
