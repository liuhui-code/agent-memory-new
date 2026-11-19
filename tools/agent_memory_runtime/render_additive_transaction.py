"""Add source-proved cleanup expression passages; never replace a selected owner."""
from copy import deepcopy
from pathlib import Path
import hashlib
import sqlite3
import time
from .query_render_recall import parse_render_request
from .query_render_source import parse_render_source, lex
from .query_language import excluded_code_candidate
from .query_ui_pair import valid_row
from .storage import connect
from .context_budget import synchronize_estimate
from .performance_scoring import estimate_payload_tokens
from .context_source_excerpt import (MAX_EXCERPT_ANCHORS, MAX_EXCERPTS_PER_ANCHOR,
    MAX_EXCERPT_LINES, MAX_EXCERPT_CHARS, MAX_TOTAL_EXCERPT_CHARS)


def eligible(data):
    request = parse_render_request(data.get('query'))
    return bool(type(data) is dict and request and request.capability == 'cleanup'
                and data.get('source_freshness', {}).get('status') == 'current'
                and bool(data.get('query_handoff', {}).get('code_anchors')))


def qualify(project, baseline, deadline):
    """Positive proof in the existing bounded recall pool, not whole-repo absence."""
    if not eligible(baseline): return None
    paths = sorted({r['file_path'] for r in baseline.get('wiki_matches', [])
                    if isinstance(r, dict) and isinstance(r.get('file_path'), str)})
    if not 0 < len(paths) <= 12: return None
    generation = baseline['source_freshness'].get('generation')
    try:
        with connect(project) as conn:
            conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            conn.execute('BEGIN')
            state = conn.execute('SELECT * FROM code_index_state WHERE project_id=?', (project.project_id,)).fetchone()
            if state is None or state['status'] != 'active' or state['generation'] != generation: return None
            marks = ','.join('?' for _ in paths)
            files = [dict(r) for r in conn.execute('SELECT * FROM code_files WHERE project_id=? AND file_path IN ('+marks+')', [project.project_id,*paths])]
            symbols = [dict(r) for r in conn.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ('+marks+') LIMIT 257', [project.project_id,*paths])]
    except sqlite3.Error: return None
    if len(files) != len(paths) or len(symbols) > 256: return None
    if len({r.get('symbol_key') for r in symbols}) != len(symbols): return None
    root = Path(project.root).resolve(); receipts = []; total = 0
    for f in files:
        if time.monotonic() > deadline: return None
        path = (root/f['file_path']).resolve()
        if not path.is_relative_to(root) or f.get('index_generation') != generation: return None
        try:
            with path.open('rb') as stream: raw = stream.read(256*1024+1)
            total += len(raw)
            if len(raw)>256*1024 or total>1024*1024 or hashlib.sha256(raw).hexdigest()!=f.get('source_digest'): return None
            source = raw.decode('utf-8')
        except (OSError, UnicodeError): return None
        if path.suffix != '.ets': continue
        parsed = parse_render_source(source)
        if parsed is None: continue
        local = [r for r in symbols if r['file_path'] == f['file_path']]
        owners = [r for r in local if r['symbol']==parsed['owner'] and r['symbol_type'] in {'struct','component'}]
        if len(owners)!=1: return None
        owner = owners[0]
        tokens=lex(source)
        declarations=[t.line for i,t in enumerate(tokens[:-1]) if t.value=='struct' and tokens[i+1].value==parsed['owner']]
        closes=[t.line for t in tokens if t.kind=='punct' and t.value=='}']
        if (len(declarations)!=1 or not closes or owner.get('owner_kind')!='component'
                or owner.get('owner_name') not in ('',None)
                or owner.get('start_line')!=declarations[0] or owner.get('end_line')!=closes[-1]): return None
        if excluded_code_candidate(baseline['query'], owner): continue
        if (not valid_row(owner, project) or owner['source_digest']!=f['source_digest']
                or owner['index_generation']!=generation or owner.get('qualified_name')!=owner['symbol']): return None
        members=[]
        for name,lo,hi in [('build',parsed['build_start'],parsed['build_end']),
                           (parsed['helper'],parsed['helper_start'],parsed['helper_end'])]:
            matches=[r for r in local if r['symbol']==name and r.get('qualified_name')==owner['symbol']+'.'+name
                     and r.get('owner_name')==owner['symbol'] and r.get('owner_kind')=='component'
                     and r.get('symbol_type') in {'method','function'} and r.get('start_line')==lo and r.get('end_line')==hi]
            if len(matches)!=1: return None
            row=matches[0]
            if (not valid_row(row,project) or row['source_digest']!=f['source_digest']
                    or row['index_generation']!=generation or not owner['start_line']<=lo<=hi<=owner['end_line']): return None
            members.append(row)
        receipts.append(dict(file=f,lines=source.split('\n'),members=members))
    return receipts if 0<len(receipts)<=3 and time.monotonic()<=deadline else None


def append_passages(output, receipts, *, selection_reason='static_render_expression',anchor_role=None):
    if type(output) is not dict or not isinstance(output.get('output_budget'),dict): return output, []
    if output['output_budget'].get('target_tokens') not in (1500,2000): return output, []
    candidate=deepcopy(output);h=candidate.get('query_handoff',{});anchors=h.get('code_anchors')
    if type(anchors) is not list or not anchors: return output, []
    added=[];count=chars=0
    for receipt in receipts:
        f,lines=receipt['file'],receipt['lines'];same=[a for a in anchors if a.get('file_path')==f['file_path']]
        # Existing visible source must still match this certified snapshot.
        for a in same:
            for e in a.get('source_excerpts',[]):
                lo,hi=e.get('start_line'),e.get('end_line')
                if (type(lo) is not int or type(hi) is not int or not 0<lo<=hi<=len(lines)
                        or e.get('content')!='\n'.join(lines[lo-1:hi])): return output, []
        missing=[]
        for row in receipt['members']:
            lo,hi=row['start_line'],row['end_line'];text='\n'.join(lines[lo-1:hi])
            covered=any(e['start_line']<=lo<=hi<=e['end_line'] for a in same for e in a.get('source_excerpts',[]))
            if covered: continue
            if hi-lo+1>MAX_EXCERPT_LINES or len(text)>MAX_EXCERPT_CHARS: return output, []
            missing.append((row,dict(symbol=row['symbol'],start_line=lo,end_line=hi,content=text,
                source='validated_request_snapshot',selection_reason=selection_reason,truncated=False)))
        if not missing: continue
        # Never grow an existing anchor's identity or read window. A new source
        # passage is a separate supporting object even when its path is shared.
        anchor=dict(file_path=f['file_path'],record_ids=[],record_type='code_symbol',source_ranges=[],
                    read_window=dict(start_line=min(r['start_line']for r,e in missing),end_line=max(r['end_line']for r,e in missing)),source_excerpts=[])
        if anchor_role is not None:anchor['role']=anchor_role
        anchors.append(anchor)
        snapshot=dict(index_generation=f['index_generation'],source_digest=f['source_digest'])
        if 'source_snapshot' in anchor and anchor['source_snapshot']!=snapshot: return output, []
        anchor['source_snapshot']=snapshot
        for row,excerpt in missing:
            if row['id'] not in anchor['record_ids']: anchor['record_ids'].append(row['id'])
            span=dict(symbol=row['symbol'],start_line=row['start_line'],end_line=row['end_line'])
            if span not in anchor['source_ranges']: anchor['source_ranges'].append(span)
            anchor.setdefault('source_excerpts',[]).append(excerpt)
            added.append(dict(row,kind='symbol'));count+=1;chars+=len(excerpt['content'])
    if not added: return output, []
    displayed=[a for a in anchors if a.get('source_excerpts')]
    if len(displayed)>MAX_EXCERPT_ANCHORS or any(len(a['source_excerpts'])>MAX_EXCERPTS_PER_ANCHOR for a in displayed): return output, []
    if sum(len(e['content'])for a in displayed for e in a['source_excerpts'])>MAX_TOTAL_EXCERPT_CHARS: return output, []
    policy=h.get('source_excerpt_policy')
    if type(policy) is not dict or type(policy.get('excerpt_count')) is not int or type(policy.get('excerpt_chars')) is not int: return output, []
    policy['excerpt_count']+=count;policy['excerpt_chars']+=chars
    synchronize_estimate(candidate)
    if estimate_payload_tokens(candidate)>output['output_budget']['target_tokens']: return output, []
    return candidate, added


def finalize(project, baseline, output):
    deadline=time.monotonic()+.5
    receipts=qualify(project,baseline,deadline)
    if receipts is None: return output, []
    candidate,members=append_passages(output,receipts)
    if candidate is output: return output, []
    if qualify(project,baseline,deadline)!=receipts or time.monotonic()>deadline: return output, []
    return candidate,members
