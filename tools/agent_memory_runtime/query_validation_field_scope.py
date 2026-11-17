# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Complete bounded validation source view; DB witnesses never add roots."""
from copy import deepcopy
import hashlib
from pathlib import Path
from .storage import connect
from .query_command_table_scope import IDENTITY, FILE_FIELDS, same_fields
from .query_output_loop_selection import valid_row, snapshot


def validation_field_scope(project, permission, pool):
    from .validation_field_source import parse_validation_field_file
    from .query_validation_field_request import validation_field_matches
    if type(pool) is not list or not pool or any(type(r) is not dict for r in pool):
        return None
    paths = set()
    for item in pool:
        path = item.get('file_path')
        if (item.get('kind') not in {'symbol', 'file'} or not isinstance(path, str)
                or not path or Path(path).is_absolute() or '..' in Path(path).parts
                or Path(path).as_posix() != path):
            return None
        paths.add(path)
    if len(paths) > 12:
        return None
    root = Path(project.root).resolve()
    with connect(project) as db:
        # SQLite implicit transactions start on writes, not these SELECTs.
        db.execute('BEGIN')
        args = (project.project_id, *sorted(paths))
        marks = ','.join('?' for _ in paths)
        rows = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ('+marks+') ORDER BY id', args)]
        files = [dict(r) for r in db.execute('SELECT * FROM code_files WHERE project_id=? AND file_path IN ('+marks+') ORDER BY id', args)]
        states = [dict(r) for r in db.execute('SELECT * FROM code_index_state WHERE project_id=?', (project.project_id,))]
        if (len(states) != 1 or type(states[0].get('generation')) is not int
                or states[0]['generation'] <= 0 or states[0].get('status') != 'active'):
            return None
        generation = states[0]['generation']
        def unique(row):
            aliases = [dict(r) for r in db.execute(
                'SELECT * FROM code_symbols WHERE project_id=? AND (id=? OR symbol_key=?) LIMIT 2',
                (project.project_id, row.get('id'), row.get('symbol_key')))]
            return len(aliases) == 1 and same_fields(row, aliases[0], IDENTITY)
        verified = {}
        for item in pool:
            if item['kind'] == 'file':
                found = [r for r in files if r['id'] == item.get('id') or r['file_path'] == item['file_path']]
                if len(found) != 1 or not same_fields(item, found[0], FILE_FIELDS):
                    return None
            else:
                if not valid_row(item, project) or not unique(item):
                    return None
                if item['id'] in verified and not same_fields(item, verified[item['id']], IDENTITY):
                    return None
                verified[item['id']] = deepcopy(item)
        anchors, members, sources = [], [], []
        for path in sorted(paths):
            actual = (root/path).resolve()
            if not actual.is_relative_to(root) or actual.suffix not in {'.ts', '.ets'}:
                return None
            with actual.open('rb') as stream:
                raw = stream.read(2*1024*1024+1)
            if len(raw) > 2*1024*1024:
                return None
            source = raw.decode('utf-8'); digest = hashlib.sha256(raw).hexdigest()
            metadata = [r for r in files if r['file_path'] == path]
            if (len(metadata) != 1 or metadata[0]['source_digest'] != digest
                    or type(metadata[0]['index_generation']) is not int
                    or metadata[0]['index_generation'] != generation):
                return None
            sources.append((path, digest))
            local = [r for r in rows if r['file_path'] == path]
            for r in verified.values():
                if r['file_path'] == path and (r['source_digest'] != digest or r['index_generation'] != generation):
                    return None
            proof = parse_validation_field_file(source)
            # Unknown anywhere in original scope cannot certify absence or shrink positives.
            if type(proof) is not list:
                return None
            for fact in proof:
                if not validation_field_matches(permission, fact['owner'], fact['method'], fact['field']):
                    continue
                owners = [r for r in local if r['symbol'] == fact['owner'] and not r.get('owner_name')
                          and r['symbol_type'] in {'class', 'struct', 'component'}]
                if len(owners) != 1:
                    return None
                owner = owners[0]
                kind = fact['kind']
                expected = 'component' if kind in {'struct', 'component'} else 'class'
                if (kind not in {'class', 'struct', 'component'} or not valid_row(owner, project)
                        or not unique(owner) or owner['qualified_name'] != fact['owner']
                        or owner['owner_kind'] != expected
                        or (owner['start_line'], owner['end_line']) != (fact['owner_start'], fact['owner_end'])):
                    return None
                candidates = [r for r in verified.values() if r['file_path'] == path
                              and r.get('owner_name') == fact['owner'] and r['symbol'] == fact['method']]
                if len(candidates) != 1:
                    return None
                method = candidates[0]
                lo, hi = fact['start_line'], fact['end_line']
                if (method['symbol_type'] not in {'function', 'method'} or method['owner_kind'] != expected
                        or method['qualified_name'] != fact['owner']+'.'+fact['method']
                        or (method['start_line'], method['end_line']) != (lo, hi)
                        or not owner['start_line'] <= lo <= hi <= owner['end_line']
                        or hi > len(source.splitlines())):
                    return None
                for r in (owner, method):
                    if r['source_digest'] != digest or r['index_generation'] != generation:
                        return None
                span = dict(symbol=method['symbol'], start_line=lo, end_line=hi)
                anchors.append(dict(file_path=path, symbol=method['symbol'], symbol_type=method['symbol_type'],
                    record_ids=[method['id']], record_type='code_symbol', source_ranges=[span],
                    read_window=dict(start_line=lo, end_line=hi), role='supporting', source_excerpts=[dict(span,
                        content='\n'.join(source.splitlines()[lo-1:hi]), truncated=False, source='validated_request_snapshot')]))
                members.append(method)
        if not 0 < len(members) <= 3 or len({r['id'] for r in members}) != len(members):
            return None
        return anchors, members, tuple(sources), snapshot(dict(rows=rows, files=files, states=states))
