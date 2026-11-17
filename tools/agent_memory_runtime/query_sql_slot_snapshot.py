"""Authenticate a complete bounded admitted source scope; never create roots."""
from copy import deepcopy
import hashlib
import sqlite3
from pathlib import Path, PurePosixPath
from .storage import connect
from .query_output_loop_selection import valid_row, snapshot

SYMBOL_FIELDS = ('id', 'project_id', 'file_path', 'symbol', 'symbol_key', 'qualified_name',
                 'start_line', 'end_line', 'source_digest', 'index_generation',
                 'owner_name', 'owner_kind', 'semantic_adapter', 'evidence_class', 'symbol_type')
FILE_FIELDS = ('id', 'project_id', 'file_path', 'language', 'source_digest', 'index_generation')
MAX_SOURCE = 2 * 1024 * 1024


def project_rows(project, paths):
    marks = ','.join('?' for _ in paths)
    args = (project.project_id, *paths)
    with connect(project) as conn:
        files = [dict(r) for r in conn.execute(
            f'SELECT * FROM code_files WHERE project_id=? AND file_path IN ({marks})', args)]
        rows = [dict(r) for r in conn.execute(
            f'SELECT * FROM code_symbols WHERE project_id=? AND (file_path IN ({marks}) '
            f'OR symbol_key IN (SELECT symbol_key FROM code_symbols WHERE project_id=? AND file_path IN ({marks})))',
            (*args, *args))]
    return files, rows


def identities(files, rows):
    return snapshot({
        'files': sorted(({k: r.get(k) for k in FILE_FIELDS} for r in files), key=lambda r: r['id']),
        'symbols': sorted(({k: r.get(k) for k in SYMBOL_FIELDS} for r in rows), key=lambda r: r['id']),
    })


def source_bytes(root, name):
    path = PurePosixPath(name)
    if (path.is_absolute() or '..' in path.parts or str(path) != name
            or path.suffix != '.ets'):
        raise ValueError('unsupported_source_path')
    resolved = (root / name).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError('source_path_escape')
    with resolved.open('rb') as stream:
        raw = stream.read(MAX_SOURCE + 1)
    if len(raw) > MAX_SOURCE:
        raise ValueError('source_size')
    return raw


def load_scope(project, pool):
    """All pool paths, including outside-slot declarations, authenticated together."""
    try:
        if type(pool) is not list or not pool or any(type(r) is not dict for r in pool):
            return None
        if any(r.get('kind') not in {'file', 'symbol'} for r in pool):
            return None
        paths = sorted({r.get('file_path') for r in pool})
        if not paths or len(paths) > 12 or any(type(p) is not str or not p for p in paths):
            return None
        root = Path(project.root).resolve()
        files, rows = project_rows(project, paths)
        if any(not valid_row(r, project) for r in rows):
            return None
        # IDs and keys are unique within their typed namespace, not across tables.
        if (len({r['id'] for r in rows}) != len(rows)
                or len({r['symbol_key'] for r in rows}) != len(rows)
                or len({r['id'] for r in files}) != len(files)):
            return None
        sources, digests = {}, {}
        for name in paths:
            found = [r for r in files if r['file_path'] == name]
            if len(found) != 1:
                return None
            file = found[0]
            if (type(file.get('id')) is not int or file['id'] <= 0
                    or file.get('project_id') != project.project_id
                    or type(file.get('index_generation')) is not int or file['index_generation'] <= 0):
                return None
            raw = source_bytes(root, name)
            digest = hashlib.sha256(raw).hexdigest()
            if file.get('source_digest') != digest:
                return None
            sources[name], digests[name] = raw.decode('utf-8'), digest
            local = [r for r in rows if r['file_path'] == name]
            if (not local or any(r['source_digest'] != digest or
                    r['index_generation'] != file['index_generation'] for r in local)
                    or len({r['semantic_adapter'] for r in local}) != 1):
                return None
        for recalled in pool:
            table, fields = (files, FILE_FIELDS) if recalled['kind'] == 'file' else (rows, SYMBOL_FIELDS)
            aliases = [r for r in table if r['id'] == recalled.get('id') or
                       (recalled['kind'] == 'symbol' and r['symbol_key'] == recalled.get('symbol_key'))]
            if len(aliases) != 1 or any(recalled.get(k) != aliases[0].get(k) for k in fields):
                return None
        return dict(root=root, project=project, paths=paths, sources=sources, digests=digests,
                    files=files, rows=rows, pool=deepcopy(pool), identity=identities(files, rows))
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, sqlite3.Error):
        return None


def current_scope(scope):
    """Recheck every source and DB identity, not just selected output sources."""
    try:
        project = scope['project']
        if Path(project.root).resolve() != scope['root']:
            return False
        for name, digest in scope['digests'].items():
            if hashlib.sha256(source_bytes(scope['root'], name)).hexdigest() != digest:
                return False
        files, rows = project_rows(project, scope['paths'])
        return identities(files, rows) == scope['identity']
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, sqlite3.Error):
        return False


def owner_row(scope, path, declaration):
    name = declaration['name']
    found = [r for r in scope['rows'] if r['file_path'] == path and r['symbol'] == name
             and r['qualified_name'] == name and r['symbol_type'] in {'class', 'component'}]
    if len(found) != 1:
        return None
    row = found[0]
    if (row['owner_name'] not in ('', None) or not row['owner_kind']
            or (row['start_line'], row['end_line']) !=
            (declaration['span']['start_line'], declaration['span']['end_line'])):
        return None
    return row


def method_root(scope, path, owner, declaration):
    """Return an original admitted method only, never an invented DB root."""
    found = [r for r in scope['rows'] if r['file_path'] == path
             and r['symbol'] == declaration['name']
             and r['qualified_name'] == owner['symbol'] + '.' + declaration['name']
             and r['owner_name'] == owner['symbol'] and r['owner_kind'] == owner['owner_kind']
             and r['symbol_type'] in {'method', 'function'}
             and (r['start_line'], r['end_line']) ==
             (declaration['span']['start_line'], declaration['span']['end_line'])]
    if len(found) != 1:
        return None
    row = found[0]
    recalled = [r for r in scope['pool'] if r['kind'] == 'symbol' and r['id'] == row['id']]
    if not recalled or any(any(r.get(k) != row.get(k) for k in SYMBOL_FIELDS) for r in recalled):
        return None
    return deepcopy(recalled[0])
