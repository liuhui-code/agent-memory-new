# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Transactional, lossy ranking-detail trade for a complete existing source range."""
from copy import deepcopy
from math import isfinite
import hashlib
import re
import io

from .context_source_excerpt import (
    MAX_EXCERPT_CHARS, MAX_EXCERPT_LINES, MAX_TOTAL_EXCERPT_CHARS,
    resolved_root, safe_source_path,
)
from .performance_scoring import estimate_payload_tokens

MAX_VERIFY_SOURCE_BYTES = 2 * 1024 * 1024

RANK_REASONS = frozenset({
    'expanded_query:symbol', 'expanded_query:summary',
    'expanded_query:method_evidence', 'first_stage_rank_prior',
})


def recover_partial_primary(payload, project_path, token_budget, *,
                            source_char_cap=MAX_EXCERPT_CHARS, source_rows=(),
                            source_line_cap=MAX_EXCERPT_LINES,
                            total_char_cap=MAX_TOTAL_EXCERPT_CHARS):
    """Return the original object unless a fully bounded replacement fits.

    Raw evidence is never changed. No identity, role, mechanism, unknown reason,
    log, graph, uncertainty or alternative is removed. Only optional rank numbers
    and explicitly recognized ranking explanations are sacrificed after selection.
    """
    freshness = payload.get('source_freshness')
    if not isinstance(freshness, dict) or freshness.get('status') != 'current':
        return payload
    handoff = payload.get('query_handoff', {})
    anchors = handoff.get('code_anchors', [])
    if len(anchors) != 1 or anchors[0].get('role') != 'primary':
        return payload
    anchor = anchors[0]
    spans, excerpts = anchor.get('source_ranges', []), anchor.get('source_excerpts', [])
    if len(spans) != 1 or len(excerpts) != 1 or excerpts[0].get('truncated') is not True:
        return payload
    span, old = spans[0], excerpts[0]
    start, end = span.get('start_line'), span.get('end_line')
    if (type(start) is not int or type(end) is not int or not 0 < start <= end
            or end - start + 1 > min(source_line_cap, MAX_EXCERPT_LINES)
            or not span.get('symbol') or span.get('symbol') != old.get('symbol')
            or type(old.get('start_line')) is not int or old['start_line'] != start
            or type(old.get('end_line')) is not int
            or not start <= old['end_line'] < end):
        return payload
    root = resolved_root(project_path)
    path = safe_source_path(root, anchor.get('file_path')) if root else None
    if path is None:
        return payload
    matching = [row for row in source_rows if isinstance(row, dict)
                and type(row.get('id')) is int and row['id'] > 0
                and type(row.get('start_line')) is int and type(row.get('end_line')) is int
                and row.get('file_path') == anchor.get('file_path')
                and row.get('id') in anchor.get('record_ids', [])
                and {'file': 'code_file', 'symbol': 'code_symbol'}.get(row.get('kind')) == anchor.get('record_type')
                and row.get('symbol') == span['symbol']
                and row.get('start_line') == start and row.get('end_line') == end]
    if any(not isinstance(row.get('source_digest'), str) for row in matching):
        return payload
    digests = {row['source_digest'] for row in matching}
    if len(digests) != 1:
        return payload
    digest = next(iter(digests))
    if not isinstance(digest, str) or re.fullmatch(r'[0-9a-f]{64}', digest) is None:
        return payload
    try:
        with path.open('rb') as handle:
            raw = handle.read(MAX_VERIFY_SOURCE_BYTES + 1)
    except OSError:
        return payload
    if len(raw) > MAX_VERIFY_SOURCE_BYTES or hashlib.sha256(raw).hexdigest() != digest:
        return payload
    # Hash and extract from the same bounded bytes, never a second source read.
    with io.TextIOWrapper(io.BytesIO(raw), encoding='utf-8', errors='replace', newline=None) as handle:
        lines = [line.rstrip('\r\n') for line in handle]
    if end > len(lines) or any('\x00' in line for line in lines[start-1:end]):
        return payload
    content = '\n'.join(lines[start-1:end])
    if len(content) > min(source_char_cap, MAX_EXCERPT_CHARS):
        return payload
    complete = {'content': content}
    old_lines = str(old.get('content') or '').splitlines()
    new_lines = complete['content'].splitlines()
    if not old_lines or old_lines != new_lines[:len(old_lines)]:
        return payload
    if len(complete['content']) > min(total_char_cap, MAX_TOTAL_EXCERPT_CHARS):
        return payload
    candidate = deepcopy(payload)
    evidence = candidate['query_handoff'].get('callable_evidence', {})
    rows = [evidence.get('primary'), *evidence.get('alternatives', [])]
    changed = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in ('score', 'evidence_score'):
            value = row.get(key)
            if type(value) is int or (type(value) is float and isfinite(value)):
                del row[key]
                changed = True
        reasons = row.get('reasons')
        if isinstance(reasons, list):
            kept = [reason for reason in reasons if not isinstance(reason, str) or reason not in RANK_REASONS]
            if kept != reasons:
                row['reasons'] = kept
                changed = True
    if not changed:
        return payload
    updated = candidate['query_handoff']['code_anchors'][0]['source_excerpts'][0]
    # Keep existing selection/focus metadata: only restore the same source interval.
    updated.update(content=complete['content'], end_line=end, truncated=False)
    policy = candidate['query_handoff'].get('source_excerpt_policy')
    if isinstance(policy, dict):
        policy['excerpt_chars'] = len(complete['content'])
    budget = candidate.get('output_budget')
    if not isinstance(budget, dict):
        return payload
    budget['truncated'] = True  # Ranking diagnostics were removed even though source grew.
    for _ in range(3):
        budget['estimated_tokens'] = estimate_payload_tokens(candidate)
    if budget['estimated_tokens'] > token_budget:
        return payload
    return candidate
