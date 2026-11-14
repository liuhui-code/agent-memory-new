# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite declared recovery roles, never a registry-to-store causal relation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from .storage import connect
from .query_ui_pair import valid_row

WORD = r'[A-Za-z]+(?:-[A-Za-z]+)*'
NP = rf'{WORD}(?: {WORD}){{0,2}}'
REQUEST = re.compile(rf'(?:The (?P<a>{NP}) remains after (?P<b>{NP}); )?(?:Return|Locate|Find) the registry branch and store sync owners\.?', re.I | re.ASCII)
RESERVED = set('and or not no only except exclude without return locate find source generated quoted literal both'.split())


def recovery_request(query):
    if not isinstance(query, str) or len(query) > 400:
        return False
    match = REQUEST.fullmatch(query)
    return bool(match and not any(word.casefold() in RESERVED for name in ('a', 'b')
                                 for word in re.split('[ -]', match[name] or '')))


def snapshot(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


class RecoveryHandoff(dict):
    def __copy__(self):
        return dict(self)

    def __deepcopy__(self, memo):
        return deepcopy(dict(self), memo)


def protected(handoff, path=None):
    path = path or handoff.get('path_context') or {}
    return (path.get('activated') or path.get('wrapped_log_evidence')
            or handoff.get('log_anchors')
            or any(a.get(k) for a in handoff.get('code_anchors') or []
                   for k in ('identity_match', 'log_identity_match', 'graph_neighbor', 'graph_relation')))


def bind_recovery_pair(project, query, handoff):
    if not recovery_request(query) or protected(handoff):
        return handoff
    anchors = handoff.get('code_anchors') or []
    paths = sorted({a.get('file_path') for a in anchors if isinstance(a.get('file_path'), str)})
    if not paths or len(anchors) > 12:
        return handoff
    marks = ','.join('?' for _ in paths)
    with connect(project) as conn:
        rows = [dict(r) for r in conn.execute(f'SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ({marks})', (project.project_id, *paths))]
        files = [dict(r) for r in conn.execute(f'SELECT * FROM code_files WHERE project_id=? AND file_path IN ({marks})', (project.project_id, *paths))]
    return bind_from_rows(project, query, handoff, rows, files)


def bind_from_rows(project, query, handoff, rows, files):
    from .query_recovery_source import parse_recovery_source
    if not recovery_request(query) or protected(handoff):
        return handoff
    anchors = handoff.get('code_anchors') or []
    if not anchors or len(anchors) > 12:
        return handoff
    root = Path(project.root).resolve()
    roles = {'registry': [], 'store': []}
    receipts = {}
    for path in sorted({a.get('file_path') for a in anchors if isinstance(a.get('file_path'), str)}):
        owners = [r for r in rows if r.get('file_path') == path and r.get('symbol_type') == 'class']
        file_rows = [r for r in files if r.get('file_path') == path]
        if len(owners) != 1 or len(file_rows) != 1 or not valid_row(owners[0], project):
            continue
        owner = owners[0]
        if any(file_rows[0].get(k) != owner[k] for k in ('source_digest', 'index_generation')):
            continue
        try:
            file = (root / path).resolve()
            if not file.is_relative_to(root) or file.suffix != '.ets' or file.stat().st_size > 2 * 1024 * 1024:
                continue
            raw = file.read_bytes()
            if len(raw) > 2 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != owner['source_digest']:
                continue
            source = raw.decode('utf-8')
        except (OSError, UnicodeError):
            continue
        parsed = parse_recovery_source(source)
        if not parsed or (parsed['owner'], parsed['class_start'], parsed['class_end']) != (owner['symbol'], owner['start_line'], owner['end_line']):
            continue
        represented = [a for a in anchors if a.get('file_path') == path and a.get('symbol') == owner['symbol']
                       and (a.get('start_line'), a.get('end_line')) == (owner['start_line'], owner['end_line'])]
        valid_methods = []
        for method in parsed['methods']:
            matching = [r for r in rows if r.get('file_path') == path and r.get('qualified_name') == owner['symbol'] + '.' + method['name']]
            if (len(matching) != 1 or not valid_row(matching[0], project)
                    or matching[0].get('symbol_type') not in {'method', 'function'}
                    or matching[0].get('owner_name') != owner['symbol']
                    or any(matching[0].get(k) != owner[k] for k in ('source_digest', 'index_generation'))
                    or (matching[0]['start_line'], matching[0]['end_line']) != (method['start_line'], method['end_line'])):
                continue
            if method['kind'] == 'store':
                state_fields = [f for f in parsed['fields'] if f['kind'] == 'state']
                if len(state_fields) != 1:
                    continue
                state = state_fields[0]
                matching_state = [r for r in rows if r.get('file_path') == path and r.get('qualified_name') == owner['symbol'] + '.' + state['name']]
                if (len(matching_state) != 1 or not valid_row(matching_state[0], project)
                        or matching_state[0].get('symbol_type') != 'state'
                        or any(matching_state[0].get(k) != owner[k] for k in ('source_digest', 'index_generation'))
                        or (matching_state[0]['start_line'], matching_state[0]['end_line']) != (state['start_line'], state['end_line'])):
                    continue
            valid_methods.append(method)
        for role in parsed['roles']:
            matches = [m for m in valid_methods if m['kind'] == role]
            if len(matches) == 1:
                roles[role].append((owner['symbol_key'], path))
                if len(represented) == 1:
                    receipts[path] = {'anchor': deepcopy(represented[0]), 'source': source,
                                      'digest': owner['source_digest'], 'parsed': parsed}
    if any(len(items) != 1 for items in roles.values()):
        return handoff
    selected_paths = list(dict.fromkeys(roles[role][0][1] for role in ('registry', 'store')))
    if any(path not in receipts for path in selected_paths):
        return handoff
    from .query_recovery_source import components
    certified = {(path, receipts[path]['parsed']['owner']) for path in selected_paths}
    evidence = handoff.get('callable_evidence') or {}
    observed = [evidence.get('primary') or {}, *(evidence.get('alternatives') or []),
                *((evidence.get('passage_portfolio') or {}).get('members') or [])]
    for item in observed:
        owner = item.get('owner_name')
        if (isinstance(owner, str) and {'registry', 'store'} & components(owner)
                and (item.get('file_path'), owner) not in certified):
            return handoff
    result = RecoveryHandoff(handoff)
    result._query = query
    result._receipts = tuple(receipts[p] for p in selected_paths)
    result._root = str(root)
    result._binding = (query, snapshot(anchors), snapshot(result._receipts), result._root, snapshot(evidence))
    return result


def valid(handoff, anchors, query, path=None):
    if not isinstance(handoff, RecoveryHandoff) or not recovery_request(query) or protected(handoff, path):
        return False
    try:
        return ((query, snapshot(anchors), snapshot(handoff._receipts), handoff._root,
                 snapshot(handoff.get('callable_evidence') or {})) == handoff._binding
                and query == handoff._query and isinstance(handoff._receipts, tuple)
                and 1 <= len(handoff._receipts) <= 2)
    except (AttributeError, TypeError, ValueError):
        return False


def preserve_recovery_pair(handoff, anchors, focused, query, path):
    if not valid(handoff, anchors, query, path):
        return focused
    result = list(focused)
    for receipt in handoff._receipts:
        original = receipt['anchor']
        if not any(a.get('file_path') == original['file_path'] and a.get('symbol') == original['symbol']
                   and a.get('start_line') == original['start_line'] and a.get('end_line') == original['end_line'] for a in result):
            result.append(deepcopy(original))
    return result


def current_sources(handoff):
    try:
        root = Path(handoff._root).resolve()
        for receipt in handoff._receipts:
            file = (root / receipt['anchor']['file_path']).resolve()
            if not file.is_relative_to(root) or file.suffix != '.ets' or file.stat().st_size > 2 * 1024 * 1024:
                return False
            raw = file.read_bytes()
            if len(raw) > 2 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != receipt['digest']:
                return False
        return True
    except (AttributeError, OSError, KeyError, TypeError, ValueError):
        return False


def accepted_output(handoff, baseline, candidate):
    if not current_sources(handoff):
        return False
    old, new = baseline['query_handoff'], candidate['query_handoff']
    if any(old.get(k) != new.get(k) for k in ('log_keywords', 'log_anchors', 'path_context', 'relation_hints')):
        return False
    current = new.get('code_anchors') or []
    cursor = 0
    for anchor in old.get('code_anchors') or []:
        found = next((i for i in range(cursor, len(current)) if current[i] == anchor), None)
        if found is None:
            return False
        cursor = found + 1
    for receipt in handoff._receipts:
        a = receipt['anchor']; start, end = a['start_line'], a['end_line']
        matches = [item for item in current if item.get('file_path') == a['file_path']]
        if len(matches) != 1:
            return False
        item = matches[0]
        if not any(r.get('start_line', 0) <= start and r.get('end_line', 0) >= end
                   for r in item.get('source_ranges') or []):
            return False
        excerpts = item.get('source_excerpts') or ([item['source_excerpt']] if item.get('source_excerpt') else [])
        lines = receipt['source'].splitlines()
        if not any(e.get('start_line', 0) <= start and e.get('end_line', 0) >= end
                   and e.get('content') == '\n'.join(lines[e['start_line']-1:e['end_line']]) for e in excerpts):
            return False
    return candidate.get('output_budget', {}).get('estimated_tokens', 1501) <= 1500


def complete_added_snapshots(handoff, baseline, candidate):
    """Only new exact certified anchors may display the retained source bytes."""
    if not valid(handoff, handoff.get('code_anchors') or [], handoff.get('input_query')):
        return candidate
    old_paths = {a.get('file_path') for a in baseline['query_handoff'].get('code_anchors') or []}
    result = deepcopy(candidate)
    for receipt in handoff._receipts:
        original = receipt['anchor']
        if original['file_path'] in old_paths:
            continue
        targets = [a for a in result['query_handoff'].get('code_anchors') or []
                   if a.get('file_path') == original['file_path'] and a.get('symbol') == original['symbol']]
        if len(targets) != 1:
            continue
        target = targets[0]
        start, end = original['start_line'], original['end_line']
        if not any(r.get('symbol') == original['symbol'] and r.get('start_line') == start and r.get('end_line') == end
                   for r in target.get('source_ranges') or []):
            continue
        target['source_excerpts'] = [{'symbol': original['symbol'], 'start_line': start, 'end_line': end,
            'content': '\n'.join(receipt['source'].splitlines()[start-1:end]),
            'source': 'validated_request_snapshot', 'selection_reason': 'existing_recovery_role_range',
            'focus_line': None, 'truncated': False}]
    from .context_budget import synchronize_estimate
    result['output_budget'] = {'estimated_tokens': 0, 'target_tokens': 1500,
                               'truncated': bool(candidate.get('output_budget', {}).get('truncated'))}
    synchronize_estimate(result)
    return result
