# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""EXPERIMENT ONLY: copied into a disposable runtime by install_overlay.py."""
import json
import re
from dataclasses import replace

def validate(w, entity):
    if not isinstance(w, dict) or set(w) != {'version','source','formal','argument_call','callback','invocation'}:
        raise ValueError('invalid experiment witness structure')
    if w['version'] != 'offline-callback-source/v1' or len(json.dumps(w).encode()) > 8192:
        raise ValueError('unknown version or oversized witness')
    s=w['source']
    for field,value in [('symbol_key',entity.key),('file_path',entity.file_path),('qualified_name',entity.qualified_name),('signature',entity.signature),('start_line',entity.start_line),('end_line',entity.end_line)]:
        if s.get(field)!=value:raise ValueError('source identity mismatch '+field)
    if not re.fullmatch('[0-9a-f]{64}',str(s.get('source_digest',''))):raise ValueError('invalid digest')
    f=w['formal']
    if type(f.get('index')) is not int or not 0<=f['index']<16:raise ValueError('invalid formal index')
    for value in [f.get('name'),f.get('declared_type'),w['invocation'].get('receiver'),w['invocation'].get('member'),w['callback'].get('property')]:
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',value):raise ValueError('invalid identifier')
    if f['name']!=w['invocation']['receiver']:raise ValueError('receiver mismatch')
    prior=None
    for span in [w['argument_call']['range'],w['argument_call']['object_range'],w['callback']['range'],w['callback']['body_range'],w['invocation']['range']]:
        if not isinstance(span,list) or len(span)!=2 or any(type(x)is not int for x in span) or not 0<=span[0]<span[1]<=32768:raise ValueError('invalid coordinates')
        if prior and not prior[0]<=span[0]<span[1]<=prior[1]:raise ValueError('invalid containment')
        prior=span

def attach(text,path,entities,mechanisms):
    from .listener_experiment_prototype import extract,validate_witness
    facts,_=extract(text,path)
    bykey={e.key:e for e in entities}
    eligible={}
    for w in facts:
        entity=bykey.get(w['source']['symbol_key'])
        if entity is None:continue
        validate(w,entity)
        validate_witness(w,{'source':text,'file_path':path,'sha256':w['source']['source_digest']})
        normalized='\n'.join(text.splitlines())
        line=normalized.count('\n',0,w['invocation']['range'][0])+1
        eligible.setdefault((entity.key,line,'call:'+w['invocation']['receiver']+'.'+w['invocation']['member']),[]).append(w)
    out=[]
    for m in mechanisms:
        candidates=eligible.get((m.source_key,m.line,m.detail),[])
        out.append(replace(m,typed_invocation_witness=candidates[0]) if m.kind=='operation' and len(candidates)==1 else m)
    return out
