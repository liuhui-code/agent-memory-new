# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Disposable experiment only. Structural decoder is not source authentication."""
import json,re
VERSION='typed-local-invocation/v2'
UNIT='newline-normalized decoded character, half-open'
FIELDS={'version','source','formal','argument_call','callback','invocation'}
def exact(obj,keys):
    if not isinstance(obj,dict) or set(obj)!=set(keys):raise ValueError('unexpected structure')
def identifier(x):
    if not isinstance(x,str) or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',x):raise ValueError('identifier')
def span(x,limit):
    if not isinstance(x,list) or len(x)!=2 or any(type(v)is not int for v in x) or not 0<=x[0]<x[1]<=limit:raise ValueError('span')
def validate(w,entity,digests):
    from .query_typed_contract import _signature
    exact(w,FIELDS)
    if w['version']!=VERSION or len(json.dumps(w).encode())>8192:raise ValueError('version/size')
    s=w['source'];exact(s,['file_path','symbol_key','qualified_name','signature','start_line','end_line','source_digest','coordinate_unit','outer_range','snapshot_length'])
    for k,value in [('file_path',entity.file_path),('symbol_key',entity.key),('qualified_name',entity.qualified_name),('signature',entity.signature),('start_line',entity.start_line),('end_line',entity.end_line)]:
        if s[k]!=value:raise ValueError('identity '+k)
    if any(type(s[k])is not int for k in ['start_line','end_line','snapshot_length']) or not 0<s['snapshot_length']<=32768:raise ValueError('source bounds')
    if s['coordinate_unit']!=UNIT or s['source_digest']!=digests.get(entity.file_path) or not re.fullmatch('[a-f0-9]{64}',s['source_digest']):raise ValueError('snapshot')
    parsed=_signature({'signature':entity.signature,'symbol':entity.name})
    f=w['formal'];exact(f,['index','name','declared_type']);identifier(f['name']);identifier(f['declared_type'])
    if not parsed or type(f['index'])is not int or not 0<=f['index']<len(parsed[0]) or parsed[0][f['index']]!=(f['name'],f['declared_type']):raise ValueError('formal signature')
    if sum(t==f['declared_type']for _,t in parsed[0])!=1:raise ValueError('ambiguous type')
    c=w['argument_call'];exact(c,['receiver','member','range','object_range'])
    cb=w['callback'];exact(cb,['property','range','body_range'])
    inv=w['invocation'];exact(inv,['receiver','member','range'])
    for value in [c['receiver'],c['member'],cb['property'],inv['receiver'],inv['member']]:identifier(value)
    if c['receiver']not in dict(parsed[0]) or inv['receiver']!=f['name']:raise ValueError('receiver declaration')
    previous=None
    for bounds in [s['outer_range'],c['range'],c['object_range'],cb['range'],cb['body_range'],inv['range']]:
        span(bounds,s['snapshot_length'])
        if previous and not previous[0]<=bounds[0]<bounds[1]<=previous[1]:raise ValueError('containment')
        previous=bounds

def extract(text,path,entities,digest):
    from .listener_experiment_prototype import extract as prototype,validate_witness
    facts,_=prototype(text,path);bykey={e.key:e for e in entities};out=[]
    for w in facts:
        e=bykey.get(w['source']['symbol_key'])
        if e is None or w['source']['source_digest']!=digest:continue
        validate_witness(w,{'source':text,'file_path':path,'sha256':digest})
        lines=text.splitlines();norm='\n'.join(lines);s=w['source']
        w['version']=VERSION;s['snapshot_length']=len(norm)
        s['outer_range']=[sum(len(v)+1 for v in lines[:e.start_line-1]),sum(len(v)+1 for v in lines[:e.end_line])-1]
        validate(w,e,{path:digest});out.append(w)
    return out

def pack(legacy,witnesses):
    remaining=4096-len(legacy.encode('utf-8'))
    if remaining<2:return None
    kept=[]
    for w in witnesses:
        candidate=json.dumps([*kept,w],ensure_ascii=False,separators=(',',':'),sort_keys=True)
        if len(candidate.encode('utf-8'))>remaining:break
        kept.append(w)
    return json.dumps(kept,ensure_ascii=False,separators=(',',':'),sort_keys=True)

def legacy_guard(value):
    typed={'typed_invocation_witness','typed_invocation_witnesses','callback_argument_binding'}
    def visit(x):
        if isinstance(x,dict):
            if typed & set(x):raise ValueError('legacy typed contamination')
            for v in x.values():visit(v)
        elif isinstance(x,list):
            for v in x:visit(v)
    visit(value)
