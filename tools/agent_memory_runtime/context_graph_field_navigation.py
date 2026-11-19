"""Optional additive navigation from this response's authenticated import sources.

No new ranking, owner/causal authority, body delivery or recursive graph search.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath
import sqlite3
from time import monotonic

from .context_budget import synchronize_estimate
from .context_field_alternative import field_read_request, guarded_calls
from .performance_scoring import estimate_payload_tokens
from .query_output_loop_selection import valid_row
from .query_validation_field_request import parts
from .source_exploration import exploration_contract, EXPANSION_ANCHOR_LIMIT
from .storage import connect
from .validation_field_lexical import tokenize_validation
from .validation_field_source import Unknown

MAX_EDGES = 10
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_ROWS_PER_FILE = 128
MAX_SECONDS = 2.0


def append_graph_field_navigation(project, original, payload, *, enabled=False):
    if type(payload) is not dict or enabled is not True:
        return payload
    budget = payload.get('output_budget')
    if type(budget) is not dict or budget.get('target_tokens') != 2000:
        return payload
    try:
        return _append(project, original, payload)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError,
            sqlite3.Error, Unknown, RecursionError):
        return payload


def _append(project, original, payload):
    anchors = payload['query_handoff']['code_anchors']
    expansions = sum(a.get('role') == 'expansion' for a in anchors)
    if expansions >= EXPANSION_ANCHOR_LIMIT or len(anchors) >= 5:
        return payload
    additions = qualify_graph_field_navigation(project, original, payload)
    if not additions or len(additions) + expansions > EXPANSION_ANCHOR_LIMIT or len(anchors) + len(additions) > 5:
        return payload
    trial = deepcopy(payload)
    trial['query_handoff']['code_anchors'].extend(additions)
    synchronize_estimate(trial)
    return trial if estimate_payload_tokens(trial) <= 2000 else payload


@dataclass(frozen=True)
class _DisplayReceipt:
    query: str
    project_id: str
    generation: int
    navigation: list
    bodies: list | None


def qualify_graph_field_navigation(project, original, payload, *, _capture_body=False):
    permission = field_read_request(payload.get('query'))
    if not permission or not isinstance(original, dict) or original.get('query') != payload['query']:
        return None
    root = Path(project.root).resolve()
    if (original.get('project_id') != project.project_id or payload.get('project_id') != project.project_id
            or Path(original.get('project_path', '')).resolve() != root):
        return None
    fresh = payload.get('source_freshness') or {}; raw_fresh = original.get('source_freshness') or {}
    generation = fresh.get('generation')
    if (fresh.get('status') != 'current' or raw_fresh.get('status') != 'current'
            or type(generation) is not int or generation <= 0 or raw_fresh.get('generation') != generation):
        return None
    h = payload['query_handoff']; anchors = h.get('code_anchors')
    if (type(anchors) is not list or h.get('source_exploration') != exploration_contract()
            or any(type(a) is not dict or a.get('role') not in {'primary', 'expansion'} for a in anchors)):
        return None
    primary = sum(a['role'] == 'primary' for a in anchors)
    expansions = len(anchors) - primary
    if primary > 3 or expansions > EXPANSION_ANCHOR_LIMIT or len(anchors) > 5:
        return None
    edges = original.get('edge_matches')
    if type(edges) is not list or not 0 < len(edges) <= MAX_EDGES:
        return None
    started = monotonic(); captured = {}; additions = {}; edge_ids = set()
    def expired():
        return monotonic() - started > MAX_SECONDS
    def read_file(row):
        path = row['file_path']; p = PurePosixPath(path); file = (root / path).resolve()
        if (p.is_absolute() or '..' in p.parts or str(p) != path or not file.is_relative_to(root)
                or p.suffix not in {'.ts', '.ets'} or row.get('index_generation') != generation):
            raise ValueError('file identity')
        if path not in captured:
            with file.open('rb') as stream:
                data = stream.read(MAX_FILE_BYTES + 1)
            if (len(data) > MAX_FILE_BYTES or b'\0' in data or expired()
                    or sum(len(x[1]) for x in captured.values()) + len(data) > MAX_TOTAL_BYTES):
                raise ValueError('source resource limit')
            captured[path] = (file, data, hashlib.sha256(data).hexdigest())
        file, data, digest = captured[path]
        if row.get('source_digest') != digest:
            raise ValueError('source digest')
        return file, data, digest
    with connect(project) as db:
        db.execute('BEGIN')
        db.set_progress_handler(lambda: int(expired()), 1000)
        states = [dict(r) for r in db.execute('SELECT * FROM code_index_state WHERE project_id=?', (project.project_id,))]
        if len(states) != 1 or states[0].get('generation') != generation or states[0].get('status') != 'active':
            return None
        for supplied in edges:
            if type(supplied) is not dict:
                return None
            if supplied.get('relation') != 'imports':
                continue
            eid = supplied.get('id')
            if type(eid) is not int or eid <= 0 or eid in edge_ids:
                return None
            edge_ids.add(eid)
            rows = [dict(r) for r in db.execute('SELECT * FROM memory_edges WHERE project_id=? AND id=?', (project.project_id, eid))]
            if len(rows) != 1:
                return None
            edge = rows[0]
            keys = ('project_id', 'source_type', 'source_id', 'relation', 'target_type', 'target_id',
                    'evidence_kind', 'valid_from', 'valid_to', 'extractor_version')
            if (any(edge.get(k) != supplied.get(k) for k in keys) or edge.get('valid_to') is not None
                    or edge.get('source_type') != 'code_file' or edge.get('target_type') != 'code_file'
                    or edge.get('evidence_kind') != 'static_import'):
                return None
            endpoints = []
            for key in ('source_id', 'target_id'):
                rid = edge[key]
                if type(rid) is not int or rid <= 0:
                    return None
                rows = [dict(r) for r in db.execute('SELECT * FROM code_files WHERE project_id=? AND id=?', (project.project_id, rid))]
                if len(rows) != 1:
                    return None
                endpoints.append(rows[0])
            source, data, digest = read_file(endpoints[0]); target, _, _ = read_file(endpoints[1])
            facts = guarded_calls(data.decode('utf-8'))
            if expired():
                return None
            if facts is None:
                continue  # unsupported source remains evidence, not a negative or uniqueness proof
            if not _import_matches(source, target, root, data.decode('utf-8')):
                return None
            matching = [f for f in facts if parts(f['field']) == permission['field_parts']]
            if not matching:
                continue
            symbols = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path=? LIMIT ?',
                       (project.project_id, endpoints[0]['file_path'], MAX_ROWS_PER_FILE + 1))]
            if len(symbols) > MAX_ROWS_PER_FILE:
                return None
            for fact in matching:
                method = _unique(symbols, fact['owner'] + '.' + fact['method'])
                owner = _unique(symbols, fact['owner'])
                if not _valid_fact(db, project, method, owner, fact, digest, generation):
                    return None
                path = method['file_path']; lo, hi = method['start_line'], method['end_line']
                # Existing path already provides navigation; do not create a competing duplicate.
                if any(a.get('file_path') == path for a in anchors):
                    continue
                key = (path, method['id'])
                if key in additions:
                    continue
                additions[key] = dict(file_path=path, symbol=method['symbol'], record_type='code_symbol',
                    record_ids=[method['id']], source_ranges=[dict(symbol=method['symbol'], start_line=lo, end_line=hi)],
                    read_window=dict(start_line=lo, end_line=hi), role='expansion',
                    display_basis=dict(kind='partial_static_guarded_field_call', field=fact['field'],
                        domain_unverified=True, action_unverified=True, edge_id=eid, gap='missing_state_owner'))
        for file, data, digest in captured.values():
            with file.open('rb') as stream:
                reread = stream.read(MAX_FILE_BYTES + 1)
            if hashlib.sha256(reread).hexdigest() != digest or expired():
                return None
    navigation = list(additions.values())
    if _capture_body:
        bodies = []
        try:
            for anchor in navigation:
                lo, hi = anchor['read_window']['start_line'], anchor['read_window']['end_line']
                data = captured[anchor['file_path']][1]
                content = '\n'.join(data.decode('utf-8').splitlines()[lo-1:hi])
                if len(content) > 1500 or expired():
                    bodies = None
                    break
                bodies.append(dict(symbol=anchor['symbol'], start_line=lo, end_line=hi,
                    content=content, source='current_worktree',
                    selection_reason='authenticated_graph_field_body', focus_line=None, truncated=False))
        except (UnicodeError, ValueError, KeyError):
            bodies = None
        return _DisplayReceipt(payload['query'], project.project_id, generation, navigation, bodies)
    return navigation


def _unique(rows, name):
    matches = [r for r in rows if r.get('qualified_name') == name]
    if len(matches) != 1:
        raise ValueError('ambiguous identity')
    return matches[0]


def _valid_fact(db, project, method, owner, fact, digest, generation):
    for row in (method, owner):
        if (not valid_row(row, project) or row['source_digest'] != digest or row['index_generation'] != generation
                or db.execute('SELECT COUNT(*) FROM code_symbols WHERE project_id=? AND symbol_key=?',
                   (project.project_id, row['symbol_key'])).fetchone()[0] != 1):
            return False
    kind = 'component' if fact['kind'] in {'struct', 'component'} else 'class'
    return (method['symbol_type'] in {'method', 'function'} and owner['symbol_type'] == kind
            and method['file_path'] == owner['file_path'] and not owner.get('owner_name')
            and owner['symbol'] == fact['owner'] and method['owner_name'] == fact['owner']
            and method['symbol'] == fact['method'] and owner['owner_kind'] == kind and method['owner_kind'] == kind
            and (method['start_line'], method['end_line']) == (fact['start_line'], fact['end_line'])
            and (owner['start_line'], owner['end_line']) == (fact['owner_start'], fact['owner_end'])
            and 0 < method['start_line'] <= method['end_line'] and method['end_line'] - method['start_line'] < 40)


def _import_matches(source, target, root, text):
    tokens, _ = tokenize_validation(text)
    paths = [tokens[i + 1].value for i, token in enumerate(tokens[:-1])
             if token.kind == 'name' and token.value == 'from' and tokens[i + 1].kind == 'string']
    matched = False
    for path in paths:
        if not path.startswith('.'):
            continue
        base = (source.parent / path).resolve()
        if not base.is_relative_to(root):
            return False
        options = [base] if base.suffix else [base.with_suffix('.ets'), base.with_suffix('.ts')]
        existing = [p for p in options if p.is_file()]
        if len(existing) > 1:
            return False
        if existing == [target]:
            matched = True
    return matched
