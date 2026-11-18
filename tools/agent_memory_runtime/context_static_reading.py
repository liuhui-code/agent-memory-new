# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Terminal non-exclusive reading order. Never fed back into retrieval/focus."""
from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import re
import sqlite3
from .cache_scan_reading_source import parse_clock_scan
from .query_output_loop_selection import valid_row
from .query_sql_slot_guard import ordinary_callable
from .storage import connect
from .context_budget import synchronize_estimate
from .performance_scoring import estimate_payload_tokens

TARGET = r'(?:executable eviction scan ownership|(?:the )?timestamp scan and delete implementation|(?:the )?minimum-field scan and key deletion source)'
REQUEST = re.compile(r'(?:(?:A|The) (?P<background>[a-z -]{1,150})\. )?(?:Locate|Find|Return) '+TARGET+r'\.?')
UNSUPPORTED = re.compile(r'\b(?:fifo|literal|text|display|explain|generate|log|logs|diagnos\w*|trace|error|failed|failure|both|only|except|instead|not|never|without|ignore)\b', re.I)


def reading_request(query):
    if type(query) is not str or len(query)>240 or UNSUPPORTED.search(query): return None
    match=REQUEST.fullmatch(query)
    if match is None: return None
    background=match['background'] or ''
    # An optional cache observation is context, never an identifier selector.
    if background and not re.search(r'\bcache\b',background): return None
    return background


def identity(candidate):
    span=candidate.get('source_range') or {}
    return (candidate.get('file_path'),candidate.get('owner_name'),candidate.get('symbol'),span.get('start_line'),span.get('end_line'))


def complete_excerpt(anchors,path,lo,hi,source):
    lines=source.splitlines();seen={}
    for anchor in anchors:
        if anchor.get('file_path')!=path: continue
        for excerpt in anchor.get('source_excerpts') or []:
            start,end=excerpt.get('start_line'),excerpt.get('end_line')
            content=excerpt.get('content')
            if type(start)is not int or type(end)is not int or type(content)is not str: return False
            text=content.splitlines()
            if start<1 or end<start or len(text)!=end-start+1 or end>len(lines): return False
            if text!=lines[start-1:end]: return False
            for n,line in enumerate(text,start):
                if n in seen and seen[n]!=line:return False
                seen[n]=line
    return all(seen.get(n)==lines[n-1]for n in range(lo,hi+1))


def qualify(project,candidate,payload):
    path,owner,name,lo,hi=identity(candidate)
    if not all(type(x)is str and x for x in (path,owner,name)): return False
    p=PurePosixPath(path);root=Path(project.root).resolve();file=(root/path).resolve()
    if p.is_absolute() or '..'in p.parts or str(p)!=path or p.suffix not in {'.ts','.ets'} or not file.is_relative_to(root):return False
    try:
        with file.open('rb')as stream:raw=stream.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:return False
        source=raw.decode('utf-8');proof=parse_clock_scan(source)
    except(OSError,UnicodeError):return False
    if proof is None or (owner,name)!=(proof['owner'],proof['method']):return False
    if type(lo)is not int or type(hi)is not int or not proof['start_line']<=lo<=hi<=proof['end_line']:return False
    if (lo,hi)!=(proof['start_line'],proof['end_line']) and candidate['source_range'].get('selection_reason')!='semantic_mechanism_window':return False
    lo,hi=proof['start_line'],proof['end_line']
    digest=hashlib.sha256(raw).hexdigest();generation=payload['source_freshness'].get('generation')
    with connect(project)as conn:
        rows=[dict(r)for r in conn.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path=?',(project.project_id,path))]
        files=[dict(r)for r in conn.execute('SELECT * FROM code_files WHERE project_id=? AND file_path=?',(project.project_id,path))]
    if len(files)!=1 or files[0].get('source_digest')!=digest or files[0].get('index_generation')!=generation:return False
    methods=[r for r in rows if r.get('qualified_name')==owner+'.'+name or (r.get('symbol')==name and r.get('start_line')==lo)]
    owners=[r for r in rows if r.get('qualified_name')==owner and r.get('symbol')==owner]
    if len(methods)!=1 or len(owners)!=1:return False
    method,container=methods[0],owners[0]
    with connect(project)as conn:
        if any(conn.execute('SELECT COUNT(*) FROM code_symbols WHERE project_id=? AND symbol_key=?',(project.project_id,r.get('symbol_key'))).fetchone()[0]!=1 for r in (method,container)):return False
    if any(not valid_row(r,project)or r['source_digest']!=digest or r['index_generation']!=generation for r in (method,container)):return False
    if (method['qualified_name']!=owner+'.'+name or method['symbol']!=name or candidate.get('owner_kind')!=method['owner_kind'] or container.get('owner_name')not in ('',None) or method['symbol_type']not in {'method','function'}or method['owner_name']!=owner or method['owner_kind']!=container['owner_kind']or container['symbol_type']!='class'
        or (method['start_line'],method['end_line'])!=(lo,hi)or(container['start_line'],container['end_line'])!=(proof['class_start'],proof['class_end'])):return False
    return {'display_complete':complete_excerpt(payload['query_handoff']['code_anchors'],path,lo,hi,source)}


def static_reading_order(project,payload):
    """All-or-nothing permutation; unknown, stale, ambiguous, over-budget=no-op."""
    query=payload.get('query');background=reading_request(query)
    if background is None or payload.get('source_freshness',{}).get('status')!='current':return payload
    h=payload.get('query_handoff',{});e=h.get('callable_evidence');path=h.get('path_context')or{}
    if not ordinary_callable(e)or not e.get('primary')or path.get('activated')or path.get('wrapped_log_evidence'):return payload
    candidates=[e['primary'],*e['alternatives']]
    if len({identity(c)for c in candidates})!=len(candidates):return payload
    if any(a.get(k)for a in h.get('code_anchors',[])for k in ('identity_match','log_identity_match')):return payload
    if any(re.search(r'\b'+re.escape(str(c.get(k)or''))+r'\b',background,re.I)for c in candidates for k in ('symbol','owner_name')if c.get(k)):return payload
    try:matches=[(i,proof)for i,c in enumerate(candidates)if (proof:=qualify(project,c,payload))]
    except(KeyError,TypeError,ValueError,OverflowError,OSError,sqlite3.Error):return payload
    if len(matches)!=1 or matches[0][0]==0 or not matches[0][1]['display_complete']:return payload
    selected=matches[0][0];order=[selected,*[i for i in range(len(candidates))if i!=selected]]
    result=deepcopy(payload);e2=result['query_handoff']['callable_evidence']
    e2['primary']=deepcopy(candidates[selected]);e2['alternatives']=[deepcopy(candidates[i])for i in order[1:]]
    e2['certainty']='uncertain';e2['boundary']='nonexclusive_static_clock_scan_reading'
    e2['reading_basis']={'prior':[order.index(i)for i in range(len(candidates))]}
    synchronize_estimate(result)
    if estimate_payload_tokens(result)>result.get('output_budget',{}).get('target_tokens',0):return payload
    return result
