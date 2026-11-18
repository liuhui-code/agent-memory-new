"""Terminal same-response Web reading permutation; no evidence deletion."""
from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import re
import sqlite3
from time import monotonic
from .web_policy_reading_source import web_policy_inventory
from .context_static_reading import identity, complete_excerpt
from .query_output_loop_selection import valid_row
from .query_sql_slot_guard import ordinary_callable
from .storage import connect
from .context_budget import synchronize_estimate
from .performance_scoring import estimate_payload_tokens

REQUEST = re.compile(r'(?:(?:The|An) (?:embedded|in-app) (?:document )?WebView (?P<observation>[a-zA-Z -]{1,100})\. )?Locate (?:the )?executable (?:WebView )?(?:file )?access and (?:URL )?navigation policy (?:ownership|source|implementation)\.')
UNSUPPORTED = re.compile(r'\b(?:not|no|never|only|except|instead|without|compare|both|metadata|settings|log|logs|graph|trace|ignore|exclude|text|display|generate)\b', re.I)


def web_reading_request(query):
    if type(query) is not str or len(query) > 260 or UNSUPPORTED.search(query): return False
    match = REQUEST.fullmatch(query)
    if match is None: return False
    observation = match['observation'] or ''
    # Finite descriptive words grant no owner-name or runtime-truth authority.
    return all(word in {'permits','accepts','blocks','rejects','dangerous','file','and','script','URL','schemes','navigation','loads','content'} for word in observation.split())


def web_reading_order(project, original, payload):
    try:
        return _order(project, original, payload)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError, sqlite3.Error):
        return payload


def _order(project, original, payload):
    if not web_reading_request(payload.get('query')) or original.get('query') != payload['query']:
        return payload
    if payload.get('project_id') != project.project_id or original.get('project_id') != project.project_id:
        return payload
    freshness = payload.get('source_freshness', {}); generation = freshness.get('generation')
    if (freshness.get('status') != 'current' or type(generation) is not int
        or original.get('source_freshness', {}).get('status') != 'current'
        or original['source_freshness'].get('generation') != generation): return payload
    h = payload['query_handoff']; e = h.get('callable_evidence'); raw = original['query_handoff']; path_context = h.get('path_context') or {}
    if not ordinary_callable(e) or not e.get('primary') or path_context.get('activated') or path_context.get('wrapped_log_evidence'):
        return payload
    candidates = [e['primary'], *e['alternatives']]
    raw_e = raw.get('callable_evidence') or {}
    raw_candidates = [raw_e.get('primary'), *raw_e.get('alternatives', [])]
    if any(type(c) is not dict for c in raw_candidates): return payload
    if candidates != raw_candidates or len({identity(c) for c in candidates}) != len(candidates): return payload
    if any(a.get(k) for a in h.get('code_anchors', []) for k in ('identity_match', 'log_identity_match')): return payload
    paths = {c['file_path'] for c in candidates}
    paths.update(a['file_path'] for a in original.get('wiki_matches', []))
    paths.update(a['file_path'] for a in raw.get('code_anchors', []) if a.get('source') == 'wiki')
    if not 0 < len(paths) <= 8: return payload
    root = Path(project.root).resolve()
    if Path(original.get('project_path', '')).resolve() != root: return payload
    captured = {}; facts = []; total = 0; started = monotonic(); indexed = {}
    with connect(project) as db:
        db.execute('BEGIN')
        db.set_progress_handler(lambda: int(monotonic()-started > 2.0), 1000)
        state = [dict(r) for r in db.execute('SELECT * FROM code_index_state WHERE project_id=? LIMIT 2', (project.project_id,))]
        if len(state) != 1 or state[0].get('generation') != generation or state[0].get('status') != 'active': return payload
        for path in sorted(paths):
            if monotonic()-started > 2.0: return payload
            p = PurePosixPath(path); file = (root/path).resolve()
            if p.is_absolute() or '..' in p.parts or str(p) != path or p.suffix != '.ets' or not file.is_relative_to(root): return payload
            with file.open('rb') as stream: data = stream.read(2*1024*1024+1)
            total += len(data)
            if len(data) > 2*1024*1024 or total > 8*1024*1024: return payload
            source = data.decode('utf-8'); inventory = web_policy_inventory(source)
            if inventory is None: return payload
            captured[file] = data; digest = hashlib.sha256(data).hexdigest()
            files = [dict(r) for r in db.execute('SELECT * FROM code_files WHERE project_id=? AND file_path=? LIMIT 2', (project.project_id,path))]
            if len(files) != 1 or files[0].get('source_digest') != digest or files[0].get('index_generation') != generation: return payload
            rows = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path=? LIMIT 513', (project.project_id,path))]
            if len(rows) > 512 or monotonic()-started > 2.0: return payload
            indexed[path] = (rows, digest, inventory['methods'])
            for f in inventory['chains']:
                owners = [r for r in rows if r.get('qualified_name') == f['owner'] and r.get('symbol') == f['owner']]
                methods = [r for r in rows if r.get('qualified_name') == f['owner']+'.build']
                if len(owners) != 1 or len(methods) != 1: return payload
                owner, method = owners[0], methods[0]
                if any(not valid_row(r,project) or r.get('source_digest') != digest or r.get('index_generation') != generation for r in (owner,method)): return payload
                if any(db.execute('SELECT COUNT(*) FROM code_symbols WHERE project_id=? AND symbol_key=?',(project.project_id,r['symbol_key'])).fetchone()[0] != 1 for r in (owner,method)): return payload
                if (owner['symbol_type'] != 'component' or owner['owner_kind'] != 'component'
                    or method['owner_name'] != f['owner'] or method['owner_kind'] != 'component'
                    or method['symbol_type'] not in {'method','function'} or method['symbol'] != 'build'
                    or (owner['start_line'],owner['end_line']) != (f['class_start'],f['class_end'])
                    or (method['start_line'],method['end_line']) != (f['start_line'],f['end_line'])): return payload
                facts.append((path,f,source))
        for c in candidates:
            path, owner_name, symbol, lo, hi = identity(c)
            rows, digest, declarations = indexed[path]
            declared = [d for d in declarations if (d['owner'],d['method'],d['start_line'],d['end_line']) == (owner_name,symbol,lo,hi)]
            if len(declared) != 1: return payload
            owners = [r for r in rows if r.get('qualified_name') == owner_name and r.get('symbol') == owner_name]
            if len(owners) != 1: return payload
            owner = owners[0]; declaration = declared[0]
            if (not valid_row(owner,project) or owner.get('source_digest') != digest or owner.get('index_generation') != generation
                or owner.get('owner_name') not in ('',None) or owner.get('owner_kind') != 'component'
                or owner.get('symbol_type') != 'component' or c.get('owner_kind') != 'component'
                or (owner.get('start_line'),owner.get('end_line')) != (declaration['class_start'],declaration['class_end'])
                or db.execute('SELECT COUNT(*) FROM code_symbols WHERE project_id=? AND symbol_key=?',(project.project_id,owner['symbol_key'])).fetchone()[0] != 1): return payload
            selected = [r for r in rows if r.get('qualified_name') == owner_name+'.'+symbol]
            if len(selected) != 1: return payload
            row = selected[0]
            if (not valid_row(row,project) or row.get('source_digest') != digest or row.get('index_generation') != generation
                or row.get('owner_name') != owner_name or row.get('owner_kind') != c.get('owner_kind')
                or row.get('symbol') != symbol or row.get('symbol_type') not in {'function','method'}
                or (row.get('start_line'),row.get('end_line')) != (lo,hi)
                or c['source_range'].get('selection_reason') != 'callable_symbol_range'
                or db.execute('SELECT COUNT(*) FROM code_symbols WHERE project_id=? AND symbol_key=?',(project.project_id,row['symbol_key'])).fetchone()[0] != 1): return payload
        # Count source chains before considering displayed body or candidate rank.
        if len(facts) != 1: return payload
        path,f,source = facts[0]; key = (path,f['owner'],'build',f['start_line'],f['end_line'])
        matches = [i for i,c in enumerate(candidates) if identity(c) == key and c.get('owner_kind') == 'component'
                   and c['source_range'].get('selection_reason') == 'callable_symbol_range']
        if len(matches) != 1 or matches[0] == 0: return payload
        if not complete_excerpt(h['code_anchors'],path,f['start_line'],f['end_line'],source): return payload
        for file,data in captured.items():
            if monotonic()-started > 2.0: return payload
            with file.open('rb') as stream:
                if stream.read(2*1024*1024+1) != data: return payload
    index = matches[0]; order = [index,*[i for i in range(len(candidates)) if i != index]]
    result = deepcopy(payload); changed = result['query_handoff']['callable_evidence']
    changed['primary'] = deepcopy(candidates[index]); changed['alternatives'] = [deepcopy(candidates[i]) for i in order[1:]]
    changed['certainty'] = 'uncertain'; changed['boundary'] = 'partial_static_web_policy_reading_not_runtime'
    changed['reading_basis'] = {'prior':[order.index(i) for i in range(len(candidates))]}
    synchronize_estimate(result)
    return result if estimate_payload_tokens(result) <= result.get('output_budget',{}).get('target_tokens',0) else payload
