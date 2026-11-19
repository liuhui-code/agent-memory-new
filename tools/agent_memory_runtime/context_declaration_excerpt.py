"""Append a requested, already-selected declaration; never choose a new target."""
from copy import deepcopy
from pathlib import Path, PurePosixPath
import hashlib
import re
import sqlite3
from .context_callable_focus import DECLARATION_REQUEST_RE
from .query_output_loop_selection import valid_row
from .storage import connect
from .performance_scoring import estimate_payload_tokens
from .context_budget import synchronize_estimate
from .context_source_excerpt import (MAX_EXCERPT_ANCHORS, MAX_EXCERPTS_PER_ANCHOR,
    MAX_EXCERPT_LINES, MAX_EXCERPT_CHARS, MAX_TOTAL_EXCERPT_CHARS)


def append_requested_declaration(project,payload):
    try:return _append(project,payload)
    except(OSError,UnicodeError,sqlite3.Error,KeyError,TypeError,ValueError,AttributeError):return payload


def _append(project,payload):
    query=payload.get('query')
    # Unlike the selection-preservation guard, no clause stripping grants reading.
    if not isinstance(query,str) or len(query)>400:return payload
    request=DECLARATION_REQUEST_RE.fullmatch(query.strip())
    if request is None or payload.get('source_freshness',{}).get('status')!='current':return payload
    name=request['name'];h=payload.get('query_handoff',{});anchors=h.get('code_anchors',[])
    matching=[a for a in anchors if a.get('symbol')==name and a.get('symbol_type')in {'class','struct','interface'}]
    if len(matching)!=1:return payload
    anchor=matching[0];path=anchor.get('file_path');ids=anchor.get('record_ids');spans=anchor.get('source_ranges')
    if (anchor.get('record_type')!='code_symbol' or not isinstance(path,str)
        or not isinstance(ids,list) or not ids or any(type(i)is not int or i<1 for i in ids)
        or len(set(ids))!=len(ids) or not isinstance(spans,list)):return payload
    excerpts=anchor.get('source_excerpts',[])
    if not isinstance(excerpts,list) or not excerpts or len(excerpts)>=MAX_EXCERPTS_PER_ANCHOR:return payload
    root=Path(project.root).resolve();pp=PurePosixPath(path);file=(root/path).resolve()
    if pp.is_absolute()or '..'in pp.parts or str(pp)!=path or pp.suffix not in {'.ts','.ets'}or not file.is_relative_to(root):return payload
    generation=payload['source_freshness']['generation']
    with connect(project)as conn:
        conn.execute('BEGIN')
        state=conn.execute('SELECT * FROM code_index_state WHERE project_id=?',(project.project_id,)).fetchone()
        if state is None or state['status']!='active' or state['generation']!=generation:return payload
        rows=[dict(r)for r in conn.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path=? AND symbol=?',(project.project_id,path,name))]
        files=[dict(r)for r in conn.execute('SELECT * FROM code_files WHERE project_id=? AND file_path=?',(project.project_id,path))]
        if len(rows)!=1 or len(files)!=1:return payload
        row=rows[0];f=files[0]
        if conn.execute('SELECT COUNT(*) FROM code_symbols WHERE project_id=? AND symbol_key=?',(project.project_id,row.get('symbol_key'))).fetchone()[0]!=1:return payload
    if (not valid_row(row,project)or row.get('symbol_type')!=anchor['symbol_type']
        or row.get('qualified_name')!=name or row.get('owner_name')not in ('',None)
        or row['id']not in ids or row['index_generation']!=generation or f.get('index_generation')!=generation):return payload
    lo,hi=row['start_line'],row['end_line']
    if hi-lo+1>MAX_EXCERPT_LINES or spans.count(dict(symbol=name,start_line=lo,end_line=hi))!=1:return payload
    with file.open('rb')as stream:raw=stream.read(2*1024*1024+1)
    if len(raw)>2*1024*1024 or b'\0'in raw:return payload
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=row['source_digest']or digest!=f.get('source_digest'):return payload
    source=raw.decode('utf-8')
    if any(c in source for c in '\v\f\x1c\x1d\x1e\x85\u2028\u2029'):return payload
    lines=source.splitlines()
    if hi>len(lines):return payload
    header=r'\s*(?:export\s+)?(?:declare\s+)?'+re.escape(row['symbol_type'])+r'\s+'+re.escape(name)+r'\b'
    if re.match(header,lines[lo-1])is None:return payload
    # Preserve every old excerpt exactly, including overlapping non-target source.
    for e in excerpts:
        a,b=e.get('start_line'),e.get('end_line')
        if (type(a)is not int or type(b)is not int or not 0<a<=b<=len(lines)
            or e.get('source')!='current_worktree' or e.get('content')!='\n'.join(lines[a-1:b])):return payload
    if any(e['start_line']<=lo<=hi<=e['end_line']for e in excerpts):return payload
    text='\n'.join(lines[lo-1:hi])
    if len(text)>MAX_EXCERPT_CHARS:return payload
    trial=deepcopy(payload);target=trial['query_handoff']['code_anchors'][anchors.index(anchor)]
    target['source_excerpts'].append(dict(symbol=name,start_line=lo,end_line=hi,content=text,
        source='current_worktree',selection_reason='authenticated_requested_declaration',truncated=False,
        source_snapshot=dict(source_digest=digest,index_generation=generation),record_id=row['id']))
    all_excerpts=[e for a in trial['query_handoff']['code_anchors']for e in a.get('source_excerpts',[])]
    chars=sum(len(e['content'])for e in all_excerpts)
    if (chars>MAX_TOTAL_EXCERPT_CHARS or sum(bool(a.get('source_excerpts'))for a in anchors)>MAX_EXCERPT_ANCHORS
        or any(len(a.get('source_excerpts',[]))>MAX_EXCERPTS_PER_ANCHOR for a in trial['query_handoff']['code_anchors'])):return payload
    policy=trial['query_handoff'].get('source_excerpt_policy');budget=trial.get('output_budget')
    if not isinstance(policy,dict)or not isinstance(budget,dict)or budget.get('target_tokens')not in (1500,2000):return payload
    policy.update(excerpt_chars=chars,excerpt_count=len(all_excerpts));synchronize_estimate(trial)
    if estimate_payload_tokens(trial)>budget['target_tokens']:return payload
    return trial
