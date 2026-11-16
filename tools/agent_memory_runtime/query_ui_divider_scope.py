# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Original-pool component/build/file frames; no new method recall."""
from pathlib import Path
from .storage import connect
from .query_command_table_scope import IDENTITY, FILE_FIELDS, same_fields, symbol_alias
from .query_output_loop_selection import valid_row
from .query_ui_divider_request import qualifier_matches


def divider_frames(project, pool, qualifier):
    if type(pool) is not list or not pool or any(type(r) is not dict for r in pool):
        return None
    paths = set()
    for row in pool:
        path = row.get('file_path')
        if (row.get('kind') not in {'file', 'symbol'} or not isinstance(path, str)
                or not path or Path(path).is_absolute() or '..' in Path(path).parts):
            return None
        paths.add(path)
    with connect(project) as db:
        marks = ','.join('?' for _ in paths)
        args = (project.project_id, *sorted(paths))
        rows = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ('+marks+')', args)]
        files = [dict(r) for r in db.execute('SELECT * FROM code_files WHERE project_id=? AND file_path IN ('+marks+')', args)]
        verified_symbols = {}
        for row in pool:
            if row['kind'] != 'symbol':
                continue
            ident, key = row.get('id'), row.get('symbol_key')
            if type(ident) is not int or ident <= 0 or (key is not None and not isinstance(key, str)):
                return None
            clause, values = 'id=?', (project.project_id, ident)
            if isinstance(key, str) and key:
                clause += ' OR symbol_key=?'; values += (key,)
            # Identity validation only: never admit a DB-only source or symbol.
            aliases = [dict(r) for r in db.execute(
                'SELECT * FROM code_symbols WHERE project_id=? AND ('+clause+') LIMIT 2', values)]
            if len(aliases) != 1 or not same_fields(row, aliases[0], IDENTITY):
                return None
            verified_symbols[ident] = aliases[0]
    symbols, recalled_files = {}, {}
    for row in pool:
        if row['kind'] == 'file':
            matches = [r for r in files if r['id'] == row.get('id') or r['file_path'] == row['file_path']]
            if len(matches) != 1 or not same_fields(row, matches[0], FILE_FIELDS):
                return None
            recalled_files[row['file_path']] = matches[0]
        else:
            symbols[row['id']] = verified_symbols[row['id']]
    wanted = set()
    # File hints are presentation fields, not DB identity. Inspect their current
    # declaration rows only to detect missing original-pool members, never admit them.
    for row in rows:
        if (row['file_path'] in recalled_files and row.get('symbol_type') in {'component', 'struct'}
                and qualifier_matches(qualifier, row.get('symbol'))):
            wanted.add((row['file_path'], row['symbol']))
    for row in symbols.values():
        declaration = row.get('symbol_type') in {'component', 'struct'}
        owner = row.get('symbol') if declaration else row.get('owner_name')
        if (declaration or row.get('owner_kind') == 'component') and qualifier_matches(qualifier, owner):
            wanted.add((row['file_path'], owner))
    if not wanted or len(wanted) > 12:
        return None
    frames = []
    for path, name in sorted(wanted):
        owners = [r for r in rows if r['file_path'] == path and r['symbol'] == name
                  and r['symbol_type'] in {'component', 'struct'}]
        if len(owners) != 1:
            return None
        owner = owners[0]
        builds = [r for r in symbols.values() if r['file_path'] == path
                  and r.get('owner_name') == name and r.get('symbol') == 'build']
        file = recalled_files.get(path)
        if owner['id'] not in symbols or len(builds) != 1 or file is None:
            return None
        build = builds[0]
        if (not valid_row(owner, project) or not valid_row(build, project)
                or owner.get('owner_kind') != 'component' or owner.get('owner_name') not in ('', None)
                or owner['qualified_name'] != name or build['owner_kind'] != 'component'
                or build['qualified_name'] != name+'.build' or build['symbol_type'] not in {'function', 'method'}
                or build.get('signature') != 'build():unknown' or type(file.get('index_generation')) is not int):
            return None
        members = [owner, build]
        if len({r['id'] for r in members}) != 2 or len({r['symbol_key'] for r in members}) != 2:
            return None
        for row in members:
            if (row['source_digest'] != file['source_digest'] or row['index_generation'] != file['index_generation']
                    or not owner['start_line'] <= row['start_line'] <= row['end_line'] <= owner['end_line']):
                return None
            aliases = [r for r in rows if symbol_alias(row, r)]
            if len(aliases) != 1 or not same_fields(aliases[0], row, IDENTITY):
                return None
        frames.append(dict(path=path, owner=owner, build=build, file=file, members=members))
    return frames
