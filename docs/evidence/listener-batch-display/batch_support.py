# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json

def normalize(values):
    # Count/type rejection happens before serialization or element iteration.
    if type(values)is not list or len(values)>64:raise ValueError('optional count/type')
    if len(json.dumps(values,ensure_ascii=False).encode())>65536:raise ValueError('optional bytes')
    seen={};out=[]
    for w in values:
        try:key=(w['source']['symbol_key'],w['source']['source_digest'],tuple(w['invocation']['range']))
        except (KeyError,TypeError):raise ValueError('optional identity')
        canonical=json.dumps(w,sort_keys=True,ensure_ascii=False,separators=(',',':'))
        if key in seen:
            if seen[key]!=canonical:raise ValueError('conflicting optional identity')
            continue
        seen[key]=canonical;out.append(w)
    return out

def optional_batch(values,entities,digests):
    from .listener_experiment_support import validate
    try:
        out=normalize(values)
        for w in out:
            e=entities.get(w['source']['symbol_key'])
            if e is None or e.kind not in {'method','function'}:raise ValueError('noncallable')
            validate(w,e,digests)
        return out
    except (ValueError,TypeError,KeyError):return []
