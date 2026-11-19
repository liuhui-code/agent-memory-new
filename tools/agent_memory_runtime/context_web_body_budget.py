"""Budget a complete requested Web method without changing retrieval or evidence."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
from time import monotonic

from .context_budget import synchronize_estimate
from .context_source_excerpt import MAX_EXCERPT_CHARS, MAX_EXCERPT_LINES, MAX_TOTAL_EXCERPT_CHARS
from .context_source_recovery import MAX_VERIFY_SOURCE_BYTES
from .context_web_policy_reading import web_reading_request
from .performance_scoring import estimate_payload_tokens
from .query_output_loop_selection import valid_row
from .storage import connect
from .web_policy_reading_source import web_policy_inventory

_BODY_KEYS = {
    'symbol', 'source', 'selection_reason', 'start_line', 'end_line',
    'focus_line', 'truncated', 'content',
}
_WEB_MENTION = re.compile(r'\b(?:Web|fileAccess|onLoadIntercept)\b')


def prioritize_web_body(project, original, payload):
    """Transactional display change; return the exact prior response on any doubt."""
    if not web_reading_request(payload.get('query')):
        return payload
    try:
        return _trade(project, original, payload)
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, sqlite3.Error):
        return payload


def _one(conn, table, project_id, filter_sql, *values):
    rows = list(conn.execute(f'SELECT * FROM {table} WHERE project_id=? AND {filter_sql} LIMIT 2',
                             (project_id, *values)))
    if len(rows) != 1:
        raise ValueError('missing or ambiguous index identity')
    return dict(rows[0])


def _read_regular(path):
    # Nonblocking open avoids a replaced file turning an output operation into a FIFO wait.
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('not a regular source file')
        return stream.read(MAX_VERIFY_SOURCE_BYTES + 1)


def _verified_source(conn, project, root, path, generation):
    relative = PurePosixPath(path)
    source = (root / relative).resolve(strict=True)
    if (relative.is_absolute() or '..' in relative.parts or relative.as_posix() != path
            or relative.suffix != '.ets' or not source.is_relative_to(root)):
        raise ValueError('unsupported source path')
    data = _read_regular(source)
    digest = hashlib.sha256(data).hexdigest()
    indexed = _one(conn, 'code_files', project.project_id, 'file_path=?', path)
    if (len(data) > MAX_VERIFY_SOURCE_BYTES or indexed['source_digest'] != digest
            or indexed['index_generation'] != generation):
        raise ValueError('stale or unbounded source')
    decoded = data.decode('utf-8')
    if re.search(r'[\x00\x0b\x0c\x1c-\x1e\x85\u2028\u2029]|\r(?!\n)', decoded):
        raise ValueError('unreliable physical lines')
    return source, data, digest, decoded


def _exact(text, bounds):
    lo, hi = bounds
    # The index and normal excerpt reader count LF and normalize CRLF to LF.
    lines = text.replace('\r\n', '\n').removesuffix('\n').split('\n')
    if (type(lo) is not int or type(hi) is not int
            or not 0 < lo <= hi <= len(lines) or hi - lo + 1 > MAX_EXCERPT_LINES):
        raise ValueError('unverified excerpt range')
    result = '\n'.join(lines[lo - 1:hi])
    if not result or len(result) > MAX_EXCERPT_CHARS:
        raise ValueError('unverified excerpt size')
    return result


def _range(anchor):
    span, = anchor['source_ranges']
    if span['symbol'] != anchor['symbol']:
        raise ValueError('symbol disagrees with range')
    bounds = span['start_line'], span['end_line']
    if anchor['read_window'] != dict(zip(('start_line', 'end_line'), bounds)):
        raise ValueError('unexpected source window')
    return bounds


def _excerpt(anchor, source, reason, truncated):
    excerpt, = anchor['source_excerpts']
    if (set(excerpt) != _BODY_KEYS or excerpt['selection_reason'] != reason
            or excerpt['source'] != 'current_worktree' or excerpt['focus_line'] is not None
            or excerpt['truncated'] is not truncated):
        raise ValueError('unexpected excerpt metadata')
    bounds = excerpt['start_line'], excerpt['end_line']
    if excerpt['content'] != _exact(source, bounds):
        raise ValueError('old excerpt is not exact current source')
    return excerpt, bounds


def _qualify_method(conn, project, row, anchor, bounds, digest, generation):
    if (not valid_row(row, project) or row['symbol_type'] not in {'method', 'function'}
            or not row.get('owner_name') or not row.get('owner_kind')
            or row['qualified_name'] != row['owner_name'] + '.' + row['symbol']
            or (row['file_path'], row['symbol'], row['start_line'], row['end_line'],
                row['source_digest'], row['index_generation']) !=
            (anchor['file_path'], anchor['symbol'], *bounds, digest, generation)
            or _one(conn, 'code_symbols', project.project_id, 'symbol_key=?', row['symbol_key']) != row):
        raise ValueError('typed symbol identity disagrees')


def _qualify_owner(conn, project, owner, method, bounds, digest, generation, kind):
    if (not valid_row(owner, project) or owner['symbol_type'] != kind
            or owner['symbol'] != method['owner_name'] or owner['owner_name'] not in (None, '')
            or owner['owner_kind'] != method['owner_kind'] or owner['source_digest'] != digest
            or owner['index_generation'] != generation
            or (owner['start_line'], owner['end_line']) != bounds
            or _one(conn, 'code_symbols', project.project_id, 'symbol_key=?', owner['symbol_key']) != owner):
        raise ValueError('typed owner identity disagrees')


def _match_anchors(anchors, original_anchors, path, method, target):
    matches = [(i, a) for i, a in enumerate(anchors) if a['file_path'] == path]
    (index, anchor), = matches
    expected_type = 'code_symbol' if target else 'code_log_effect'
    rid, = anchor['record_ids']
    if (type(rid) is not int or rid <= 0 or anchor['record_type'] != expected_type
            or anchor['symbol'] != method):
        raise ValueError('unexpected anchor identity')
    lo, hi = _range(anchor)
    (raw,) = [item for item in original_anchors if item.get('record_type') == expected_type
              and item.get('record_id') == rid]
    if (raw['file_path'], raw['symbol'], raw['start_line'], raw['end_line']) != (path, method, lo, hi):
        raise ValueError('original and apparent anchor disagree')
    if raw.get('identity_match') or raw.get('graph_neighbor'):
        raise ValueError('explicitly selected source evidence')
    if raw.get('source') != ('wiki' if target else 'wrapped_log_caller'):
        raise ValueError('unexpected original evidence kind')
    if not target and anchor.get('source') != 'wrapped_log_caller':
        raise ValueError('unexpected supporting source kind')
    return index, anchor, rid, (lo, hi)


def _support(conn, project, original_handoff, handoff, sources, path, generation):
    original_anchors = original_handoff['code_anchors']
    choices = [a for a in handoff['code_anchors']
               if a.get('source') == 'wrapped_log_caller' and a.get('source_excerpts')]
    (support,) = choices
    support_path = support['file_path']
    if support_path == path:
        raise ValueError('no separate support file')
    index, _, effect_id, bounds = _match_anchors(
        handoff['code_anchors'], original_anchors, support_path, support['symbol'], False)
    _, _, digest, text = sources[support_path]
    if _WEB_MENTION.search(text):
        raise ValueError('possible Web-support ownership')
    effect = _one(conn, 'code_log_effects', project.project_id, 'id=?', effect_id)
    (log,) = [x for x in handoff['log_anchors'] if x.get('effect_id') == effect_id]
    if (effect['evidence_class'] not in {'inferred_wrapped', 'static_wrapped'} or effect['truncated']
            or effect['file_path'] != support_path or effect['function'] != support['symbol']
            or effect['source_digest'] != digest or effect['index_generation'] != generation
            or type(effect['line']) is not int or not bounds[0] <= effect['line'] <= bounds[1]
            or log.get('file_path') != support_path or log.get('function') != support['symbol']
            or log.get('line') != effect['line'] or log.get('evidence_class') != effect['evidence_class']
            or log.get('message_template') != effect['message_template']
            or log.get('wrapper_symbol') != effect['wrapper_symbol']
            or log.get('log_id') != effect['sink_log_id']
            or not effect['raw_call'] or effect['raw_call'] not in _exact(text, (effect['line'], effect['line']))):
        raise ValueError('support effect not authenticated in method')
    row = _one(conn, 'code_symbols', project.project_id,
               'file_path=? AND symbol=? AND start_line=? AND end_line=?',
               support_path, support['symbol'], *bounds)
    _qualify_method(conn, project, row, support, bounds, digest, generation)
    owner = _one(conn, 'code_symbols', project.project_id, 'file_path=? AND qualified_name=?',
                 support_path, row['owner_name'])
    excerpt, old = _excerpt(support, text, 'query_term_window_within_anchor', False)
    _qualify_owner(conn, project, owner, row, old, digest, generation, 'class')
    if excerpt['symbol'] != support['symbol'] or not old[0] < bounds[0] <= bounds[1] < old[1]:
        raise ValueError('support must be a strict method within its displayed class')
    # Other evidence relying on an owner outside the retained snippet stays untouched.
    if any(handoff.get('relation_hints') or ()):
        raise ValueError('do not defer source alongside relation hints')
    for other in handoff['log_anchors']:
        if other.get('file_path') == support_path and other != log:
            raise ValueError('multiple relevant log paths in support file')
    return index, old, bounds, _exact(text, bounds)


def _trade(project, original, payload):
    fresh = payload['source_freshness']
    orig_fresh = original['source_freshness']
    generation = fresh['generation']
    budget = payload['output_budget']
    if (budget['target_tokens'] != 1500 or budget['truncated'] is not True
            or fresh['status'] != 'current' or orig_fresh['status'] != 'current'
            or type(generation) is not int or generation != orig_fresh['generation']
            or original['query'] != payload['query']
            or original['project_id'] != project.project_id or payload['project_id'] != project.project_id):
        return payload
    root = Path(project.root).resolve()
    if Path(original['project_path']).resolve() != root:
        return payload
    h = payload['query_handoff']
    oh = original['query_handoff']
    if (h.get('path_context', {}).get('activated') is not False
            or oh.get('path_context', {}).get('activated') is not False
            or any(a.get('identity_match') for a in oh['code_anchors'])):
        return payload
    # Inspect nominated raw callable and anchor paths, including non-displayed candidates.
    callable_ = oh.get('callable_evidence') or {}
    nominees = [*oh['code_anchors'], *original.get('wiki_matches', ()),
                *[c for c in [callable_.get('primary'), *callable_.get('alternatives', ())] if c]]
    paths = {c['file_path'] for c in nominees}
    if not 0 < len(paths) <= 12:
        return payload
    started = monotonic()
    with connect(project) as conn:
        conn.execute('BEGIN')
        conn.set_progress_handler(lambda: int(monotonic() - started > 2), 1000)
        state = _one(conn, 'code_index_state', project.project_id, '1=1')
        if state['status'] != 'active' or state['generation'] != generation:
            return payload
        sources = {}
        chains = []
        size = 0
        for candidate in sorted(paths):
            if monotonic() - started > 2:
                return payload
            physical, content, digest, text = _verified_source(conn, project, root, candidate, generation)
            size += len(content)
            if size > 8 * 1024 * 1024:
                return payload
            sources[candidate] = physical, content, digest, text
            if _WEB_MENTION.search(text):
                inventory = web_policy_inventory(text)
                if inventory is None:
                    return payload
                chains.extend((candidate, f) for f in inventory['chains'])
        ((path, fact),) = chains
        index, target, rid, bounds = _match_anchors(h['code_anchors'], oh['code_anchors'],
                                                    path, fact['method'], True)
        _, _, digest, text = sources[path]
        if bounds != (fact['start_line'], fact['end_line']):
            return payload
        row = _one(conn, 'code_symbols', project.project_id, 'id=?', rid)
        _qualify_method(conn, project, row, target, bounds, digest, generation)
        owner = _one(conn, 'code_symbols', project.project_id, 'file_path=? AND qualified_name=?',
                     path, fact['owner'])
        if row['owner_name'] != fact['owner'] or row['owner_kind'] != 'component':
            return payload
        _qualify_owner(conn, project, owner, row, (fact['class_start'], fact['class_end']),
                       digest, generation, 'component')
        _, old = _excerpt(target, text, 'callable_mechanism_window', True)
        if not bounds[0] <= old[0] <= old[1] < bounds[1]:
            return payload
        complete = _exact(text, bounds)
        s_index, s_old, s_new, s_body = _support(conn, project, oh, h, sources, path, generation)
        for rel, (file, original_source, _, _) in sources.items():
            if (monotonic() - started > 2 or (root / rel).resolve(strict=True) != file
                    or _read_regular(file) != original_source):
                return payload
        conn.rollback()  # End the read snapshot before checking the current generation.
        state = _one(conn, 'code_index_state', project.project_id, '1=1')
        if state['status'] != 'active' or state['generation'] != generation:
            return payload
    candidate = deepcopy(payload)
    handoff = candidate['query_handoff']
    result_anchors = handoff['code_anchors']
    target = result_anchors[index]
    support = result_anchors[s_index]
    target['source_excerpts'][0].update(
        symbol=target['symbol'], start_line=bounds[0], end_line=bounds[1],
        selection_reason='callable_symbol_range', truncated=False, content=complete,
    )
    support['read_window'] = dict(zip(('start_line', 'end_line'), s_old))
    support['source_excerpts'][0].update(start_line=s_new[0], end_line=s_new[1],
                                       truncated=True, content=s_body)
    excerpts = [e for a in result_anchors for e in a.get('source_excerpts', [])]
    chars = sum(len(e['content']) for e in excerpts)
    if chars > MAX_TOTAL_EXCERPT_CHARS:
        return payload
    policy = handoff['source_excerpt_policy']
    if policy['excerpt_count'] != len(excerpts):
        return payload
    policy['excerpt_chars'] = chars
    synchronize_estimate(candidate)
    actual = estimate_payload_tokens(candidate)
    return candidate if actual == candidate['output_budget']['estimated_tokens'] and actual <= 1500 else payload
