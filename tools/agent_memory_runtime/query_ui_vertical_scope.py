"""Independent original-pool vertical frames; metadata is not a source witness."""
from pathlib import Path
import re
from .storage import connect
from .query_command_table_scope import IDENTITY, FILE_FIELDS, same_fields
from .query_output_loop_selection import valid_row, snapshot
from .query_ui_divider_request import qualifier_matches


def vertical_frames(project, pool, qualifier):
    if (type(pool) is not list or not pool or any(type(r) is not dict for r in pool)
            or type(qualifier) is not str or re.fullmatch('[a-z]{1,24}', qualifier) is None):
        return None
    paths = set()
    for item in pool:
        path = item.get('file_path')
        if (item.get('kind') not in {'file', 'symbol'} or type(path) is not str or not path
                or Path(path).is_absolute() or '..' in Path(path).parts or Path(path).as_posix() != path):
            return None
        paths.add(path)
    # New inventory resource contract: admitted paths64, matching frames12 below.
    if len(paths) > 64:
        return None
    with connect(project) as db:
        db.execute('BEGIN')
        projects = [dict(r) for r in db.execute('SELECT * FROM projects WHERE project_id=?', (project.project_id,))]
        if (len(projects) != 1 or type(projects[0].get('project_path')) is not str
                or Path(projects[0]['project_path']).resolve() != Path(project.root).resolve()):
            return None
        states = [dict(r) for r in db.execute('SELECT * FROM code_index_state WHERE project_id=?', (project.project_id,))]
        if (len(states) != 1 or type(states[0].get('generation')) is not int
                or states[0]['generation'] <= 0 or states[0].get('status') != 'active'):
            return None
        generation = states[0]['generation']
        args = (project.project_id, *sorted(paths)); marks = ','.join('?' for _ in paths)
        rows = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ('+marks+') ORDER BY id', args)]
        files = [dict(r) for r in db.execute('SELECT * FROM code_files WHERE project_id=? AND file_path IN ('+marks+') ORDER BY id', args)]
        scope_files = []
        for path in sorted(paths):
            matches = [r for r in files if r['file_path'] == path]
            if len(matches) != 1:
                return None
            file = matches[0]
            language = {'.ets': 'ArkTS', '.ts': 'TypeScript'}.get(Path(path).suffix)
            if (type(file.get('id')) is not int or file['id'] <= 0
                    or file.get('project_id') != project.project_id
                    or type(file.get('index_generation')) is not int or file['index_generation'] != generation
                    or type(file.get('source_digest')) is not str
                    or re.fullmatch('[0-9a-f]{64}', file['source_digest']) is None
                    or language is None or file.get('language') != language):
                return None
            scope_files.append(file)
        def unique(row):
            ident, key = row.get('id'), row.get('symbol_key')
            if type(ident) is not int or ident <= 0 or (key is not None and type(key) is not str):
                return False
            clause = 'id=?'; values = (project.project_id, ident)
            if key:
                clause += ' OR symbol_key=?'; values += (key,)
            # NULL event keys are not aliases of other NULL keys.
            aliases = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND ('+clause+') LIMIT 2', values)]
            return len(aliases) == 1 and same_fields(row, aliases[0], IDENTITY)
        symbols, recalled_files = {}, {}
        for item in pool:
            if item['kind'] == 'symbol':
                if not unique(item):
                    return None
                symbols[item['id']] = next(r for r in rows if r['id'] == item['id'])
            else:
                if type(item.get('id')) is not int or item['id'] <= 0:
                    return None
                matches = [r for r in files if r['id'] == item['id'] or r['file_path'] == item['file_path']]
                if len(matches) != 1 or not same_fields(item, matches[0], FILE_FIELDS):
                    return None
                recalled_files[item['file_path']] = matches[0]
        # Inventory EVERY top-level matching name, including unsupported declaration kinds.
        wanted = {(r['file_path'], r['symbol']) for r in rows
                  if not r.get('owner_name') and (r.get('qualified_name') == r.get('symbol')
                      or r.get('symbol_type') in {'component', 'struct', 'class', 'interface', 'function', 'method', 'type', 'enum'})
                  and qualifier_matches(qualifier, r.get('symbol'))}
        wanted.update((r['file_path'], r['owner_name']) for r in symbols.values()
                      if r.get('owner_name') and qualifier_matches(qualifier, r['owner_name']))
        if not wanted or len(wanted) > 12:
            return None
        metadata = snapshot(dict(projects=projects, states=states, rows=rows, files=files, scope_files=scope_files))
        frames = []
        for path, name in sorted(wanted):
            owners = [r for r in rows if r['file_path'] == path and r['symbol'] == name and not r.get('owner_name')]
            if len(owners) != 1:
                return None
            owner = owners[0]; file = recalled_files.get(path)
            if (file is None or owner['id'] not in symbols or not valid_row(owner, project)
                    or not unique(owner) or owner['symbol_type'] not in {'component', 'struct'}
                    or owner.get('owner_kind') != 'component' or owner['qualified_name'] != name
                    or type(file.get('index_generation')) is not int or file['index_generation'] != generation
                    or file.get('language') != 'ArkTS' or Path(path).suffix != '.ets'):
                return None
            builds = [r for r in rows if r['file_path'] == path and r.get('owner_name') == name and r['symbol'] == 'build']
            if len(builds) != 1:
                return None
            build = builds[0]
            if (build['id'] not in symbols or not valid_row(build, project) or not unique(build)
                    or build['owner_kind'] != 'component' or build['qualified_name'] != name+'.build'
                    or build['symbol_type'] not in {'function', 'method'} or build['signature'] != 'build():unknown'):
                return None
            # Extra members are an immutable validation inventory, not added serving roots.
            # Their finite syntax/unknown status is decided by the complete source parser.
            members = [owner] + [r for r in rows if r['file_path'] == path
                and (r.get('owner_name') == name
                     or str(r.get('qualified_name') or '').startswith(name+'.'))]
            # Legacy STATE rows have a qualified member identity but empty owner_name.
            # Include their metadata/ranges, never promote them to serving roots.
            for row in members:
                if (row.get('owner_name') not in ('', None, name)
                        or not unique(row) or row.get('source_digest') != file['source_digest']
                        or type(row.get('index_generation')) is not int or row['index_generation'] != generation
                        or type(row.get('start_line')) is not int or type(row.get('end_line')) is not int
                        or not owner['start_line'] <= row['start_line'] <= row['end_line'] <= owner['end_line']):
                    return None
            frames.append(dict(path=path, owner=owner, build=build, file=file, members=members,
                               state=states[0], pool_paths=tuple(sorted(paths)), scope_files=scope_files, metadata=metadata))
        return frames
