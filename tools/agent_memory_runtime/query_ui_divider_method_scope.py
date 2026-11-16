"""Exact recalled-build identity witnesses; never recall new methods or paths."""
from pathlib import Path
import hashlib
import re
from .storage import connect
from .query_command_table_scope import IDENTITY, FILE_FIELDS, same_fields, symbol_alias
from .query_output_loop_selection import valid_row
from .query_ui_divider_scope import divider_frames
from .query_ui_divider_request import qualifier_matches
from .ui_divider_source import tokenize, Unknown


def read_current(project, file):
    root = Path(project.root).resolve(); path = (root/file['file_path']).resolve()
    if not path.is_relative_to(root):
        return None
    with path.open('rb') as stream:
        raw = stream.read(2*1024*1024+1)
    if len(raw) > 2*1024*1024 or hashlib.sha256(raw).hexdigest() != file['source_digest']:
        return None
    return raw.decode('utf-8')


def source_component_names(source):
    # A conservative inventory check only. It cannot confer a positive witness.
    if not re.search(r'\bstruct\b|@\s*Component\b', source):
        return set()
    try:
        tokens, _ = tokenize(source, declaration_inventory=True)
    except (Unknown, ValueError, TypeError):
        return None
    result = set()
    for index, token in enumerate(tokens):
        if token.kind == 'name' and token.value == 'struct':
            if index+1 >= len(tokens) or tokens[index+1].kind != 'name':
                return None
            result.add(tokens[index+1].value)
    return result


def method_rooted_frames(project, pool, qualifiers):
    if type(pool) is not list or not pool or any(type(r) is not dict for r in pool):
        return None
    paths = set()
    for row in pool:
        name = row.get('file_path')
        if (row.get('kind') not in {'file', 'symbol'} or not isinstance(name, str) or not name
                or Path(name).is_absolute() or '..' in Path(name).parts):
            return None
        paths.add(name)
    with connect(project) as db:
        marks = ','.join('?' for _ in paths); args = (project.project_id, *sorted(paths))
        rows = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ('+marks+')', args)]
        files = [dict(r) for r in db.execute('SELECT * FROM code_files WHERE project_id=? AND file_path IN ('+marks+')', args)]
        for row in pool:
            if row['kind'] == 'symbol':
                ident, key = row.get('id'), row.get('symbol_key')
                if type(ident) is not int or ident <= 0 or (key is not None and not isinstance(key, str)):
                    return None
                clause, values = 'id=?', (project.project_id, ident)
                if isinstance(key, str) and key:
                    clause += ' OR symbol_key=?'; values += (key,)
                aliases = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND ('+clause+') LIMIT 2', values)]
                if len(aliases) != 1 or not same_fields(row, aliases[0], IDENTITY):
                    return None
            else:
                matches = [r for r in files if r['id'] == row.get('id') or r['file_path'] == row['file_path']]
                if len(matches) != 1 or not same_fields(row, matches[0], FILE_FIELDS):
                    return None
    sources, examined, required = {}, [], []
    for path in sorted(paths):
        matches = [r for r in files if r['file_path'] == path]
        if len(matches) != 1:
            return None
        file = matches[0]
        if type(file.get('id')) is not int or file['id'] <= 0 or file.get('project_id') != project.project_id:
            return None
        source = read_current(project, file)
        if source is None:
            return None
        sources[path] = source; examined.append((path, file['source_digest']))
        if Path(path).suffix == '.ets':
            names = source_component_names(source)
            if names is None:
                return None
            wanted = {n for n in names if any(qualifier_matches(t, n) for t in qualifiers)}
            indexed = {r['symbol'] for r in rows if r['file_path'] == path and r.get('symbol_type') in {'component', 'struct'}
                       and any(qualifier_matches(t, r['symbol']) for t in qualifiers)}
            if wanted != indexed:
                return None
            for name in sorted(wanted):
                declarations = [r for r in rows if r['file_path'] == path and r['symbol'] == name
                                and r['symbol_type'] in {'component', 'struct'}]
                builds = [r for r in rows if r['file_path'] == path and r.get('owner_name') == name
                          and r.get('symbol') == 'build' and r.get('owner_kind') == 'component']
                if len(declarations) != 1 or len(builds) != 1:
                    return None
                original = [r for r in pool if r['kind'] == 'symbol' and symbol_alias(r, builds[0])]
                if len(original) != 1 or not same_fields(original[0], builds[0], IDENTITY):
                    return None
                required.append((path, name))
    if not required or len(required) > 12:
        return None
    virtual = [dict(r) for r in pool]; witnesses = []
    for root in pool:
        if root['kind'] != 'symbol' or root.get('symbol') != 'build' or root.get('owner_kind') != 'component':
            continue
        if (not valid_row(root, project) or root.get('symbol_type') not in {'function', 'method'}
                or root.get('signature') != 'build():unknown'
                or root.get('qualified_name') != root.get('owner_name', '')+'.build'):
            return None
        parents = [r for r in rows if r['file_path'] == root['file_path'] and r['symbol'] == root['owner_name']
                   and r['symbol_type'] in {'component', 'struct'}]
        fs = [r for r in files if r['file_path'] == root['file_path']]
        if len(parents) != 1 or len(fs) != 1:
            return None
        parent, file = parents[0], fs[0]
        if (not valid_row(parent, project) or parent['source_digest'] != root['source_digest']
                or parent['source_digest'] != file['source_digest']
                or parent['index_generation'] != root['index_generation']
                or parent['index_generation'] != file['index_generation']):
            return None
        for row, kind in ((parent, 'symbol'), (file, 'file')):
            if not any(r['kind'] == kind and r.get('id') == row['id'] for r in virtual):
                virtual.append(dict(row, kind=kind)); witnesses.append(dict(row, kind=kind))
    frames = []
    for token in qualifiers:
        wanted = [r for r in rows if r['symbol_type'] in {'component', 'struct'} and qualifier_matches(token, r['symbol'])]
        if not wanted:
            continue
        current = divider_frames(project, virtual, token)
        if current is None:
            return None
        frames.extend(current)
    frames = list({(f['path'], f['owner']['id']): f for f in frames}.values())
    if (not frames or len(frames) > 12
            or any(Path(f['path']).suffix != '.ets' or f['file'].get('language') != 'ArkTS' for f in frames)):
        return None
    # Every accepted method is still an original-pool root, not a completed witness.
    if any(not any(r['kind'] == 'symbol' and r.get('id') == f['build']['id']
                   and same_fields(r, f['build'], IDENTITY) for r in pool) for f in frames):
        return None
    return frames, sources, tuple(examined), witnesses
