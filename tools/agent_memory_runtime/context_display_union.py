"""Final, lossless physical-window union; never a new owner/source certificate."""
from copy import deepcopy
import hashlib
from .context_source_excerpt import resolved_root, safe_source_path
from .context_source_recovery import MAX_VERIFY_SOURCE_BYTES
from .performance_scoring import estimate_payload_tokens

MEMBER_FIELDS = frozenset(('symbol', 'start_line', 'end_line', 'focus_line',
                           'source', 'selection_reason', 'truncated'))


def member_metadata(value):
    """Strict flat non-content schema, also used by sanitized transport."""
    if not isinstance(value, dict) or set(value) != MEMBER_FIELDS:
        return None
    if (not isinstance(value['symbol'], str) or not value['symbol']
            or type(value['start_line']) is not int or type(value['end_line']) is not int
            or not 0 < value['start_line'] <= value['end_line']
            or value['focus_line'] is not None and type(value['focus_line']) is not int
            or value['source'] != 'current_worktree'
            or value['selection_reason'] != 'callable_mechanism_window'
            or value['truncated'] is not False):
        return None
    return dict(value)


def union_primary_display(payload, project_path, token_budget, *, source_rows=(),
                          source_char_cap=1500, total_char_cap=2600, source_line_cap=40):
    """Any failed qualification returns the exact baseline object, without mutation."""
    h = payload.get('query_handoff', {})
    fresh = payload.get('source_freshness', {})
    evidence = h.get('callable_evidence')
    primary = evidence.get('primary') if isinstance(evidence, dict) else None
    if not isinstance(primary, dict) or not isinstance(primary.get('source_range'), dict):
        return payload
    bounds = primary['source_range']
    anchors = h.get('code_anchors', [])
    matches = [(i, a) for i, a in enumerate(anchors) if a.get('role') == 'primary'
               and a.get('file_path') == primary.get('file_path')]
    if fresh.get('status') != 'current' or len(matches) != 1:
        return payload
    index, a = matches[0]
    start, end = bounds.get('start_line'), bounds.get('end_line')
    if (type(start) is not int or type(end) is not int or not 0 < start <= end
            or a.get('symbol') != primary.get('symbol') or a.get('record_type') != 'code_symbol'
            or a.get('source_ranges') != [{'symbol': primary.get('symbol'), 'start_line': start, 'end_line': end}]
            or a.get('read_window') != {'start_line': start, 'end_line': end}):
        return payload
    old = a.get('source_excerpts', [])
    if not isinstance(old, list) or len(old) != 2:
        return payload
    members = []
    for e in old:
        if not isinstance(e, dict) or set(e) != MEMBER_FIELDS | {'content'} or not isinstance(e['content'], str):
            return payload
        m = member_metadata({k: v for k, v in e.items() if k != 'content'})
        if m is None:
            return payload
        members.append(m)
    spatial = sorted(members, key=lambda m: m['start_line'])
    low, high = spatial[0]['start_line'], spatial[1]['end_line']
    if spatial[0]['end_line'] + 1 != spatial[1]['start_line'] or not (end < low or start > high):
        return payload
    if max(high-low+1, end-start+1) > min(source_line_cap, 40):
        return payload
    ids = a.get('record_ids')
    if not isinstance(ids, list) or len(ids) != 1 or type(ids[0]) is not int:
        return payload
    rows = [r for r in source_rows if isinstance(r, dict) and r.get('id') == ids[0]]
    if len(rows) != 1:
        return payload
    row = rows[0]
    expected = dict(project_id=payload.get('project_id'), kind='symbol', file_path=a.get('file_path'),
                    symbol=a.get('symbol'), symbol_type=a.get('symbol_type'), start_line=start, end_line=end,
                    owner_name=primary.get('owner_name'), owner_kind=primary.get('owner_kind'),
                    index_generation=fresh.get('generation'))
    if (any(row.get(k) != v or v is None for k, v in expected.items())
            or row.get('qualified_name') != str(primary.get('owner_name')) + '.' + str(a.get('symbol'))):
        return payload
    root = resolved_root(project_path)
    path = safe_source_path(root, a.get('file_path')) if root else None
    if path is None:
        return payload
    try:
        with path.open('rb') as stream:
            raw = stream.read(MAX_VERIFY_SOURCE_BYTES + 1)
        if len(raw) > MAX_VERIFY_SOURCE_BYTES or hashlib.sha256(raw).hexdigest() != row.get('source_digest'):
            return payload
        lines = raw.decode('utf-8').splitlines()
    except (OSError, UnicodeError):
        return payload
    if max(high, end) > len(lines) or '\x00' in raw.decode('utf-8'):
        return payload
    def body(s, e):
        return '\n'.join(lines[s-1:e])
    if any(e['content'] != body(e['start_line'], e['end_line']) for e in old):
        return payload
    union = dict(symbol=None, start_line=low, end_line=high, focus_line=None,
                 source='current_worktree', selection_reason='adjacent_display_union', truncated=False,
                 content=body(low, high), constituent_ranges=members)
    added = dict(symbol=a['symbol'], start_line=start, end_line=end, focus_line=None,
                 source='current_worktree', selection_reason='existing_primary_display_range',
                 truncated=False, content=body(start, end))
    if len(union['content']) + len(added['content']) > min(source_char_cap, 1500):
        return payload
    candidate = deepcopy(payload)
    candidate['query_handoff']['code_anchors'][index]['source_excerpts'] = [union, added]
    all_excerpts = [e for anchor in candidate['query_handoff']['code_anchors'] for e in anchor.get('source_excerpts', [])]
    chars = sum(len(e.get('content', '')) for e in all_excerpts)
    if chars > min(total_char_cap, 2600):
        return payload
    policy = candidate['query_handoff'].get('source_excerpt_policy')
    budget = candidate.get('output_budget')
    if not isinstance(policy, dict) or not isinstance(budget, dict):
        return payload
    policy.update(excerpt_chars=chars, excerpt_count=len(all_excerpts))
    for _ in range(4):
        budget['estimated_tokens'] = estimate_payload_tokens(candidate)
    if budget['estimated_tokens'] > min(token_budget, budget.get('target_tokens', token_budget)):
        return payload
    return candidate


def display_excerpt_metadata(item):
    result = {
        key: item[key]
        for key in (
            "symbol", "start_line", "end_line", "focus_line", "source",
            "selection_reason", "truncated",
        )
        if item.get(key) not in (None, "")
    }

    members = item.get("constituent_ranges")
    if (item.get("selection_reason") == "adjacent_display_union" and item.get("symbol") is None
            and isinstance(members, list) and len(members) == 2):
        bounded = [member_metadata(member) for member in members]
        if all(member is not None for member in bounded):
            result["constituent_ranges"] = bounded
    return result


