"""Extend an authenticated existing excerpt without changing candidate certainty."""
from copy import deepcopy
import hashlib

from .context_budget import synchronize_estimate
from .context_source_excerpt import (
    MAX_EXCERPT_CHARS, MAX_EXCERPT_LINES, MAX_TOTAL_EXCERPT_CHARS,
    resolved_root, safe_source_path,
)
from .context_source_recovery import MAX_VERIFY_SOURCE_BYTES
from .ecma_callable_ranges import named_callable_ranges
from .query_certified_portfolio_bounds import certified_projection


def extend_certified_tail(payload, project_path, token_budget, *, evidence, source_rows):
    handoff = payload['query_handoff']
    fresh = payload['source_freshness']
    if token_budget != 1500 or not isinstance(evidence, dict) or fresh.get('status') != 'current':
        return payload
    primary = evidence.get('primary') or {}
    portfolio = evidence.get('passage_portfolio') or {}
    if (evidence.get('certainty') != 'uncertain'
            or not isinstance(portfolio, dict) or not isinstance(primary, dict)
            or not certified_projection(portfolio, primary)
            or handoff.get('log_anchors') or handoff['path_context']['activated']):
        return payload
    members = portfolio['members']
    if len(members) != 2:
        return payload
    members = sorted(members, key=lambda m: m['source_range']['start_line'])
    spans = [{k: m['source_range'][k] for k in ('start_line', 'end_line')}
             | {'symbol': m['symbol']} for m in members]
    if any(s['start_line'] != m['source_range']['callable_start_line']
           or s['end_line'] != m['source_range']['callable_end_line']
           for s, m in zip(spans, members)):
        return payload
    first, tail = spans
    low, high = first['start_line'], tail['end_line']
    if not first['end_line'] < tail['start_line'] or high - low + 1 > MAX_EXCERPT_LINES:
        return payload
    matches = [i for i, a in enumerate(handoff['code_anchors'])
               if a['file_path'] == primary['file_path']]
    if len(matches) != 1:
        return payload
    index = matches[0]
    anchor = handoff['code_anchors'][index]
    old_ranges = anchor.get('source_ranges')
    sources = anchor.get('source_excerpts') or []
    if (anchor.get('role') != 'primary' or anchor.get('record_type') != 'code_symbol'
            or old_ranges not in ([first], [tail]) or len(sources) != 1):
        return payload
    indexed = old_ranges[0]
    if (anchor.get('symbol') != indexed['symbol']
            or anchor.get('read_window') != {k: indexed[k] for k in ('start_line', 'end_line')}):
        return payload
    old = sources[0]
    if (old.get('symbol') is not None or old.get('truncated') is not True
            or old.get('source') != 'current_worktree'
            or old.get('selection_reason') != 'query_term_window_within_anchor'
            or not 0 < old['start_line'] <= low or not tail['start_line'] <= old['end_line'] < high
            or high - old['start_line'] + 1 > MAX_EXCERPT_LINES):
        return payload
    ids = anchor.get('record_ids') or []
    rows = [row for row in source_rows if isinstance(row, dict) and row.get('id') in ids]
    if len(ids) != 1 or len(rows) != 1:
        return payload
    row = rows[0]
    expected = dict(project_id=payload['project_id'], kind='symbol', file_path=anchor['file_path'],
                    owner_name=primary.get('owner_name'), owner_kind=primary.get('owner_kind'),
                    symbol_type=anchor['symbol_type'], index_generation=fresh.get('generation'),
                    qualified_name=f"{primary.get('owner_name')}.{indexed['symbol']}", **indexed)
    if any(v is None or row.get(k) != v for k, v in expected.items()):
        return payload
    root = resolved_root(project_path)
    path = safe_source_path(root, anchor['file_path']) if root else None
    if path is None or path.suffix not in ('.ets', '.ts', '.tsx', '.js', '.jsx'):
        return payload
    try:
        with path.open('rb') as stream:
            raw = stream.read(MAX_VERIFY_SOURCE_BYTES + 1)
        if (len(raw) > MAX_VERIFY_SOURCE_BYTES or b'\0' in raw
                or hashlib.sha256(raw).hexdigest() != row.get('source_digest')):
            return payload
        lines = raw.decode('utf-8').splitlines()
    except (OSError, UnicodeError):
        return payload
    if high > len(lines) or old['content'] != '\n'.join(lines[old['start_line']-1:old['end_line']]):
        return payload
    # The same authenticated bytes must independently agree with the callable bounds.
    physical = named_callable_ranges(lines[low-1:high])
    if not all(any((r['symbol'], r['start_line'] + low - 1, r['end_line'] + low - 1)
                   == (s['symbol'], s['start_line'], s['end_line']) for r in physical)
               for s in spans):
        return payload
    complete = '\n'.join(lines[old['start_line']-1:high])
    if len(complete) > MAX_EXCERPT_CHARS:
        return payload
    candidate = deepcopy(payload)
    projected = candidate['query_handoff']['code_anchors'][index]
    projected['source_excerpts'][0].update(content=complete, end_line=high)
    if indexed == first:
        projected['source_ranges'].append(tail)
        projected['read_window']['end_line'] = high
    # Keep the original focus and truncation semantics for the wider planned window.
    policy = candidate['query_handoff'].get('source_excerpt_policy')
    if not policy:
        return payload
    total = sum(len(e['content']) for a in candidate['query_handoff']['code_anchors']
                for e in a.get('source_excerpts') or [])
    if total > MAX_TOTAL_EXCERPT_CHARS:
        return payload
    policy['excerpt_chars'] = total
    synchronize_estimate(candidate)
    return candidate if candidate['output_budget']['estimated_tokens'] <= token_budget else payload
