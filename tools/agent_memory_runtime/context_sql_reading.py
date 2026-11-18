"""Add complete literal-SQL argument source for bounded existing candidates.

This is not a database-execution, business-owner or SQL/UI pairing certificate.
"""
from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import re
import sqlite3
from time import monotonic
from .context_budget import synchronize_estimate
from .context_field_alternative import covered
from .performance_scoring import estimate_payload_tokens
from .query_output_loop_selection import valid_row
from .query_sql_reading_request import sql_reading_request
from .source_exploration import exploration_contract
from .sql_slot_source_inventory import inventory_source
from .sql_slot_source import classify_sql_owner
from .storage import connect

MAX_CANDIDATES = 8
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_ROWS = 128
MAX_SECONDS = 2.0
HELPER_PARAMETERS = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*:string,[A-Za-z_$][A-Za-z0-9_$]*:string\[\]')


def append_sql_reading(project, original, payload):
    try:
        return _append(project, original, payload)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError, sqlite3.Error, RecursionError):
        return payload


def _candidates(handoff):
    evidence = handoff.get('callable_evidence') or {}
    primary = evidence.get('primary'); alternatives = evidence.get('alternatives')
    if type(alternatives) is not list:
        raise ValueError('candidate shape')
    items = ([primary] if primary is not None else []) + alternatives
    if not 0 < len(items) <= MAX_CANDIDATES or any(type(c) is not dict for c in items):
        raise ValueError('candidate bound')
    return items


def _identity(c):
    bounds = c.get('source_range') or {}
    if bounds.get('selection_reason') != 'callable_symbol_range':
        return None
    path, name, owner = c.get('file_path'), c.get('symbol'), c.get('owner_name')
    lo, hi = bounds.get('start_line'), bounds.get('end_line')
    if not all(type(x) is str and x for x in (path, name, owner)):
        return None
    if type(lo) is not int or type(hi) is not int or not 0 < lo <= hi or hi-lo+1 > 40:
        return None
    return path, name, owner, lo, hi


def _append(project, original, payload):
    if not sql_reading_request(payload.get('query')) or original.get('query') != payload['query']:
        return payload
    root = Path(project.root).resolve(); pid = project.project_id
    if (original.get('project_id') != pid or payload.get('project_id') != pid
            or Path(original.get('project_path', '')).resolve() != root):
        return payload
    fresh = payload.get('source_freshness') or {}; raw_fresh = original.get('source_freshness') or {}
    generation = fresh.get('generation'); budget = payload.get('output_budget') or {}
    if (fresh.get('status') != 'current' or raw_fresh.get('status') != 'current'
            or type(generation) is not int or generation <= 0 or raw_fresh.get('generation') != generation
            or type(budget.get('target_tokens')) is not int or budget['target_tokens'] not in (1500,2000)):
        return payload
    h = payload['query_handoff']; raw = original['query_handoff']; anchors = h.get('code_anchors')
    if (type(anchors) is not list or h.get('source_exploration') != exploration_contract()
            or any(type(a) is not dict or a.get('role') not in {'primary','expansion'} for a in anchors)):
        return payload
    expansions = sum(a['role'] == 'expansion' for a in anchors)
    if len(anchors)-expansions > 3 or expansions >= 2 or len(anchors) >= 5:
        return payload
    candidates = _candidates(h); originals = _candidates(raw)
    raw_anchors = raw.get('code_anchors')
    if type(raw_anchors) is not list:
        return payload
    started = monotonic(); captured = {}; seen = set(); additions = []
    def expired(): return monotonic()-started > MAX_SECONDS
    with connect(project) as db:
        db.execute('BEGIN'); db.set_progress_handler(lambda:int(expired()),1000)
        states = [dict(r) for r in db.execute('SELECT * FROM code_index_state WHERE project_id=?',(pid,))]
        if len(states)!=1 or states[0].get('status')!='active' or states[0].get('generation')!=generation:
            return payload
        for candidate in candidates:
            identity = _identity(candidate)
            if identity is None:
                continue  # unsupported candidate remains intact; not evidence of irrelevance
            if identity in seen:
                return payload
            seen.add(identity); path,name,owner_name,lo,hi = identity
            if len([c for c in originals if _identity(c)==identity])!=1:
                return payload
            matches = [a for a in raw_anchors if a.get('file_path')==path and a.get('symbol')==name
                       and a.get('record_type')=='code_symbol' and a.get('start_line')==lo and a.get('end_line')==hi]
            if len(matches)>1:
                return payload
            anchor = matches[0] if matches else None
            rid = anchor.get('record_id') if anchor is not None else None
            if anchor is not None and (type(rid) is not int or anchor.get('source')!='wiki'
                    or anchor.get('symbol_type') not in {'method','function'}
                    or anchor.get('graph_neighbor') is not False or anchor.get('graph_relation') is not None):
                return payload
            p=PurePosixPath(path); file=(root/path).resolve()
            if p.is_absolute() or '..' in p.parts or str(p)!=path or not file.is_relative_to(root) or p.suffix not in {'.ts','.ets'}:
                return payload
            if path not in captured:
                with file.open('rb') as stream: data=stream.read(MAX_FILE_BYTES+1)
                if (len(data)>MAX_FILE_BYTES or b'\0' in data or expired()
                        or sum(len(v[1])for v in captured.values())+len(data)>MAX_TOTAL_BYTES):
                    return payload
                captured[path]=(file,data,hashlib.sha256(data).hexdigest())
            file,data,digest=captured[path]
            files=[dict(r)for r in db.execute('SELECT * FROM code_files WHERE project_id=? AND file_path=?',(pid,path))]
            rows=[dict(r)for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path=? LIMIT ?',(pid,path,MAX_ROWS+1))]
            if len(files)!=1 or len(rows)>MAX_ROWS or files[0].get('source_digest')!=digest or files[0].get('index_generation')!=generation:
                return payload
            method=_unique(rows,owner_name+'.'+name); container=_unique(rows,owner_name)
            if ((anchor is not None and (method['id']!=rid or method['symbol_type']!=anchor['symbol_type']))
                    or method['symbol_type'] not in {'method','function'}
                    or method['symbol']!=name or method['owner_name']!=owner_name
                    or (method['start_line'],method['end_line'])!=(lo,hi)
                    or container['symbol']!=owner_name or container.get('owner_name')
                    or candidate.get('owner_kind')!=container['owner_kind'] or method['owner_kind']!=container['owner_kind']):
                return payload
            rid = method['id']
            for row in (method,container):
                if not _valid_row(db,project,row,digest,generation):return payload
            source=data.decode('utf-8'); inventory=inventory_source(source)
            if inventory.get('status')!='known':continue
            owners=[o for o in inventory['declarations'] if o['name']==owner_name]
            if len(owners)!=1:return payload
            owner=owners[0]
            expected_type='component' if owner['kind']=='struct' else 'class'
            if (container['symbol_type']!=expected_type or (container['start_line'],container['end_line'])!=
                    (owner['span']['start_line'],owner['span']['end_line'])):return payload
            result=classify_sql_owner(source,owner,name)
            if expired():return payload
            if result.get('status')!='known' or not result.get('matches'):continue
            if len(result['matches'])!=1:return payload
            fact=result['matches'][0]
            if (fact['method_span']['start_line'],fact['method_span']['end_line'])!=(lo,hi):return payload
            helpers=[m for m in owner['methods'] if m['name']==fact['callee']]
            if len(helpers)!=1 or HELPER_PARAMETERS.fullmatch(helpers[0]['parameters']) is None:
                continue
            helper=helpers[0]; helper_row=_unique(rows,owner_name+'.'+helper['name'])
            if (not _valid_row(db,project,helper_row,digest,generation) or helper_row['symbol_type'] not in {'method','function'}
                    or helper_row['symbol']!=helper['name'] or helper_row['owner_name']!=owner_name or helper_row['owner_kind']!=container['owner_kind']
                    or (helper_row['start_line'],helper_row['end_line'])!=(helper['span']['start_line'],helper['span']['end_line'])):
                return payload
            lines=source.splitlines(); content='\n'.join(lines[lo-1:hi])
            if hi>len(lines) or len(content)>1500:return payload
            if any(covered(e,lines,lo,hi)for a in anchors if a.get('file_path')==path for e in a.get('source_excerpts',[])):
                continue
            additions.append(dict(file_path=path,symbol=name,record_type='code_symbol',record_ids=[rid],role='expansion',
                source_ranges=[dict(symbol=name,start_line=lo,end_line=hi)],read_window=dict(start_line=lo,end_line=hi),
                display_basis=dict(kind='literal_sql_argument_source',execution_unverified=True,pair_unverified=True,behavior_unverified=True,domain_unverified=True),
                source_excerpts=[dict(symbol=name,start_line=lo,end_line=hi,content=content,source='current_worktree',
                    selection_reason='existing_sql_candidate_body',focus_line=None,truncated=False)]))
        for file,data,digest in captured.values():
            with file.open('rb')as stream:current=stream.read(MAX_FILE_BYTES+1)
            if hashlib.sha256(current).hexdigest()!=digest or expired():return payload
    if not additions or len(additions)+expansions>2 or len(additions)+len(anchors)>5:return payload
    trial=deepcopy(payload);trial['query_handoff']['code_anchors'].extend(additions)
    excerpts=[e for a in trial['query_handoff']['code_anchors']for e in a.get('source_excerpts',[])]
    chars=sum(len(e['content'])for e in excerpts)
    if chars>2600:return payload
    policy=trial['query_handoff'].setdefault('source_excerpt_policy',dict(source='current_worktree',body_persisted=False))
    policy.update(excerpt_chars=chars,excerpt_count=len(excerpts));synchronize_estimate(trial)
    return trial if estimate_payload_tokens(trial)<=budget['target_tokens'] else payload


def _unique(rows,name):
    found=[r for r in rows if r.get('qualified_name')==name]
    if len(found)!=1:raise ValueError('ambiguous typed identity')
    return found[0]


def _valid_row(db,project,row,digest,generation):
    return (valid_row(row,project) and row['source_digest']==digest and row['index_generation']==generation
            and db.execute('SELECT COUNT(*) FROM code_symbols WHERE project_id=? AND symbol_key=?',
                           (project.project_id,row['symbol_key'])).fetchone()[0]==1)
