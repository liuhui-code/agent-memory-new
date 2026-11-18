# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Opt-in, additive full-method display; never selection or diagnosis authority."""
from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import sqlite3
from .storage import connect
from .query_output_loop_selection import valid_row
from .context_budget import synchronize_estimate
from .performance_scoring import estimate_payload_tokens

FIELDS=frozenset(('symbol','start_line','end_line','content','source','selection_reason','focus_line','truncated'))


def qualified_source(project,payload,anchor,candidate):
    path=candidate.get('file_path');owner=candidate.get('owner_name');name=candidate.get('symbol');bounds=candidate.get('source_range')or{}
    lo,hi=bounds.get('start_line'),bounds.get('end_line')
    if (not all(type(v)is str and v for v in (path,owner,name)) or type(lo)is not int or type(hi)is not int
        or not 0<lo<=hi or hi-lo+1>40 or bounds.get('selection_reason')!='callable_symbol_range'):return None
    p=PurePosixPath(path);root=Path(project.root).resolve();file=(root/path).resolve()
    if p.is_absolute()or '..'in p.parts or str(p)!=path or p.suffix not in {'.ts','.ets'}or not file.is_relative_to(root):return None
    with file.open('rb')as stream:raw=stream.read(2*1024*1024+1)
    if len(raw)>2*1024*1024 or b'\0'in raw:return None
    lines=raw.decode('utf-8').splitlines();digest=hashlib.sha256(raw).hexdigest();generation=payload['source_freshness']['generation']
    if hi>len(lines):return None
    with connect(project)as conn:
        files=[dict(r)for r in conn.execute('SELECT * FROM code_files WHERE project_id=? AND file_path=?',(project.project_id,path))]
        rows=[dict(r)for r in conn.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path=?',(project.project_id,path))]
        methods=[r for r in rows if r.get('qualified_name')==owner+'.'+name]
        owners=[r for r in rows if r.get('qualified_name')==owner and r.get('symbol')==owner]
        if len(files)!=1 or len(methods)!=1 or len(owners)!=1:return None
        method,container=methods[0],owners[0]
        if any(conn.execute('SELECT COUNT(*) FROM code_symbols WHERE project_id=? AND symbol_key=?',(project.project_id,r.get('symbol_key'))).fetchone()[0]!=1 for r in (method,container)):return None
    if any(not valid_row(r,project)or r['source_digest']!=digest or r['index_generation']!=generation for r in (method,container)):return None
    if files[0].get('source_digest')!=digest or files[0].get('index_generation')!=generation:return None
    if (method['symbol']!=name or method['owner_name']!=owner or method['owner_kind']!=candidate.get('owner_kind')
        or method['symbol_type']not in {'method','function'}or(method['start_line'],method['end_line'])!=(lo,hi)
        or container['symbol_type']not in {'class','struct','component'}or container['owner_kind']!=method['owner_kind']
        or container.get('owner_name')not in ('',None)or not container['start_line']<=lo<=hi<=container['end_line']):return None
    if anchor.get('record_type')=='code_file':
        if anchor.get('record_ids')!=[files[0]['id']]or anchor.get('symbol')!=owner:return None
    elif anchor.get('record_type')=='code_symbol':
        if anchor.get('record_ids')!=[method['id']]or anchor.get('symbol')!=name:return None
    else:return None
    return lines


def expand_callable_envelopes(project,payload,*,enabled=False):
    """Keep every old excerpt byte/metadata recoverable; unknown shapes are no-op."""
    try:return _expand(project,payload,enabled=enabled)
    except(KeyError,TypeError,ValueError,AttributeError,OverflowError):return payload


def _expand(project,payload,*,enabled=False):
    if not enabled or payload.get('source_freshness',{}).get('status')!='current':return payload
    h=payload.get('query_handoff',{});ev=h.get('callable_evidence')or{}
    candidates=[c for c in [ev.get('primary'),*ev.get('alternatives',[])]if isinstance(c,dict)]
    result=payload
    for ai,anchor in enumerate(h.get('code_anchors',[])):
        excerpts=anchor.get('source_excerpts',[])
        if len(excerpts)!=1:continue
        old=excerpts[0]
        if (not isinstance(old,dict)or set(old)!=FIELDS or old['source']!='current_worktree'
            or old['selection_reason']!='callable_mechanism_window'or type(old['content'])is not str
            or type(old['start_line'])is not int or type(old['end_line'])is not int
            or not 0<old['start_line']<=old['end_line']):continue
        matches=[]
        for c in candidates:
            b=c.get('source_range')or{};lo,hi=b.get('start_line'),b.get('end_line')
            if (c.get('file_path')==anchor.get('file_path')and type(lo)is int and type(hi)is int
                and lo<=old['start_line']<=old['end_line']<=hi and (lo,hi)!=(old['start_line'],old['end_line'])):matches.append(c)
        if len(matches)!=1:continue
        c=matches[0];lo,hi=c['source_range']['start_line'],c['source_range']['end_line']
        try:lines=qualified_source(project,payload,anchor,c)
        except(OSError,UnicodeError,KeyError,TypeError,ValueError,sqlite3.Error):continue
        if lines is None or old['content']!='\n'.join(lines[old['start_line']-1:old['end_line']]):continue
        content='\n'.join(lines[lo-1:hi])
        if len(content)>1500:continue
        trial=deepcopy(result);target=trial['query_handoff']['code_anchors'][ai]['source_excerpts'][0]
        target.update(symbol=c['symbol'],start_line=lo,end_line=hi,content=content,truncated=False,
                      selection_reason='existing_callable_envelope',expanded_from={k:v for k,v in old.items()if k!='content'})
        all_excerpts=[e for a in trial['query_handoff']['code_anchors']for e in a.get('source_excerpts',[])]
        chars=sum(len(e['content'])for e in all_excerpts)
        if chars>2600:continue
        policy=trial['query_handoff'].get('source_excerpt_policy');budget=trial.get('output_budget')
        if not isinstance(policy,dict)or not isinstance(budget,dict):continue
        policy.update(excerpt_chars=chars,excerpt_count=len(all_excerpts));synchronize_estimate(trial)
        if estimate_payload_tokens(trial)<=budget.get('target_tokens',0):result=trial
    return result
