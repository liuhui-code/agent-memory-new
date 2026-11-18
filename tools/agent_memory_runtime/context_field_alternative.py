# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Add authenticated existing alternative bodies; no ranking or unique-view authority."""
from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import re
import sqlite3
from time import monotonic
from .storage import connect
from .query_output_loop_selection import valid_row
from .query_validation_field_request import validation_field_request, FIELDS, parts
from .validation_field_source import Parser, Unknown
from .context_budget import synchronize_estimate
from .performance_scoring import estimate_payload_tokens

RELATION = re.compile(r'请定位(?P<field>显示名|客户编号)为空时提示错误并中止(?P<qualifier>[\u4e00-\u9fff]{2,16})的校验和分发源码。')
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_SECONDS = 2.0

OPERATORS = ('不','非','无','没','勿','只','仅','除','而','比','或','和','另','也','并','日志','显示名','客户编号')



class _GuardedCallParser(Parser):
    """Weaker display-only relation. Never supplied to existing validation views."""
    def validate_dispatch_target(self, target):
        pass


def guarded_calls(source):
    try:
        parser = _GuardedCallParser(source)
        # Target spelling is intentionally not an action/dispatch classifier.
        return [dict(owner=f['owner'], owner_start=f['owner_start'], owner_end=f['owner_end'],
                     kind=f['kind'], method=f['method'], start_line=f['start_line'], end_line=f['end_line'],
                     field=f['field'], root=f['root'], call_argument=f['dispatch_argument'])
                for f in parser.parse() if f['dispatch_argument'] == 'scalar']
    except (Unknown, IndexError, KeyError, UnicodeError, RecursionError):
        return None


def field_read_request(query):
    """Partial field evidence permission, intentionally unusable by old view consumers."""
    if type(query) is not str:
        return None
    permission = validation_field_request(query)
    if permission and permission['kind'] == 'field':
        return {'field_parts': permission['value'], 'unverified_action': None}
    match = RELATION.fullmatch(query)
    if not match or any(word in match['qualifier'] for word in OPERATORS):
        return None
    return {'field_parts': FIELDS[match['field']], 'unverified_action': match['qualifier']}


def append_field_alternatives(project, original, payload):
    """Any unsupported identity, resource failure or all-positive overflow is exact no-op."""
    try:
        return _append(project, original, payload)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError, sqlite3.Error):
        return payload


def _append(project, original, payload):
    permission = field_read_request(payload.get('query'))
    if not permission or original.get('query') != payload['query']:
        return payload
    if original.get('project_id') != project.project_id or payload.get('project_id') != project.project_id:
        return payload
    freshness = payload.get('source_freshness', {})
    if (freshness.get('status') != 'current' or original.get('source_freshness', {}).get('status') != 'current'
        or original.get('source_freshness', {}).get('generation') != freshness.get('generation')):
        return payload
    h = payload['query_handoff']; raw = original['query_handoff']
    alternatives = (h.get('callable_evidence') or {}).get('alternatives', [])
    originals = (raw.get('callable_evidence') or {}).get('alternatives', [])
    if type(alternatives) is not list or not 0 < len(alternatives) <= 8 or type(originals) is not list:
        return payload
    anchors = h.get('code_anchors'); raw_anchors = raw.get('code_anchors')
    if type(anchors) is not list or type(raw_anchors) is not list:
        return payload
    root = Path(project.root).resolve(); generation = freshness.get('generation')
    if type(generation) is not int or generation <= 0 or Path(original.get('project_path', '')).resolve() != root:
        return payload
    started = monotonic(); total_bytes = 0
    additions, captured, seen = [], {}, set()
    with connect(project) as db:
        db.execute('BEGIN')
        db.set_progress_handler(lambda: int(monotonic()-started > MAX_SECONDS), 1000)
        state = [dict(r) for r in db.execute('SELECT * FROM code_index_state WHERE project_id=?', (project.project_id,))]
        if len(state) != 1 or state[0].get('generation') != generation or state[0].get('status') != 'active':
            return payload
        for candidate in alternatives:
            bounds = candidate.get('source_range', {})
            if bounds.get('selection_reason') != 'callable_symbol_range':
                return payload
            path, name, owner = candidate.get('file_path'), candidate.get('symbol'), candidate.get('owner_name')
            lo, hi = bounds.get('start_line'), bounds.get('end_line')
            if (not all(type(v) is str and v for v in (path, name, owner))
                or type(lo) is not int or type(hi) is not int or not 0 < lo <= hi or hi-lo+1 > 40):
                return payload
            identity = (path, name, owner, lo, hi)
            if identity in seen:
                return payload
            seen.add(identity)
            original_matches = [c for c in originals if (c.get('file_path'), c.get('symbol'), c.get('owner_name'),
                (c.get('source_range') or {}).get('start_line'), (c.get('source_range') or {}).get('end_line')) == identity]
            if len(original_matches) != 1 or original_matches[0].get('source_range') != bounds:
                return payload
            matches = [a for a in raw_anchors if a.get('file_path') == path and a.get('symbol') == name
                       and a.get('record_type') == 'code_symbol' and a.get('start_line') == lo and a.get('end_line') == hi]
            if len(matches) != 1:
                return payload
            a = matches[0]; rid = a.get('record_id')
            if (type(rid) is not int or a.get('symbol_type') not in {'method', 'function'}
                or a.get('source') != 'wiki' or a.get('graph_neighbor') is not False or a.get('graph_relation') is not None):
                return payload
            p = PurePosixPath(path); file = (root/path).resolve()
            if p.is_absolute() or '..' in p.parts or str(p) != path or not file.is_relative_to(root) or p.suffix not in {'.ts', '.ets'}:
                return payload
            if path not in captured:
                with file.open('rb') as stream:
                    source = stream.read(MAX_FILE_BYTES+1)
                total_bytes += len(source)
                if len(source) > MAX_FILE_BYTES or total_bytes > MAX_TOTAL_BYTES or b'\0' in source or monotonic()-started > MAX_SECONDS:
                    return payload
                captured[path] = (file, source, hashlib.sha256(source).hexdigest())
            file, source, digest = captured[path]
            rows = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND id=?', (project.project_id, rid))]
            owners = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND qualified_name=? AND file_path=? LIMIT 2', (project.project_id, owner, path))]
            files = [dict(r) for r in db.execute('SELECT * FROM code_files WHERE project_id=? AND file_path=?', (project.project_id, path))]
            if len(rows) != 1 or len(owners) != 1 or len(files) != 1:
                return payload
            method, container = rows[0], owners[0]
            if (method['symbol_type'] != a['symbol_type'] or method['file_path'] != path
                or method['symbol'] != name or method['owner_name'] != owner or method['qualified_name'] != owner+'.'+name
                or (method['start_line'], method['end_line']) != (lo, hi)
                or container['symbol_type'] not in {'class', 'struct', 'component'} or container.get('owner_name')
                or container['symbol'] != owner or method['owner_kind'] != container['owner_kind']
                or candidate.get('owner_kind') != container['owner_kind']):
                return payload
            for row in (method, container):
                if (not valid_row(row, project) or row['source_digest'] != digest or row['index_generation'] != generation
                    or db.execute('SELECT COUNT(*) FROM code_symbols WHERE project_id=? AND symbol_key=?', (project.project_id,row['symbol_key'])).fetchone()[0] != 1):
                    return payload
            if files[0].get('source_digest') != digest or files[0].get('index_generation') != generation:
                return payload
            text = source.decode('utf-8'); facts = guarded_calls(text)
            if monotonic()-started > MAX_SECONDS:
                return payload
            if not isinstance(facts, list):
                continue
            facts = [f for f in facts if f['owner'] == owner and f['method'] == name and parts(f['field']) == permission['field_parts']]
            if not facts:
                continue
            if (len(facts) != 1 or container['owner_kind'] != ('component' if facts[0]['kind'] in {'struct','component'} else 'class')
                or (facts[0]['start_line'],facts[0]['end_line']) != (lo,hi)
                or (facts[0]['owner_start'],facts[0]['owner_end']) != (container['start_line'],container['end_line'])):
                return payload
            lines = text.splitlines(); content = '\n'.join(lines[lo-1:hi])
            if hi > len(lines) or len(content) > 1500:
                return payload
            if any(covered(e, lines, lo, hi) for old in anchors if old.get('file_path') == path for e in old.get('source_excerpts', [])):
                continue
            # Full current identity stays an alternative. No call or business result is inferred.
            additions.append(dict(source='wiki', record_type='code_symbol', record_ids=[rid], file_path=path,
                symbol=name, symbol_type=method['symbol_type'], role='alternative',
                source_ranges=[dict(symbol=name,start_line=lo,end_line=hi)], read_window=dict(start_line=lo,end_line=hi),
                display_basis=dict(kind='partial_static_guarded_field_call',field=facts[0]['field'],domain_unverified=True,action_unverified=True,
                                   unverified_action=permission['unverified_action']),
                source_excerpts=[dict(symbol=name,start_line=lo,end_line=hi,content=content,source='current_worktree',
                    selection_reason='existing_alternative_field_body',focus_line=None,truncated=False)]))
        for file, source, digest in captured.values():
            with file.open('rb') as stream:
                current = stream.read(MAX_FILE_BYTES+1)
            if hashlib.sha256(current).hexdigest() != digest or monotonic()-started > MAX_SECONDS:
                return payload
    if not additions:
        return payload
    trial = deepcopy(payload)
    trial['query_handoff']['code_anchors'].extend(additions)
    excerpts = [e for a in trial['query_handoff']['code_anchors'] for e in a.get('source_excerpts', [])]
    chars = sum(len(e['content']) for e in excerpts)
    if chars > 2600:
        return payload
    trial['query_handoff']['source_excerpt_policy'].update(excerpt_chars=chars,excerpt_count=len(excerpts))
    synchronize_estimate(trial)
    return trial if estimate_payload_tokens(trial) <= payload['output_budget']['target_tokens'] else payload


def covered(excerpt, lines, lo, hi):
    start,end = excerpt.get('start_line'),excerpt.get('end_line')
    return (type(start) is int and type(end) is int and 0 < start <= lo <= hi <= end <= len(lines)
            and excerpt.get('source') == 'current_worktree'
            and excerpt.get('content') == '\n'.join(lines[start-1:end]))
