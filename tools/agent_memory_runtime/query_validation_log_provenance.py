# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite validation-only raw log provenance; no serving/query authority."""
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3

from .storage import connect
from .query_output_loop_selection import snapshot, valid_row
from .semantic_models import symbol_key
from .query_ui_divider_wrapped_provenance import positive, path_ok
from .query_touch_log_provenance import visible

MAX_SOURCE = 2097152


def read_source_bytes(project, path, limit):
    """One bounded binary read; returns sentinel too, never source authority."""
    if not path_ok(path) or type(limit) is not int or not 0 < limit <= MAX_SOURCE + 1:
        raise ValueError('read shape')
    root = Path(project.root).resolve()
    lexical = root / path
    if any(p.is_symlink() for p in (lexical, *lexical.parents) if p != root.parent):
        raise ValueError('source symlink')
    actual = lexical.resolve()
    if not actual.is_relative_to(root) or not actual.is_file():
        raise ValueError('source path')
    with actual.open('rb') as stream:
        return stream.read(limit)


class Resolver:
    def __init__(self, db, project, paths, bounded):
        self.db, self.project, self.paths, self.bounded = db, project, set(paths), bounded
        self.cache, self.files, self.sources = {}, {}, {}
        self.rows = []

    def one(self, table, clause, args):
        key = (table, clause, args)
        if key not in self.cache:
            found = self.db.execute('SELECT * FROM '+table+' WHERE '+clause+' LIMIT 2', args).fetchall()
            if len(found) != 1:
                raise ValueError('missing/ambiguous '+table)
            row = found[0]
            # DB strings are checked before JSON parse or detached row copies.
            if type(row) is not sqlite3.Row or len(row) > 128:
                raise ValueError('DB row shape')
            keys = row.keys()
            if len(set(keys)) != len(keys) or any(type(k) is not str or len(k) > 128 for k in keys):
                raise ValueError('DB keys')
            values = [row[k] for k in keys]
            if not self.bounded(values):
                raise ValueError('DB field bounds')
            value = {k: row[k] for k in keys}
            self.rows.append(value)
            if not self.bounded(self.rows):
                raise ValueError('aggregate DB metadata')
            self.cache[key] = value
        return self.cache[key]

    def current(self, row, generation):
        p = row.get('file_path')
        if (not positive(row.get('id')) or row.get('project_id') != self.project.project_id
                or not path_ok(p) or p not in self.paths or row.get('index_generation') != generation):
            raise ValueError('outside/stale dependency')
        file = self.one('code_files', 'project_id=? AND file_path=?', (self.project.project_id, p))
        if (not positive(file.get('id')) or file.get('index_generation') != generation
                or type(row.get('source_digest')) is not str or row['source_digest'] != file.get('source_digest')):
            raise ValueError('source identity')
        self.files[p] = file

    def method(self, path, name, line, generation):
        if not path_ok(path) or path not in self.paths or type(name) is not str or not positive(line):
            raise ValueError('method path')
        row = self.one('code_symbols', 'project_id=? AND file_path=? AND symbol=? AND symbol_type=?',
                       (self.project.project_id, path, name, 'function'))
        if not valid_row(row, self.project) or not row['start_line'] <= line <= row['end_line']:
            raise ValueError('method identity/range')
        language = {'arkts-static': 'ArkTS', 'typescript-static': 'TypeScript'}[row['semantic_adapter'].partition('@')[0]]
        if (type(row.get('signature')) is not str or not row['signature'] or
                row['symbol_key'] != symbol_key(language, path, row['qualified_name'], row['signature'])):
            raise ValueError('method key')
        alias = self.one('code_symbols', 'project_id=? AND (id=? OR symbol_key=?)',
                         (self.project.project_id, row['id'], row['symbol_key']))
        if alias != row:
            raise ValueError('method alias')
        self.current(row, generation)
        return row

    def read_all(self):
        # All dependency paths have already been checked before the first open.
        for path, file in sorted(self.files.items()):
            raw = read_source_bytes(self.project, path, MAX_SOURCE + 1)
            if type(raw) is not bytes or len(raw) > MAX_SOURCE or hashlib.sha256(raw).hexdigest() != file['source_digest']:
                raise ValueError('source bytes')
            self.sources[path] = raw.decode('utf-8').splitlines()


def projection(row, stored, bounded):
    for key, expected in stored.items():
        if key in ('call_path', 'call_path_locations'):
            expected = json.loads(expected)
            if not bounded(expected):
                raise ValueError('effect JSON bounds')
        actual = row.get(key)
        if type(actual) is not type(expected) or actual != expected:
            raise ValueError('projection '+key)


def typed_edge(r, caller, target, relation, target_type, index):
    edge = r.one('memory_edges',
                 'project_id=? AND source_type=? AND source_id=? AND relation=? AND target_type=? AND target_id=? AND valid_to IS NULL',
                 (r.project.project_id, 'code_symbol', caller['id'], relation, target_type, target['id']))
    if (not positive(edge['id']) or not edge['valid_from'] or edge['source_revision'] != index['source_revision']
            or type(edge['confidence']) not in (int,float) or not math.isfinite(edge['confidence'])
            or not 0 <= edge['confidence'] <= 1):
        raise ValueError('edge version')
    return edge


def direct(r, supplied, generation):
    row = r.one('code_log_statements', 'project_id=? AND id=?', (r.project.project_id, supplied['id']))
    projection(supplied, row, r.bounded)
    r.current(row, generation)
    if not positive(row.get('line')) or any(type(row.get(k)) is not str or not row[k]
            for k in ('function','logger','level','message_template','raw_statement')):
        raise ValueError('direct shape')
    return {'row': row}


def wrapped(r, supplied, index):
    row = r.one('code_log_effects', 'project_id=? AND id=?', (r.project.project_id, supplied['id']))
    projection(supplied, row, r.bounded)
    if (type(row.get('wrapper_depth')) is not int or row['wrapper_depth'] != 1
            or row.get('evidence_class') != 'static_wrapped' or type(row.get('truncated')) is not int
            or row['truncated'] != 0 or not positive(row.get('line')) or not positive(row.get('sink_log_id'))):
        raise ValueError('unsupported effect')
    generation = index['generation']; r.current(row, generation)
    paths, locations = json.loads(row['call_path']), json.loads(row['call_path_locations'])
    if (type(paths) is not list or type(locations) is not list or len(paths) != 3 or len(locations) != 3
            or not r.bounded([paths, locations])):
        raise ValueError('path shape')
    refs = []
    for name, location in zip(paths, locations):
        if type(name) is not str or not name or type(location) is not str or location.count('#') != 1:
            raise ValueError('location')
        path, actual = location.split('#')
        if actual != name or not path_ok(path) or path not in r.paths:
            raise ValueError('outside dependency')
        refs.append((path,name))
    sink = r.one('code_log_statements', 'project_id=? AND id=?', (r.project.project_id,row['sink_log_id']))
    r.current(sink, generation)
    if (refs[0] != (row['file_path'],row['function']) or refs[1] != (sink['file_path'],sink['function'])
            or refs[2] != (sink['file_path'],sink['logger']+'.'+sink['level']) or paths[1] != row['wrapper_symbol']
            or row['logger'] != sink['logger'] or row['level'] != sink['level']):
        raise ValueError('sink projection')
    caller = r.method(*refs[0],row['line'],generation)
    callee = r.method(*refs[1],sink['line'],generation)
    if caller['id'] == callee['id']:
        raise ValueError('cycle')
    call = typed_edge(r,caller,callee,'calls','code_symbol',index)
    proof = json.loads(call['evidence'])
    if (not r.bounded(proof) or type(proof) is not dict or proof.get('schema_version') != 'semantic-evidence/v1'
            or proof.get('evidence_class') != 'static' or proof.get('line') != row['line']
            or not positive(proof.get('line')) or not caller['start_line'] <= proof['line'] <= caller['end_line']
            or proof.get('source_digest') != caller['source_digest'] or proof.get('adapter') != caller['semantic_adapter']
            or call['evidence_kind'] != 'static_semantic_calls'
            or call['extractor_version'] != 'semantic-index:v1/'+caller['semantic_adapter']):
        raise ValueError('typed call proof')
    emits = typed_edge(r,callee,sink,'emits_log','code_log_statement',index)
    if (emits['extractor_version'] != 'code-wiki:v4' or emits['evidence_kind'] != 'code_observability'
            or emits['evidence'] != sink['file_path']+':'+str(sink['line'])):
        raise ValueError('emits proof')
    return dict(row=row,sink=sink,methods=[caller,callee],calls=[call],emits=emits)


def verify_validation_logs(project, capture, raw_logs, scope_paths):
    """Private captured inventory + exact raw projection, rechecked on every call."""
    try:
        from .query_validation_log_capture import validation_log_inventory, bounded_metadata
        if (type(scope_paths) not in (list,tuple) or not 0 < len(scope_paths) <= 12
                or any(not path_ok(p) for p in scope_paths) or len(set(scope_paths)) != len(scope_paths)
                or type(raw_logs) is not list or not bounded_metadata([list(scope_paths),raw_logs])):
            return None
        inventory = validation_log_inventory(project,capture)
        if type(inventory) is not dict:
            return None
        if type(inventory.get('scope_paths')) is not list or sorted(scope_paths) != inventory['scope_paths']:
            return None
        rows = {k:inventory[k] for k in ('direct','effects')}
        if (any(type(v) is not list for v in rows.values()) or not 0 < sum(map(len,rows.values())) <= 64
                or not bounded_metadata([rows,raw_logs])):
            return None
        with connect(project) as db:
            db.execute('BEGIN'); r = Resolver(db,project,scope_paths,bounded_metadata)
            index = r.one('code_index_state','project_id=?',(project.project_id,))
            graph = r.one('graph_runtime_state','project_id=?',(project.project_id,))
            if (index['status'] != 'active' or not positive(index['generation']) or not positive(graph['graph_revision'])
                    or type(index['source_revision']) is not str or not index['source_revision']
                    or index['extractor_version'] != 'code-derived:v1'):
                return None
            items = {}
            for kind in ('direct','effects'):
                for row in rows[kind]:
                    if type(row) is not dict or not positive(row.get('id')) or (kind,row['id']) in items:
                        return None
                    items[kind,row['id']] = direct(r,row,index['generation']) if kind=='direct' else wrapped(r,row,index)
            seen = set()
            for log in raw_logs:
                if type(log) is not dict:return None
                effect = log.get('effect_id') is not None
                key = ('effects' if effect else 'direct',log.get('effect_id') if effect else log.get('log_id'))
                if not positive(key[1]) or key not in items or key in seen:return None
                visible(log,items[key],effect); seen.add(key)
            r.read_all()
            for item in items.values():
                sink = item.get('sink',item['row']); lines = r.sources[sink['file_path']]
                if not positive(sink.get('line')) or sink['line'] > len(lines):return None
                if sink['raw_statement'].strip() not in lines[sink['line']-1]:return None
                for method in item.get('methods',[]):
                    if method['end_line'] > len(r.sources[method['file_path']]):return None
                if item.get('calls'):
                    caller,callee = item['methods']; line = item['row']['line']
                    if not re.search(r'\.\s*'+re.escape(callee['symbol'])+r'\s*\(',r.sources[caller['file_path']][line-1]):return None
            return snapshot(dict(contract='validation-raw-log-provenance/v1',inventory=rows,logs=raw_logs,
                items=[dict(kind=k[0],id=k[1],witness=v) for k,v in items.items()],
                files=[dict(file=f,source_digest=f['source_digest']) for _,f in sorted(r.files.items())],index=index,graph=graph))
    except (AttributeError,KeyError,TypeError,ValueError,IndexError,OSError,UnicodeError,sqlite3.Error,OverflowError,RecursionError):
        return None
