# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""One terminal source/DB authentication round, not collection or route authority."""
import re
import sqlite3
from pathlib import Path
from contextlib import closing
from .semantic_models import symbol_key
from .query_recovery_pair import recovery_request
from .query_recovery_source import parse_recovery_source, lex, KEYWORDS
from .query_output_loop_selection import valid_row
from .query_validation_log_capture import bounded_metadata
from .query_touch_log_provenance import visible
from .query_recovery_append_db import Round, FILE, SYMBOL, LOG, same, path_ok


def positive(v):
    return type(v) is int and v > 0


def file_row(r, path, generation):
    row = r.one('code_files', 'project_id=? AND file_path=?', (r.project.project_id, path))
    if (not positive(row['id']) or row['index_generation'] != generation
            or row['language'] != 'ArkTS' or not path.endswith('.ets')
            or re.fullmatch('[0-9a-f]{64}', str(row['source_digest'] or '')) is None):
        raise ValueError('file identity')
    alias = r.one('code_files', 'project_id=? AND (id=? OR file_path=?)',
                  (r.project.project_id, row['id'], path))
    if alias != row:
        raise ValueError('file alias')
    return row


def symbol_row(r, path, qualified, generation, file):
    row = r.one('code_symbols', 'project_id=? AND file_path=? AND qualified_name=?',
                (r.project.project_id, path, qualified))
    if (not valid_row(row, r.project) or row['index_generation'] != generation
            or row['source_digest'] != file['source_digest']
            or str(row['semantic_adapter']).partition('@')[0] != 'arkts-static'
            or type(row['signature']) is not str or not row['signature']
            or row['symbol_key'] != symbol_key('ArkTS', path, qualified, row['signature'])):
        raise ValueError('symbol identity')
    alias = r.one('code_symbols', 'project_id=? AND (id=? OR symbol_key=?)',
                  (r.project.project_id, row['id'], row['symbol_key']))
    if alias != row:
        raise ValueError('symbol alias')
    return row


def pool_current(r, pool, generation):
    for item in pool:
        path = item['file_path']; file = file_row(r, path, generation)
        if item['kind'] == 'file':
            if not same(item, file, FILE):
                raise ValueError('original file changed')
        elif item['kind'] == 'symbol':
            row = symbol_row(r, path, item['qualified_name'], generation, file)
            if not same(item, row, SYMBOL):
                raise ValueError('original symbol changed')
        else:
            raise ValueError('pool kind')


def class_proof(r, anchor, pool, generation):
    path = anchor['file_path']; name = anchor['symbol']
    file = file_row(r, path, generation)
    owner = symbol_row(r, path, name, generation, file)
    if (owner['symbol_type'] != 'class' or owner['symbol'] != name
            or owner['signature'] != 'class '+name
            or owner['owner_name'] not in ('', None)
            or (anchor.get('start_line'), anchor.get('end_line'))
               != (owner['start_line'], owner['end_line'])):
        raise ValueError('class range')
    kind = {'code_file': 'file', 'code_symbol': 'symbol'}.get(anchor.get('record_type'))
    original = [x for x in pool if x['kind'] == kind and x['id'] == anchor.get('record_id')
                and x['file_path'] == path]
    if len(original) != 1:
        raise ValueError('root absent from original pool')
    expected = file if kind == 'file' else owner
    if anchor.get('record_id') != expected['id']:
        raise ValueError('unserved class identity')
    source = r.read(path, file['source_digest'])
    parsed = parse_recovery_source(source)
    if (not parsed or not r.bounded(parsed)
            or (parsed['owner'], parsed['class_start'], parsed['class_end'])
               != (name, owner['start_line'], owner['end_line'])):
        raise ValueError('unknown whole candidate')
    members = []
    for method in parsed['methods']:
        row = symbol_row(r, path, name+'.'+method['name'], generation, file)
        if (row['symbol_type'] not in ('function', 'method') or row['symbol'] != method['name']
                or row['owner_name'] != name or row['owner_kind'] != owner['owner_kind']
                or (row['start_line'], row['end_line']) != (method['start_line'], method['end_line'])
                or row['semantic_adapter'] != owner['semantic_adapter']):
            raise ValueError('method identity')
        expected = (method['name']+'('+method['parameter']+':boolean):void'
                    if method['kind'] == 'registry' else 'async'+method['name']+'():Promise<void>')
        if re.sub(r'\s+', '', row['signature']) != expected:
            raise ValueError('method signature')
        members.append(row)
    for field in parsed['fields']:
        if field['kind'] == 'state':
            row = symbol_row(r, path, name+'.'+field['name'], generation, file)
            if (row['symbol_type'] != 'state' or row['symbol'] != field['name']
                    or row['signature'] != field['name']
                    or row['semantic_adapter'] != owner['semantic_adapter']
                    or (row['start_line'], row['end_line']) != (field['start_line'], field['end_line'])):
                raise ValueError('state identity')
            members.append(row)
    start, end = owner['start_line'], owner['end_line']
    lines = source.splitlines()
    if not 1 <= start <= end <= len(lines) or end-start+1 > 40:
        raise ValueError('class excerpt lines')
    text = '\n'.join(lines[start-1:end])
    if len(text) > 1500:
        raise ValueError('class excerpt chars')
    for excerpt in anchor.get('source_excerpts', []):
        lo, hi = excerpt.get('start_line'), excerpt.get('end_line')
        if (not positive(lo) or not positive(hi) or not start <= lo <= hi <= end
                or excerpt.get('content') != '\n'.join(lines[lo-1:hi])):
            raise ValueError('raw excerpt differs')
    if anchor.get('source_excerpt') is not None:
        raise ValueError('unsupported legacy raw excerpt')
    proof = dict(anchor=anchor, roles=parsed['roles'], owner=owner, members=members,
                 excerpt=dict(symbol=name, start_line=start, end_line=end, content=text,
                              source='validated_request_snapshot',
                              selection_reason='existing_recovery_role_range',
                              focus_line=None, truncated=False))
    if not r.bounded(proof):
        raise ValueError('class certificate budget')
    return proof


def literal_file(source):
    """Closed direct console-only class. No imports, fields, params or aliases.

    Reuses the existing comment/string lexer; keyword/token kinds are checked.
    Dynamic/template arguments and source-text-only substring proofs decline.
    """
    tokens = lex(source); at = 0
    def take(value=None, kind=None):
        nonlocal at
        token = tokens[at]
        if ((value is not None and (token.value != value or token.kind == 'string'))
                or (kind is not None and token.kind != kind)):
            raise ValueError('direct source grammar')
        at += 1
        return token
    def name():
        token = take(kind='ident')
        if token.value in KEYWORDS or token.value == 'console':
            raise ValueError('direct shadowing')
        return token
    first = tokens[at]
    if tokens[at].value == 'export' and tokens[at].kind == 'ident':
        take('export', 'ident')
    take('class', 'ident'); owner = name().value; take('{')
    methods = []; names = set(); calls = []
    while tokens[at].value != '}':
        begin = name(); method = begin.value
        if method in names or len(names) >= 16:
            raise ValueError('duplicate/many methods')
        names.add(method)
        for value in ('(', ')', ':'):
            take(value)
        take('void', 'ident'); take('{')
        while tokens[at].value != '}':
            start = take('console', 'ident'); take('.')
            level = take(kind='ident')
            if level.value not in ('info', 'warn', 'error', 'log', 'debug'):
                raise ValueError('console level')
            take('('); message = take(kind='string'); end = take(')')
            if start.line != message.line or start.line != end.line or not message.value:
                raise ValueError('physical direct literal')
            statement = source[start.start:end.end]
            if tokens[at].value == ';':
                take(';')
            elif tokens[at].value != '}' and tokens[at].line <= end.line:
                raise ValueError('statement separator')
            calls.append(dict(function=method, line=start.line, logger='console',
                              level=level.value, message_template=message.value,
                              statement=statement))
            if len(calls) > 64:
                raise ValueError('direct call cap')
        finish = take('}')
        methods.append(dict(name=method, start=begin.line, end=finish.line))
    last = take('}'); take(kind='eof')
    if not calls:
        raise ValueError('no literal calls')
    return dict(owner=owner, start=first.line, end=last.line, methods=methods, calls=calls)


def log_proofs(r, inventory, raw_logs, generation):
    proved = []; by_id = {}; parsed_files = {}
    r.parts.extend([proved, parsed_files])
    for supplied in inventory['direct']:
        if type(supplied) is not dict or not positive(supplied.get('id')) or supplied['id'] in by_id:
            raise ValueError('direct inventory identity')
        row = r.one('code_log_statements', 'project_id=? AND id=?',
                    (r.project.project_id, supplied['id']))
        if not same(supplied, row, LOG):
            raise ValueError('direct changed')
        path = row['file_path']; file = file_row(r, path, generation)
        if row['index_generation'] != generation or row['source_digest'] != file['source_digest']:
            raise ValueError('direct generation')
        source = r.read(path, file['source_digest'])
        if path not in parsed_files:
            parsed = literal_file(source)
            if not r.bounded(parsed):
                raise ValueError('aggregate parsed logs')
            parsed_files[path] = parsed
        parsed = parsed_files[path]
        if not r.bounded(parsed):
            raise ValueError('literal certificate budget')
        owner = symbol_row(r, path, parsed['owner'], generation, file)
        if (owner['symbol_type'] != 'class' or owner['symbol'] != parsed['owner']
                or owner['signature'] != 'class '+parsed['owner'] or owner['owner_name'] not in ('', None)
                or (owner['start_line'], owner['end_line']) != (parsed['start'], parsed['end'])):
            raise ValueError('logger owner')
        method = r.one('code_symbols', 'project_id=? AND file_path=? AND qualified_name=?',
                       (r.project.project_id, path, parsed['owner']+'.'+row['function']))
        method = symbol_row(r, path, method['qualified_name'], generation, file)
        actual = [m for m in parsed['methods'] if m['name'] == row['function']]
        if (len(actual) != 1 or method['symbol_type'] not in ('function', 'method')
                or method['owner_name'] != parsed['owner'] or method['symbol'] != row['function']
                or method['owner_kind'] != owner['owner_kind']
                or re.sub(r'\s+', '', method['signature']) != row['function']+'():void'
                or method['semantic_adapter'] != owner['semantic_adapter']
                or (method['start_line'], method['end_line']) != (actual[0]['start'], actual[0]['end'])):
            raise ValueError('logger method')
        matches = [c for c in parsed['calls'] if all(c[k] == row[k]
                   for k in ('function','line','logger','level','message_template'))]
        if len(matches) != 1 or row['raw_statement'].strip().rstrip(';') != matches[0]['statement']:
            raise ValueError('literal statement proof')
        item = dict(row=row, owner=owner, method=method)
        if not r.bounded([proved, item]):
            raise ValueError('log certificate budget')
        proved.append(item); by_id[row['id']] = item
    seen = set()
    for log in raw_logs:
        ident = log.get('log_id') if type(log) is dict else None
        if not positive(ident) or ident not in by_id or ident in seen:
            raise ValueError('raw direct projection')
        visible(log, by_id[ident], False); seen.add(ident)
    return proved


def authenticate(project, query, raw, pool, inventory, *, budget_context=None):
    """Caller supplies authentic live capture; this function grants no issuance.

    budget_context must include complete matches/audit and caller certificate
    parts so each DB/source-proof allocation is charged jointly, not afterwards.
    """
    try:
        if (budget_context is None or type(raw) is not dict or type(pool) is not list
                or type(inventory) is not dict or set(inventory) != {'direct','effects'}
                or not recovery_request(query) or raw.get('query') != query
                or raw.get('project_id') != project.project_id
                or type(raw.get('project_path')) is not str
                or Path(raw['project_path']).resolve() != Path(project.root).resolve()
                or type(inventory['direct']) is not list or not 0 < len(inventory['direct']) <= 64
                or inventory['effects'] != [] or not bounded_metadata([raw,pool,inventory,budget_context])):
            return None
        if not pool or any(type(x) is not dict or not path_ok(x.get('file_path')) for x in pool):
            return None
        paths = sorted({x['file_path'] for x in pool})
        if len(paths) > 12:
            return None
        anchors = raw['query_handoff']['code_anchors']
        if type(anchors) is not list or any(type(a) is not dict for a in anchors):
            return None
        roots = [a for a in anchors if a.get('symbol_type') == 'class']
        if not 0 < len(roots) <= 3 or len({a.get('file_path') for a in roots}) != len(roots):
            return None
        if any(a.get('file_path') not in paths for a in roots):
            return None
        logs = raw['query_handoff']['log_anchors']
        if type(logs) is not list:
            return None
        uri = Path(project.db_path).resolve().as_uri() + '?mode=ro'
        with closing(sqlite3.connect(uri, uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN')
            r = Round(db, project, paths, [raw,pool,inventory,budget_context])
            index = r.one('code_index_state', 'project_id=?', (project.project_id,))
            if (index['status'] != 'active' or not positive(index['generation'])
                    or index['extractor_version'] != 'code-derived:v1'
                    or type(index['source_revision']) is not str or not index['source_revision']):
                return None
            generation = index['generation']; pool_current(r, pool, generation)
            candidates = []
            r.parts.append(candidates)
            for anchor in roots:
                proof = class_proof(r, anchor, pool, generation)
                if not r.bounded([candidates, proof]):
                    return None
                candidates.append(proof)
            if not {'registry','store'} <= {role for p in candidates for role in p['roles']}:
                return None
            direct = log_proofs(r, inventory, logs, generation)
            proof = dict(roots=candidates, logs=direct, index=index, rows=r.rows,
                         files=[dict(file_path=p, source_digest=v['digest']) for p,v in sorted(r.sources.items())],
                         read_stats=dict(reads=r.source_reads, bytes=r.source_bytes))
            return proof if bounded_metadata([raw,pool,inventory,budget_context,proof]) else None
    except (AttributeError,KeyError,TypeError,ValueError,IndexError,OSError,UnicodeError,
            sqlite3.Error,OverflowError,RecursionError):
        return None
